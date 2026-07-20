"""API-Routen — exakt nach docs/api-contract.md.

Send- und Papierkorb-Pfade existieren NUR hier, als direkte Folge von
UI-Aktionen; die AI-Endpunkte (classify/draft) sind nachweislich frei von
Mailbox-Seiteneffekten (tests/test_safety.py).
"""

from __future__ import annotations

import functools
import re

from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from imapclient.exceptions import IMAPClientError
from pydantic import BaseModel

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


class SendBody(BaseModel):
    account: str
    to: list[str]
    cc: list[str] = []
    subject: str
    body: str
    reply_to_uid: int | None = None
    folder: str = "INBOX"


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
    with request.app.state.open_mailbox(acc) as box:
        # exists() statt Voll-Download: Triage (j/e/j/e …) ist der heiße Pfad.
        if not box.exists(body.folder, uid):
            raise HTTPException(404, f"Mail {uid} nicht gefunden")
        if body.action == "read":
            box.set_seen(body.folder, uid, True)
        elif body.action == "unread":
            box.set_seen(body.folder, uid, False)
        elif body.action == "trash":
            box.trash(body.folder, uid)
        elif body.action == "archive":
            category = request.app.state.ai.cached_categories(account, body.folder, [uid]).get(uid)
            # folder_for: respektiert per-Kategorie-Ordner-Mapping (z. B. INBOX/Abos auf GMX).
            target = agent_config.folder_for(category) if category else box.archive_folder_default()
            box.move(body.folder, uid, target, ensure=True)
        elif body.action == "label":
            if not body.label:
                raise HTTPException(422, "label fehlt")
            box.move(body.folder, uid, agent_config.full_label(body.label), ensure=True)
        else:
            raise HTTPException(422, f"Unbekannte Aktion „{body.action}“")
    return {"ok": True}


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
@_mailbox_errors
def send(request: Request, body: SendBody):
    from .mail_send import build_outgoing

    acc = _account(request, body.account)
    # Eine IMAP-Verbindung für Original-Fetch UND Sent-Ablage.
    with request.app.state.open_mailbox(acc) as box:
        original = None
        if body.reply_to_uid is not None:
            original = box.get_message(body.folder, body.reply_to_uid)
        mime_bytes = build_outgoing(
            from_addr=acc.address, to=body.to, cc=body.cc,
            subject=body.subject, body=body.body,
            reply_to_original=original,
        )
        # Im Demo-Modus ist smtp_send ein No-Op (Factory-Seam in app.py).
        request.app.state.smtp_send(acc, mime_bytes)
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
    acc = _account(request, body.account)
    with request.app.state.open_mailbox(acc) as box:
        indexed = request.app.state.emilia.index(body.account, box)
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


# --- Live-Push (SSE): meldet der App neue Mails aus dem IDLE-Watcher ---


@router.get("/events")
async def events(request: Request, once: int = 0):
    import asyncio
    import json as jsonlib

    from fastapi.responses import StreamingResponse

    state = request.app.state.live

    async def stream():
        yield ": verbunden\n\n"
        last = state.snapshot()
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
                    yield f"data: {jsonlib.dumps({'type': 'new_mail', 'account': account})}\n\n"
            last = now
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
    with request.app.state.open_mailbox(acc) as box:
        mails = box.search(folder, q)
    categories = request.app.state.ai.cached_categories(account, folder, [m.uid for m in mails])
    return [_summary(account, folder, m, categories.get(m.uid)) for m in mails]
