"""App-Factory und Runner. Bindet ausschließlich an 127.0.0.1 (Single-User, lokal)."""

from __future__ import annotations

import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .ai import AiService, DemoAiService
from .api import router
from .config import MailAccount, load_postfach_config
from .demo import DemoEmiliaLLM, DemoMailbox
from .emilia import EmiliaService
from .mail_imap import Mailbox
from .memory import FakeEmbedder, MailMemory, OllamaEmbedder
from .watcher import LiveState, start_watcher_thread

log = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = int(os.environ.get("POSTFACH_PORT", "8722"))

_DEMO_ACCOUNT = MailAccount(
    name="demo", provider="imap", address="alex@demo.example",
    password_env="POSTFACH_DEMO", imap_host="demo.invalid",
)


def _llm_backend(agent_config):
    from email_agent.cli import backend_from_config

    return backend_from_config(agent_config)


def _root() -> Path:
    return Path(os.environ.get("POSTFACH_ROOT") or Path(__file__).resolve().parents[3])


def create_app(root: Path | None = None, demo: bool | None = None, mailbox_factory=None) -> FastAPI:
    root = Path(root) if root is not None else _root()
    if demo is None:
        demo = os.environ.get("POSTFACH_DEMO") == "1"

    cfg = load_postfach_config(root / "config" / "config.yaml")
    data_dir = root / "data"
    style_path = root / "config" / "style_profile.md"

    from .stores import DraftStore, ScreenerStore, SettingsStore, SnippetStore, SubscriptionStore

    app = FastAPI(title="Postfach", version="0.3.0")
    app.state.config = cfg
    app.state.demo = demo
    app.state.live = LiveState()
    # Demo und Echtbetrieb teilen data/ — Demo-Spielstände strikt trennen,
    # damit Demo-Experimente nie echte Signaturen/Entwürfe/Snippets anfassen.
    store_dir = data_dir / "demo" if demo else data_dir
    app.state.settings = SettingsStore(store_dir / "settings.json")
    app.state.drafts = DraftStore(store_dir / "drafts.json")
    app.state.snippets = SnippetStore(store_dir / "snippets.json")
    app.state.subscriptions = SubscriptionStore(store_dir / "subscriptions.json")
    app.state.screener = ScreenerStore(store_dir / "screener.json")

    from .search import SearchIndex

    app.state.search = SearchIndex(store_dir / "search.db")

    from .schedule import OutboxStore, Scheduler, ScheduleStore, start_scheduler_thread

    app.state.schedule = ScheduleStore(store_dir / "schedule.json")
    app.state.outbox = OutboxStore(store_dir / "outbox")

    if demo:
        app.state.accounts = {_DEMO_ACCOUNT.name: _DEMO_ACCOUNT}
        app.state.demo_mailbox = DemoMailbox()
        app.state.ai = DemoAiService(cfg.agent, data_dir / "classify-demo.json", style_path)
        app.state.emilia_memory = MailMemory(data_dir / "memory-demo.db", FakeEmbedder())
        app.state.emilia = EmiliaService(DemoEmiliaLLM(), app.state.emilia_memory, owner="Alex")

        @contextmanager
        def open_mailbox(account: MailAccount):
            yield app.state.demo_mailbox

        app.state.open_mailbox = open_mailbox
        # No-Op-Sender: der Demo-Unterschied bleibt hier am Factory-Seam,
        # die Send-Route kennt keinen Demo-Begriff.
        app.state.smtp_send = lambda account, mime_bytes: None
    else:
        from email_agent.llm.ollama import OllamaBackend

        app.state.accounts = {a.name: a for a in cfg.accounts}
        # Emilia ist immer lokal; Sortieren/Entwürfe je nach Schalter lokal oder Claude.
        local_llm = OllamaBackend(model=cfg.emilia.model, base_url=cfg.emilia.ollama_url)
        cloud_llm = _llm_backend(cfg.agent)
        app.state.ai = AiService(
            cfg.agent,
            backend=local_llm if cfg.emilia.sort_local else cloud_llm,
            cache_path=data_dir / "classify.json",
            style_path=style_path,
            draft_backend=local_llm if cfg.emilia.draft_local else cloud_llm,
        )
        app.state.emilia_memory = MailMemory(
            data_dir / "memory.db", OllamaEmbedder(cfg.emilia.embed_model, cfg.emilia.ollama_url)
        )
        app.state.emilia = EmiliaService(local_llm, app.state.emilia_memory, owner=cfg.agent.owner_name)

        def default_factory(account: MailAccount) -> Mailbox:
            password = os.environ.get(account.password_env, "").strip()
            if not password:
                raise OSError(f"Env-Variable {account.password_env} fehlt (.env)")
            return Mailbox.connect(
                host=account.imap_host, port=account.imap_port,
                address=account.address, password=password,
                sent_folder=account.sent_folder,
            )

        factory = mailbox_factory or default_factory

        @contextmanager
        def open_mailbox(account: MailAccount):
            box = factory(account)
            try:
                yield box
            finally:
                if hasattr(box, "logout"):
                    box.logout()

        app.state.open_mailbox = open_mailbox

        from .mail_send import send_mail

        def smtp_send(account: MailAccount, mime_bytes: bytes) -> None:
            password = os.environ.get(account.password_env, "").strip()
            send_mail(account, password, mime_bytes)

        app.state.smtp_send = smtp_send

        # Live-Push: IDLE-Watcher nur im echten Betrieb mit Default-Factory
        # (Tests injizieren mailbox_factory und bekommen keine Netz-Threads).
        if mailbox_factory is None:
            from imapclient import IMAPClient

            # Wasserstand pro Konto: bis zu welcher UID wurde schon benachrichtigt
            # (verhindert Doppel-Meldungen bei Re-IDLE/EXPUNGE-Echos).
            notified_uid: dict[str, int] = {}
            notify_lock = threading.Lock()

            def _index_new_mail(account_name: str) -> None:
                # Neue Mails in Emilias Gedächtnis aufnehmen und (falls pro
                # Konto aktiviert) nativ melden — EIN Fetch für beides, Best Effort.
                from .notify import notify_macos, pick_new_unseen, split_blocked

                account = app.state.accounts[account_name]
                with open_mailbox(account) as box:
                    mails = box.list_messages("INBOX", 10)
                    # Screener-Regel (NUTZER-Entscheidung, keine KI): geblockte
                    # Absender nach „Aussortiert" — nie Papierkorb, nie löschen.
                    kept, sorted_out = split_blocked(mails, app.state.screener.blocked(account_name))
                    if sorted_out:
                        try:
                            box.move_many("INBOX", [m.uid for m in sorted_out],
                                          "Aussortiert", ensure=True)
                            mails = kept  # weder indexieren (neue UID im Ziel) noch melden
                        except Exception:
                            log.exception("Aussortieren fehlgeschlagen (%s)", account_name)
                app.state.emilia.index_mails(account_name, "INBOX", mails, owner_addr=account.address)
                app.state.search.add_mails(account_name, "INBOX", mails)
                with notify_lock:
                    last = notified_uid.get(account_name)
                    if last is None:
                        # Erster Push seit App-Start: nur die neueste Mail melden
                        # (der Rest ist Bestand), Wasserstand auf Max setzen.
                        fresh = [m for m in mails[:1] if not m.seen]
                    else:
                        fresh = pick_new_unseen(mails, last)
                    notified_uid[account_name] = max(
                        (m.uid for m in mails), default=notified_uid.get(account_name, 0)
                    )
                if app.state.settings.notifications_enabled(account_name):
                    for m in fresh:
                        notify_macos(m.from_name or m.from_addr, m.subject or "(kein Betreff)")

            def _watch_connect_for(account: MailAccount):
                def connect():
                    password = os.environ.get(account.password_env, "").strip()
                    client = IMAPClient(account.imap_host, port=account.imap_port, ssl=True)
                    client.login(account.address, password)
                    return client

                return connect

            for account in cfg.accounts:
                start_watcher_thread(
                    account.name, _watch_connect_for(account), app.state.live, _index_new_mail
                )

    # --- Zeit-Warteschlange: Undo/Später-Sends, Snooze-Aufwachen, Follow-ups ---
    from .api import SendBody, perform_send
    from .mail_imap import is_sent_folder

    def _notify(account_name: str | None, title: str, text: str) -> None:
        if demo:  # Demo-Gespiele soll keine echten macOS-Meldungen werfen
            return
        # Pro-Konto-Einstellung respektieren; account=None = immer melden
        # (Sendefehler dürfen nie still bleiben).
        if account_name is not None and not app.state.settings.notifications_enabled(account_name):
            return
        from .notify import notify_macos

        notify_macos(title, text)

    def _run_send_job(job: dict) -> None:
        loaded = app.state.outbox.load(job["id"])
        if loaded is None:
            return  # Storno-Rest — nichts zu tun
        body_dict, attachments = loaded
        # Wurde der Entwurf NACH dem Planen weiterbearbeitet, gehört er dem
        # Nutzer — der Versand nimmt den eingefrorenen Stand, löscht aber nicht.
        draft_id = body_dict.get("draft_id")
        if draft_id:
            drafts = {d["id"]: d for d in app.state.drafts.list(body_dict.get("account", ""))}
            edited = drafts.get(draft_id)
            if edited and edited.get("updated", "") > job.get("created", ""):
                body_dict = {**body_dict, "draft_id": None}
        result = perform_send(app.state, SendBody(**body_dict), attachments)
        if result.get("warning"):
            _notify(None, "Gesendet — mit Einschränkung", result["warning"])
        app.state.live.bump(job["account"])  # UI: Ausgang/Gesendet auffrischen

    def _wake_snooze(job: dict) -> None:
        account = app.state.accounts[job["account"]]
        message_id = job["payload"]["message_id"]
        subject = job["payload"].get("subject", "")
        with app.state.open_mailbox(account) as box:
            uid = box.find_by_message_id(box.SNOOZE_FOLDER, message_id)
            if uid is None:
                _notify(job["account"], "Wiedervorlage", f"„{subject}“ ist nicht mehr im Später-Ordner")
                return
            # Erst ungelesen markieren, dann moven — Flags reisen mit,
            # die neue UID im Ziel kennen wir nicht.
            box.set_seen(box.SNOOZE_FOLDER, uid, False)
            box.move(box.SNOOZE_FOLDER, uid, "INBOX")
        app.state.live.bump(job["account"])
        _notify(job["account"], "Wiedervorlage", subject or "Eine Mail ist zurück in der Inbox")

    def _followup_answered(job: dict) -> bool:
        payload = job["payload"]
        account = app.state.accounts[job["account"]]
        thread = app.state.search.thread(job["account"], payload.get("thread_root", ""))
        sent_at = payload.get("sent_at", "")
        from .schedule import is_later

        return any(
            is_later(m["date"], sent_at)
            and not is_sent_folder(m["folder"])
            and m["from_addr"].lower() != account.address.lower()
            for m in thread
        )

    scheduler = Scheduler(
        app.state.schedule, app.state.outbox,
        send_fn=_run_send_job, wake_fn=_wake_snooze,
        followup_fn=_followup_answered,
        # Scheduler kennt keine Konten-Zuordnung → Fehler immer melden
        notify_fn=lambda title, text: _notify(None, title, text),
    )
    app.state.scheduler = scheduler
    if mailbox_factory is None:
        start_scheduler_thread(scheduler)

    app.include_router(router, prefix="/api")

    @app.middleware("http")
    async def _no_html_cache(request, call_next):
        # index.html darf nie cachen, sonst hängen Browser nach Updates am
        # alten Bundle (Assets selbst sind content-gehasht und cachebar).
        response = await call_next(request)
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    dist = root / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


def main() -> None:
    import uvicorn

    from email_agent.cli import load_env

    root = _root()
    load_env(root)
    uvicorn.run(create_app(root=root), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
