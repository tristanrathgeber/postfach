"""IMAP-Schicht des Clients: lesen, ablegen, Flags — plus Sent-Ablage.

Anders als der email-agent darf Postfach in den Papierkorb verschieben und
Gesendetes ablegen — aber ausschließlich als Folge expliziter UI-Aktionen
(tests/test_safety.py erzwingt, dass die AI-Schicht hierauf keinen Zugriff hat).
Endgültiges Entfernen vom Server gibt es hier nicht.
"""

from __future__ import annotations

import email
import email.utils
from dataclasses import dataclass, field
from email.policy import default as default_policy

from email_agent.textutil import html_to_text

_TRASH_NAMES = {"trash", "papierkorb", "gelöscht", "deleted items", "deleted messages", "gelöschte objekte", "geloeschte objekte"}
_SENT_NAMES = {"sent", "sent items", "sent messages", "gesendet", "gesendete objekte", "gesendete elemente"}
_ARCHIVE_NAMES = {"archive", "archiv", "all mail", "alle nachrichten"}
_JUNK_NAMES = {"spam", "junk", "junk-e-mail", "spamverdacht", "werbung", "bulk mail"}


def is_sent_folder(folder: str) -> bool:
    """Kanonische Sent-Erkennung per Ordnername — einzige Wahrheit, damit
    z. B. die Kontakt-Ernte keine eigene, driftende Namensliste pflegt."""
    leaf = folder.split("/")[-1].split(".")[-1].lower()
    return folder.lower() in _SENT_NAMES or leaf in _SENT_NAMES


@dataclass(frozen=True)
class AttachmentMeta:
    index: int
    filename: str
    content_type: str
    size: int


@dataclass(frozen=True)
class AttachmentFile:
    filename: str
    content_type: str
    payload: bytes


@dataclass(frozen=True)
class ParsedMail:
    uid: int
    subject: str
    from_name: str
    from_addr: str
    to: tuple[str, ...]
    cc: tuple[str, ...]
    reply_to: str | None
    message_id: str
    references: str
    date_iso: str
    seen: bool
    body_text: str
    body_html_raw: str | None
    attachments: tuple[AttachmentMeta, ...] = field(default_factory=tuple)
    headers: dict = field(default_factory=dict)  # lowercase keys (für AI-Heuristik)


def _addresses(msg, header: str) -> tuple[str, ...]:
    return tuple(a for _n, a in email.utils.getaddresses([str(msg.get(header, ""))]) if a)


def _date_iso(msg) -> str:
    try:
        parsed = email.utils.parsedate_to_datetime(str(msg.get("Date", "")))
        return parsed.isoformat() if parsed else ""
    except Exception:
        return ""


def _walk_parts(msg):
    text, html = None, None
    attachments = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        if filename or part.get_content_disposition() == "attachment":
            attachments.append(part)
        elif part.get_content_type() == "text/plain" and text is None:
            text = part
        elif part.get_content_type() == "text/html" and html is None:
            html = part
    return text, html, attachments


def _content(part) -> str:
    try:
        return str(part.get_content())
    except Exception:
        payload = part.get_payload(decode=True)
        return payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else ""


def parse_full(uid: int, raw: bytes, seen: bool) -> ParsedMail:
    msg = email.message_from_bytes(raw, policy=default_policy)
    from_name, from_addr = email.utils.parseaddr(str(msg.get("From", "")))
    _, reply_to = email.utils.parseaddr(str(msg.get("Reply-To", "")))
    text_part, html_part, attachment_parts = _walk_parts(msg)
    body_html_raw = _content(html_part) if html_part is not None else None
    body_text = _content(text_part).strip() if text_part is not None else (
        html_to_text(body_html_raw) if body_html_raw else ""
    )
    attachments = tuple(
        AttachmentMeta(
            index=i,
            filename=str(part.get_filename() or f"anhang-{i}"),
            content_type=part.get_content_type(),
            size=len(part.get_payload(decode=True) or b""),
        )
        for i, part in enumerate(attachment_parts)
    )
    return ParsedMail(
        uid=uid,
        subject=str(msg.get("Subject", "")),
        from_name=from_name,
        from_addr=from_addr,
        to=_addresses(msg, "To"),
        cc=_addresses(msg, "Cc"),
        reply_to=reply_to or None,
        message_id=str(msg.get("Message-ID", "")).strip(),
        # Viele Clients setzen nur In-Reply-To — als References-Ersatz nutzen
        # (Threading-Wurzel wäre sonst blind für deren Antworten).
        references=(str(msg.get("References", "")).strip() or str(msg.get("In-Reply-To", "")).strip()),
        date_iso=_date_iso(msg),
        seen=seen,
        body_text=body_text,
        body_html_raw=body_html_raw,
        attachments=attachments,
        headers={k.lower(): str(v) for k, v in msg.items()},
    )


