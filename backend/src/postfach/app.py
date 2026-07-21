"""App-Factory und Runner. Bindet ausschließlich an 127.0.0.1 (Single-User, lokal)."""

from __future__ import annotations

import os
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

    from .stores import DraftStore, SettingsStore, SnippetStore

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

            def _index_new_mail(account_name: str) -> None:
                # Neue Mails direkt in Emilias Gedächtnis aufnehmen (Best Effort).
                account = app.state.accounts[account_name]
                with open_mailbox(account) as box:
                    app.state.emilia.index_folder(
                        account_name, box, "INBOX", limit=10, owner_addr=account.address
                    )

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
