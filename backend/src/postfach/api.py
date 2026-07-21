"""API-Routen — exakt nach docs/api-contract.md.

Send- und Papierkorb-Pfade existieren NUR hier, als direkte Folge von
UI-Aktionen; die AI-Endpunkte (classify/draft) sind nachweislich frei von
Mailbox-Seiteneffekten (tests/test_safety.py).
"""

from __future__ import annotations

import functools
import json
import re

from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from imapclient.exceptions import IMAPClientError
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool

from email_agent.textutil import truncate

from .config import MailAccount
from .mail_imap import ParsedMail
from .sanitize import sanitize_mail_html

router = APIRouter()


class ActionBody(BaseModel):
    action: str
    folder: str = "INBOX"
    label: str | None = None


class ClassifyBody(BaseModel):
    account: str
    folder: str = "INBOX"
    uids: list[int]


class DraftBody(BaseModel):
    account: str
    folder: str = "INBOX"
    uid: int


class ForwardOf(BaseModel):
    folder: str = "INBOX"
    uid: int
    include_attachments: bool = True


class SendBody(BaseModel):
    account: str
    to: list[str]
    cc: list[str] = []
    bcc: list[str] = []
    subject: str
    body: str
    reply_to_uid: int | None = None
    folder: str = "INBOX"
    forward_of: ForwardOf | None = None
    # Nach erfolgreichem Versand serverseitig löschen — atomar gegenüber
    # spät eintreffenden Auto-Save-Upserts des Clients.
    draft_id: str | None = None


MAX_ATTACHMENT_TOTAL = 25 * 1024 * 1024  # 25 MB


def _account(request: Request, name: str) -> MailAccount:
    account = request.app.state.accounts.get(name)
    if account is None:
        raise HTTPException(404, f"Unbekanntes Konto „{name}“")
    return account