class Mailbox:
    """Ein Konto, ein injizierter IMAPClient (dadurch testbar)."""

    def __init__(self, client, sent_folder: str | None = None) -> None:
        self._client = client
        self._sent_override = sent_folder

    @classmethod
    def connect(cls, host: str, port: int, address: str, password: str, sent_folder: str | None = None) -> "Mailbox":
        from imapclient import IMAPClient

        client = IMAPClient(host, port=port, ssl=True)
        client.login(address, password)
        return cls(client, sent_folder=sent_folder)

    def logout(self) -> None:
        try:
            self._client.logout()
        except Exception:
            pass

    # --- Lesen ---

    def list_messages(self, folder: str, limit: int) -> list[ParsedMail]:
        self._client.select_folder(folder, readonly=True)
        uids = sorted(self._client.search(["ALL"]))[-limit:]
        mails = self._fetch_parsed(folder, uids)
        return sorted(mails, key=lambda m: m.uid, reverse=True)

    def get_message(self, folder: str, uid: int) -> ParsedMail | None:
        mails = self.get_messages(folder, [uid])
        return mails[0] if mails else None

    def get_messages(self, folder: str, uids: list[int]) -> list[ParsedMail]:
        self._client.select_folder(folder, readonly=True)
        return self._fetch_parsed(folder, sorted(set(uids)))

    def exists(self, folder: str, uid: int) -> bool:
        self._client.select_folder(folder, readonly=True)
        return uid in set(self._client.search(["UID", str(uid)]))

    def get_attachment_files(self, folder: str, uid: int) -> list[AttachmentFile]:
        """Alle Anhänge mit EINEM Fetch + Parse — der Weiterleitungs-Pfad
        holt sonst dieselbe Mail pro Anhang komplett neu über IMAP."""
        raw = self._raw_for(folder, uid)
        if raw is None:
            return []
        msg = email.message_from_bytes(raw, policy=default_policy)
        _t, _h, attachment_parts = _walk_parts(msg)
        return [
            AttachmentFile(
                filename=str(part.get_filename() or f"anhang-{i}"),
                content_type=part.get_content_type(),
                payload=part.get_payload(decode=True) or b"",
            )
            for i, part in enumerate(attachment_parts)
        ]

    def get_attachment(self, folder: str, uid: int, index: int) -> AttachmentFile | None:
        files = self.get_attachment_files(folder, uid)
        return files[index] if index < len(files) else None

    def search(self, folder: str, query: str) -> list[ParsedMail]:
        from imapclient.exceptions import IMAPClientError

        self._client.select_folder(folder, readonly=True)
        charset = None if query.isascii() else "UTF-8"
        try:
            uids = sorted(self._client.search(["TEXT", query], charset))[-50:]
        except (IMAPClientError, UnicodeEncodeError):
            # Server ohne UTF-8-SEARCH (oder ascii-only-Pfad): lokale Filterung
            # über die letzten 200 Mails statt harter 500er.
            recent = sorted(self._client.search(["ALL"]))[-200:]
            needle = query.lower()
            mails = self._fetch_parsed(folder, recent)
            return sorted(
                (m for m in mails if needle in m.subject.lower() or needle in m.body_text.lower()),
                key=lambda m: m.uid,
                reverse=True,
            )
        return sorted(self._fetch_parsed(folder, uids), key=lambda m: m.uid, reverse=True)

    def _fetch_parsed(self, folder: str, uids: list[int]) -> list[ParsedMail]:
        if not uids:
            return []
        data = self._client.fetch(uids, ["BODY.PEEK[]", "FLAGS"])
        mails = []
        for uid in uids:
            item = data.get(uid) or {}
            raw = item.get(b"BODY[]")
            if not raw:
                continue
            seen = b"\\Seen" in tuple(item.get(b"FLAGS", ()))
            mails.append(parse_full(uid, raw, seen))
        return mails

    def _raw_for(self, folder: str, uid: int) -> bytes | None:
        self._client.select_folder(folder, readonly=True)
        data = self._client.fetch([uid], ["BODY.PEEK[]"])
        return (data.get(uid) or {}).get(b"BODY[]")

    # --- Struktur & Aktionen (nur durch UI-Aktionen erreichbar) ---

    def list_folders(self) -> list[str]:
        return [name for _f, _d, name in self._client.list_folders()]

    def _find_by_name(self, wanted: set[str]) -> str | None:
        for name in self.list_folders():
            leaf = name.split("/")[-1].split(".")[-1]
            if name.lower() in wanted or leaf.lower() in wanted:
                return name
        return None

    def _resolve(self, special_flag: bytes, names: set[str], fallback: str) -> str:
        folder = self._client.find_special_folder(special_flag) or self._find_by_name(names)
        if folder:
            return folder
        self._client.create_folder(fallback)
        return fallback

    def move(self, folder: str, uid: int, target: str, ensure: bool = False) -> None:
        self.move_many(folder, [uid], target, ensure)

    # imapclient joint UIDs unkomprimiert — sehr lange Listen sprengen die
    # IMAP-Kommandozeile mancher Server (~8 KB). Blockweise senden.
    _UID_CHUNK = 500

    def move_many(self, folder: str, uids: list[int], target: str, ensure: bool = False) -> None:
        """Bulk-Triage: IMAP-MOVE mit UID-Liste statt N Einzeloperationen."""
        if not uids:
            return
        if ensure and target not in set(self.list_folders()):
            self._client.create_folder(target)
        self._client.select_folder(folder, readonly=False)
        for i in range(0, len(uids), self._UID_CHUNK):
            self._client.move(uids[i : i + self._UID_CHUNK], target)

    def set_seen(self, folder: str, uid: int, seen: bool) -> None:
        self.set_seen_many(folder, [uid], seen)

    def set_seen_many(self, folder: str, uids: list[int], seen: bool) -> None:
        if not uids:
            return
        self._client.select_folder(folder, readonly=False)
        flag_op = self._client.add_flags if seen else self._client.remove_flags
        for i in range(0, len(uids), self._UID_CHUNK):
            flag_op(uids[i : i + self._UID_CHUNK], [b"\\Seen"], silent=True)

    def trash(self, folder: str, uid: int) -> None:
        self.move(folder, uid, self.trash_folder())

    def trash_folder(self) -> str:
        return self._resolve(b"\\Trash", _TRASH_NAMES, "Trash")

    def junk_folder(self) -> str:
        return self._resolve(b"\\Junk", _JUNK_NAMES, "Spam")

    SNOOZE_FOLDER = "Später"

    def find_by_message_id(self, folder: str, message_id: str) -> int | None:
        """UID einer Mail über die Message-ID — UIDs sind nach Moves wertlos,
        die Message-ID bleibt (Snooze-Aufwachen)."""
        self._client.select_folder(folder, readonly=True)
        uids = self._client.search(["HEADER", "Message-ID", message_id])
        return sorted(uids)[-1] if uids else None

    def archive_folder_default(self) -> str:
        return self._resolve(b"\\Archive", _ARCHIVE_NAMES, "Archive")

    def append_sent(self, mime_bytes: bytes) -> None:
        folder = self._sent_override or self._resolve(b"\\Sent", _SENT_NAMES, "Sent")
        self._client.append(folder, mime_bytes, flags=[b"\\Seen"])