def _mailbox_errors(fn):
    """IMAP-/Netzfehler → 502 mit lesbarer Meldung.

    functools.wraps ist hier essenziell: FastAPI liest die Signatur der
    dekorierten Funktion für die Parameter-Injektion.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Lokales Ollama nicht erreichbar/fehlgeschlagen: {exc}") from exc
        except (IMAPClientError, OSError) as exc:
            raise HTTPException(502, str(exc)) from exc

    return wrapper


def _summary(account: str, folder: str, mail: ParsedMail, category: str | None) -> dict:
    snippet = truncate(re.sub(r"\s+", " ", mail.body_text).strip(), 120)
    return {
        "account": account,
        "folder": folder,
        "uid": mail.uid,
        "subject": mail.subject,
        "from_name": mail.from_name,
        "from_addr": mail.from_addr,
        "date": mail.date_iso,
        "snippet": snippet,
        "seen": mail.seen,
        "has_attachments": bool(mail.attachments),
        "category": category,
    }


@router.get("/accounts")
def accounts(request: Request):
    return [
        {"name": a.name, "address": a.address, "provider": a.provider}
        for a in request.app.state.accounts.values()
    ]


@router.get("/folders")
@_mailbox_errors
def folders(request: Request, account: str):
    acc = _account(request, account)
    with request.app.state.open_mailbox(acc) as box:
        return box.list_folders()


@router.get("/messages")
@_mailbox_errors
def messages(request: Request, account: str, folder: str = "INBOX", limit: int = 50):
    acc = _account(request, account)
    with request.app.state.open_mailbox(acc) as box:
        mails = box.list_messages(folder, limit)
    categories = request.app.state.ai.cached_categories(account, folder, [m.uid for m in mails])
    return [_summary(account, folder, m, categories.get(m.uid)) for m in mails]


@router.get("/messages/{account}/{uid}")
@_mailbox_errors
def message_detail(request: Request, account: str, uid: int, folder: str = "INBOX"):
    acc = _account(request, account)
    with request.app.state.open_mailbox(acc) as box:
        mail = box.get_message(folder, uid)
    if mail is None:
        raise HTTPException(404, f"Mail {uid} nicht gefunden")
    category = request.app.state.ai.cached_categories(account, folder, [uid]).get(uid)
    body_html = body_html_images = None
    if mail.body_html_raw:
        sanitized = sanitize_mail_html(mail.body_html_raw)
        body_html = sanitized.blocked
        body_html_images = sanitized.with_images if sanitized.had_remote_images else None
    return {
        **_summary(account, folder, mail, category),
        "to": list(mail.to),
        "cc": list(mail.cc),
        "reply_to": mail.reply_to,
        "message_id": mail.message_id,
        "body_text": mail.body_text,
        "body_html": body_html,
        "body_html_images": body_html_images,
        "attachments": [
            {"index": a.index, "filename": a.filename, "content_type": a.content_type, "size": a.size}
            for a in mail.attachments
        ],
    }


@router.get("/messages/{account}/{uid}/attachments/{index}")
@_mailbox_errors
def attachment(request: Request, account: str, uid: int, index: int, folder: str = "INBOX"):
    acc = _account(request, account)
    with request.app.state.open_mailbox(acc) as box:
        file = box.get_attachment(folder, uid, index)
    if file is None:
        raise HTTPException(404, "Anhang nicht gefunden")
    return Response(
        content=file.payload,
        media_type=file.content_type,
        headers={"Content-Disposition": _content_disposition(file.filename)},
    )


def _content_disposition(filename: str) -> str:
    """RFC-5987: Header-Werte sind latin-1 — Unicode-Namen (€, Umlaute) gehen
    über filename*, der ASCII-Fallback ist zusätzlich escaped (kein CRLF/Quote)."""
    from urllib.parse import quote

    fallback = re.sub(r"[^A-Za-z0-9. _-]", "_", filename) or "anhang"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"


@router.post("/messages/{account}/{uid}/action")
@_mailbox_errors
def action(request: Request, account: str, uid: int, body: ActionBody):
    acc = _account(request, account)
    agent_config = request.app.state.config.agent
    moved_to: str | None = None
    with request.app.state.open_mailbox(acc) as box:
        # exists() statt Voll-Download: Triage (j/e/j/e …) ist der heiße Pfad.
        if not box.exists(body.folder, uid):
            raise HTTPException(404, f"Mail {uid} nicht gefunden")
        if body.action in ("read", "unread"):
            box.set_seen(body.folder, uid, body.action == "read")
            request.app.state.search.set_seen(account, body.folder, [uid], body.action == "read")
        elif body.action == "trash":
            moved_to = box.trash_folder()
            box.move(body.folder, uid, moved_to)
        elif body.action == "archive":
            category = request.app.state.ai.cached_categories(account, body.folder, [uid]).get(uid)
            # folder_for: respektiert per-Kategorie-Ordner-Mapping (z. B. INBOX/Abos auf GMX).
            moved_to = agent_config.folder_for(category) if category else box.archive_folder_default()
            box.move(body.folder, uid, moved_to, ensure=True)
        elif body.action == "label":
            if not body.label:
                raise HTTPException(422, "label fehlt")
            moved_to = agent_config.full_label(body.label)
            box.move(body.folder, uid, moved_to, ensure=True)
        elif body.action == "spam":
            target = box.junk_folder()
            if target != body.folder:  # Self-Move ist serverabhängig NO/UID-Wechsel
                box.move(body.folder, uid, target)
                moved_to = target
        elif body.action == "unspam":
            if body.folder != "INBOX":
                box.move(body.folder, uid, "INBOX")
                moved_to = "INBOX"
        else:
            raise HTTPException(422, f"Unbekannte Aktion „{body.action}“")
    if moved_to:
        # Verschoben = im Ziel neue UID → Index-Eintrag entfernen (Re-Index füllt nach)
        request.app.state.search.remove_mails(account, body.folder, [uid])
    return {"ok": True}





class BatchActionBody(BaseModel):
    account: str
    folder: str = "INBOX"
    uids: list[int]
    # Bewusst geschlossene Liste — insbesondere KEIN send.
    action: Literal["read", "unread", "archive", "trash", "spam", "unspam"]


@router.post("/batch-action")
@_mailbox_errors
def batch_action(request: Request, body: BatchActionBody):
    """Bulk-Triage: EINE Verbindung, Listen-Operationen statt N Requests."""
    acc = _account(request, body.account)
    agent_config = request.app.state.config.agent
    uids = sorted(set(body.uids))
    if not uids:
        return {"ok": True, "done": 0}
    removed: list[int] = []
    with request.app.state.open_mailbox(acc) as box:
        if body.action in ("read", "unread"):
            box.set_seen_many(body.folder, uids, body.action == "read")
            request.app.state.search.set_seen(body.account, body.folder, uids, body.action == "read")
        elif body.action == "trash":
            # Ziel EINMAL auflösen — trash() würde pro UID neu resolven.
            box.move_many(body.folder, uids, box.trash_folder())
            removed = uids
        elif body.action == "spam":
            target = box.junk_folder()
            if target != body.folder:
                box.move_many(body.folder, uids, target)
                removed = uids
        elif body.action == "unspam":
            if body.folder != "INBOX":
                box.move_many(body.folder, uids, "INBOX")
                removed = uids
        else:  # archive — Kategorie-Mapping gilt PRO Mail, also nach Ziel gruppieren
            categories = request.app.state.ai.cached_categories(body.account, body.folder, uids)
            by_target: dict[str, list[int]] = {}
            for uid in uids:
                category = categories.get(uid)
                target = agent_config.folder_for(category) if category else box.archive_folder_default()
                by_target.setdefault(target, []).append(uid)
            for target, group in by_target.items():
                box.move_many(body.folder, group, target, ensure=True)
            removed = uids
    if removed:
        # Verschoben = im Ziel neue UIDs → Index-Einträge entfernen (Re-Index füllt nach)
        request.app.state.search.remove_mails(body.account, body.folder, removed)
    return {"ok": True, "done": len(uids)}


class ClassifyOverrideBody(BaseModel):
    account: str
    folder: str = "INBOX"
    uid: int
    category: str


@router.post("/classify/override")
def classify_override(request: Request, body: ClassifyOverrideBody):
    _account(request, body.account)
    valid = set(request.app.state.config.agent.taxonomy)
    if body.category not in valid:
        raise HTTPException(422, f"Unbekannte Kategorie „{body.category}“ — erlaubt: {sorted(valid)}")
    request.app.state.ai.override_category(body.account, body.folder, body.uid, body.category)
    return {"ok": True}


@router.get("/status")
def status(request: Request):
    """Verbindungsstatus der IDLE-Watcher — nie still scheitern."""
    return {"accounts": request.app.state.live.status_snapshot()}


@router.get("/categories")
def categories(request: Request):
    """Alle konfigurierten Kategorien (fürs Korrektur-Menü im Reader)."""
    return sorted(request.app.state.config.agent.taxonomy)


@router.post("/classify")
@_mailbox_errors
def classify(request: Request, body: ClassifyBody):
    acc = _account(request, body.account)
    with request.app.state.open_mailbox(acc) as box:
        mails = box.get_messages(body.folder, body.uids)
    result = request.app.state.ai.classify(body.account, body.folder, mails)
    return {str(uid): entry for uid, entry in result.items()}


@router.post("/draft")
@_mailbox_errors
def draft(request: Request, body: DraftBody):
    acc = _account(request, body.account)
    with request.app.state.open_mailbox(acc) as box:
        mail = box.get_message(body.folder, body.uid)
    if mail is None:
        raise HTTPException(404, f"Mail {body.uid} nicht gefunden")
    return {"text": request.app.state.ai.draft(mail)}


@router.post("/send")
async def send(request: Request):
    """Nimmt JSON (ohne Dateien) ODER multipart (payload-Feld + files).
    Der blockierende Mail-Teil läuft im Threadpool."""
    attachments: list[tuple[str, str, bytes]] = []
    content_type = request.headers.get("content-type", "")
    try:
        if content_type.startswith("multipart/"):
            form = await request.form()
            body = SendBody(**json.loads(str(form.get("payload") or "{}")))
            total = 0
            for upload in form.getlist("files"):
                if not hasattr(upload, "read"):  # reines Textfeld namens "files"
                    continue
                payload = await upload.read()
                total += len(payload)
                if total > MAX_ATTACHMENT_TOTAL:
                    raise HTTPException(413, "Anhänge zusammen größer als 25 MB.")
                attachments.append(
                    (upload.filename or "anhang", upload.content_type or "application/octet-stream", payload)
                )
        else:
            body = SendBody(**await request.json())
    except (ValidationError, json.JSONDecodeError) as exc:
        raise HTTPException(422, str(exc)) from exc

    return await run_in_threadpool(_do_send, request, body, attachments)


@_mailbox_errors
def _do_send(request: Request, body: SendBody, attachments: list[tuple[str, str, bytes]]):
    from .mail_send import build_outgoing

    acc = _account(request, body.account)
    # Eine IMAP-Verbindung für Original-Fetch, Weiterleitungs-Anhänge UND Sent-Ablage.
    with request.app.state.open_mailbox(acc) as box:
        original = None
        if body.reply_to_uid is not None:
            original = box.get_message(body.folder, body.reply_to_uid)
        if body.forward_of is not None and body.forward_of.include_attachments:
            for file in box.get_attachment_files(body.forward_of.folder, body.forward_of.uid):
                attachments.append((file.filename, file.content_type, file.payload))
        # Das Limit gilt für die Gesamtheit — Upload-Dateien UND Original-Anhänge.
        if sum(len(p) for _f, _t, p in attachments) > MAX_ATTACHMENT_TOTAL:
            raise HTTPException(413, "Anhänge zusammen größer als 25 MB.")
        mime_bytes = build_outgoing(
            from_addr=acc.address, to=body.to, cc=body.cc,
            subject=body.subject, body=body.body,
            reply_to_original=original,
            bcc=body.bcc, attachments=attachments,
        )
        # Im Demo-Modus ist smtp_send ein No-Op (Factory-Seam in app.py).
        request.app.state.smtp_send(acc, mime_bytes)
        # Ab hier IST die Mail raus — der zugehörige Entwurf ist Geschichte,
        # egal was die Sent-Ablage noch sagt.
        if body.draft_id:
            request.app.state.drafts.delete(body.draft_id)
        # Gmail legt via SMTP Gesendetes selbst ab — APPEND ergäbe Duplikate.
        if acc.provider != "gmail":
            try:
                box.append_sent(mime_bytes)
            except (IMAPClientError, OSError) as exc:
                # Die Mail IST raus — das darf nicht wie ein Sendefehler aussehen,
                # sonst schickt der Nutzer sie „nochmal" und der Empfänger kriegt sie doppelt.
                return {
                    "ok": True,
                    "warning": f"Gesendet — aber die Ablage im Gesendet-Ordner schlug fehl: {exc}",
                }
    return {"ok": True}


# --- Emilia (lokaler Copilot: liest & formuliert, führt nie Aktionen aus) ---


class EmiliaChatBody(BaseModel):
    account: str
    message: str
    folder: str = "INBOX"
    uid: int | None = None


class EmiliaImproveBody(BaseModel):
    text: str
    mode: Literal["korrigieren", "verbessern"]


class EmiliaIndexBody(BaseModel):
    account: str


@router.post("/emilia/chat")
@_mailbox_errors
def emilia_chat(request: Request, body: EmiliaChatBody):
    acc = _account(request, body.account)
    context_mail = None
    if body.uid is not None:
        with request.app.state.open_mailbox(acc) as box:
            context_mail = box.get_message(body.folder, body.uid)
    return request.app.state.emilia.chat(body.account, body.message, context_mail)


@router.post("/emilia/improve")
def emilia_improve(request: Request, body: EmiliaImproveBody):
    return {"text": request.app.state.emilia.improve(body.text, body.mode)}


@router.post("/emilia/index")
@_mailbox_errors
def emilia_index(request: Request, body: EmiliaIndexBody):
    from datetime import datetime

    from .emilia import iter_index_folders

    acc = _account(request, body.account)
    search_index = request.app.state.search
    emilia = request.app.state.emilia
    indexed = 0
    scanned: list[str] = []
    # Ein Scan, zwei Abnehmer: Emilia-Gedächtnis + Volltext-Suche.
    with request.app.state.open_mailbox(acc) as box:
        for folder in iter_index_folders(box):
            mails = box.list_messages(folder, 10000)
            indexed += emilia.index_mails(body.account, folder, mails, owner_addr=acc.address)
            search_index.add_mails(body.account, folder, mails)
            search_index.prune_folder(body.account, folder, [m.uid for m in mails])
            scanned.append(folder)
    # Extern verschwundene Ordner (und nie gescannte wie Papierkorb/Spam) räumen
    search_index.prune_missing_folders(body.account, scanned)
    search_index.mark_full_index(body.account, datetime.now().isoformat(timespec="seconds"))
    return {"indexed": indexed}


@router.get("/emilia/status")
def emilia_status(request: Request):
    emilia_cfg = request.app.state.config.emilia
    return {
        "model": emilia_cfg.model,
        "embed_model": emilia_cfg.embed_model,
        "indexed_mails": request.app.state.emilia_memory.count_all(),
        "sort_local": emilia_cfg.sort_local,
    }


# --- Batch 1: Einstellungen, Entwürfe, Snippets, Kontakte (lokale Stores) ---


class DraftSaveBody(BaseModel):
    id: str | None = None
    account: str
    to: list[str] = []
    cc: list[str] = []
    bcc: list[str] = []
    subject: str = ""
    body: str = ""
    mode: Literal["new", "reply", "forward"] = "new"
    ref_folder: str | None = None
    ref_uid: int | None = None
    include_attachments: bool = True  # Weiterleitung: Original-Anhänge mitsenden?


class SettingsBody(BaseModel):
    # None = Sektion nicht anfassen (Teil-Update; Alt-Clients schicken nur signatures)
    signatures: dict[str, str] | None = None
    notifications: dict[str, bool] | None = None


class SnippetItem(BaseModel):
    abbrev: str
    title: str = ""
    text: str


@router.get("/settings")
def get_settings(request: Request):
    return request.app.state.settings.get()


@router.put("/settings")
def put_settings(request: Request, body: SettingsBody):
    request.app.state.settings.put(body.model_dump())
    return {"ok": True}


@router.get("/contacts")
def contacts(request: Request, q: str, limit: int = 8):
    return request.app.state.emilia_memory.search_contacts(q, limit=min(limit, 20))


@router.get("/drafts")
def list_drafts(request: Request, account: str):
    return request.app.state.drafts.list(account)


@router.post("/drafts")
def upsert_draft(request: Request, body: DraftSaveBody):
    return {"id": request.app.state.drafts.upsert(body.model_dump())}


@router.delete("/drafts/{draft_id}")
def delete_draft(request: Request, draft_id: str):
    if not request.app.state.drafts.delete(draft_id):
        raise HTTPException(404, "Entwurf nicht gefunden")
    return {"ok": True}


@router.get("/snippets")
def get_snippets(request: Request):
    return request.app.state.snippets.get()


@router.put("/snippets")
def put_snippets(request: Request, body: list[SnippetItem]):
    request.app.state.snippets.put([i.model_dump() for i in body])
    return {"ok": True}


# --- Live-Push (SSE): meldet der App neue Mails aus dem IDLE-Watcher ---


@router.get("/events")
async def events(request: Request, once: int = 0):
    import asyncio

    from fastapi.responses import StreamingResponse

    state = request.app.state.live

    async def stream():
        yield ": verbunden\n\n"
        last = state.snapshot()
        last_status = state.status_snapshot()
        ticks = 0
        while True:
            if once and ticks > 0:
                return
            if await request.is_disconnected():
                return
            await asyncio.sleep(0 if once else 2)
            ticks += 1
            now = state.snapshot()
            for account, version in now.items():
                if version != last.get(account, 0):
                    yield f"data: {json.dumps({'type': 'new_mail', 'account': account})}\n\n"
            last = now
            # Verbindungsstatus-Wechsel sofort in die UI (nie still scheitern)
            now_status = state.status_snapshot()
            for account, entry in now_status.items():
                if entry["connected"] != last_status.get(account, {}).get("connected"):
                    yield (
                        "data: "
                        + json.dumps({"type": "status", "account": account, "connected": entry["connected"]})
                        + "\n\n"
                    )
            last_status = now_status
            if ticks % 12 == 0:
                yield ": ping\n\n"  # Keepalive gegen Proxy-/Idle-Timeouts

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/search")
@_mailbox_errors
def search(request: Request, account: str, q: str, folder: str = "INBOX"):
    acc = _account(request, account)
    index = request.app.state.search
    if index.is_ready(account):
        # Schneller Pfad: lokaler FTS-Index über ALLE Ordner des Kontos.
        # (Erst nach einem VOLLEN Index-Lauf — die paar Watcher-Zeilen eines
        # frischen Setups dürfen den IMAP-Fallback nicht verschatten.)
        hits = index.search(account, q)
        categories = request.app.state.ai.cached_categories_many(
            account, [(h["folder"], h["uid"]) for h in hits]
        )
        for h in hits:
            h["category"] = categories.get((h["folder"], h["uid"]))
        return hits
    # Fallback (Index nie voll aufgebaut): IMAP-Suche im übergebenen Ordner.
    with request.app.state.open_mailbox(acc) as box:
        mails = box.search(folder, q)
    categories = request.app.state.ai.cached_categories(account, folder, [m.uid for m in mails])
    return [_summary(account, folder, m, categories.get(m.uid)) for m in mails]


@router.get("/search/status")
def search_status(request: Request, account: str):
    """ready=False → UI weist darauf hin, dass nur der IMAP-Fallback sucht."""
    _account(request, account)
    index = request.app.state.search
    return {"indexed": index.count(account), "ready": index.is_ready(account)}
