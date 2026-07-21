"""SMTP-Versand — ausschließlich vom /api/send-Endpunkt aufgerufen (User-Klick).

tests/test_safety.py erzwingt, dass kein AI- oder Automatik-Pfad dieses Modul
importiert. 587 = STARTTLS, 465 = SSL.
"""

from __future__ import annotations

import email
import smtplib
from email.message import EmailMessage as MimeMessage
from email.policy import default as default_policy
from email.utils import getaddresses, make_msgid

from .config import MailAccount
from .mail_imap import ParsedMail

_TIMEOUT = 60


def _clean(value: str) -> str:
    """CR/LF aus Header-Werten entfernen — Werte kommen teils aus untrusted
    Quellen (z. B. Anhang-Dateinamen fremder Mails) und dürfen weder Header
    injizieren noch EmailMessage mit ValueError crashen lassen."""
    return value.replace("\r", " ").replace("\n", " ")


def build_outgoing(
    from_addr: str,
    to: list[str],
    cc: list[str],
    subject: str,
    body: str,
    reply_to_original: ParsedMail | None = None,
    bcc: list[str] | None = None,
    attachments: list[tuple[str, str, bytes]] | None = None,
) -> tuple[bytes, str]:
    """Threading-Header (In-Reply-To/References) werden HIER abgeleitet —
    RFC-5322-Wissen gehört in die Mail-Schicht, nicht in Routen.

    Bcc bleibt im MIME (für die Gesendet-Kopie); smtplib.send_message nimmt
    Bcc-Empfänger in den Envelope und entfernt den Header beim Versand selbst.
    attachments: (dateiname, content_type, bytes)."""
    mime = MimeMessage()
    mime["From"] = _clean(from_addr)
    mime["To"] = _clean(", ".join(to))
    if cc:
        mime["Cc"] = _clean(", ".join(cc))
    if bcc:
        mime["Bcc"] = _clean(", ".join(bcc))
    mime["Subject"] = _clean(subject)
    message_id = make_msgid()
    mime["Message-ID"] = message_id
    if reply_to_original is not None and reply_to_original.message_id:
        mime["In-Reply-To"] = reply_to_original.message_id
        mime["References"] = (
            f"{reply_to_original.references} {reply_to_original.message_id}".strip()
        )
    mime.set_content(body)
    for filename, content_type, payload in attachments or []:
        maintype, _, subtype = (content_type or "application/octet-stream").partition("/")
        mime.add_attachment(
            payload,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=_clean(filename),
        )
    return mime.as_bytes(), message_id


def send_mail(account: MailAccount, password: str, mime_bytes: bytes) -> None:
    msg = email.message_from_bytes(mime_bytes, policy=default_policy)
    # Bcc-Invariante am Transport erzwingen, nicht smtplib überlassen:
    # Empfänger explizit in den Envelope, Header vor dem Versand entfernen.
    recipients = [
        addr
        for _n, addr in getaddresses(
            msg.get_all("To", []) + msg.get_all("Cc", []) + msg.get_all("Bcc", [])
        )
        if addr
    ]
    del msg["Bcc"]
    transport = smtplib.SMTP_SSL if account.smtp_port == 465 else smtplib.SMTP
    with transport(account.smtp_host, account.smtp_port, timeout=_TIMEOUT) as smtp:
        if transport is smtplib.SMTP:
            smtp.starttls()
        smtp.login(account.address, password)
        smtp.send_message(msg, to_addrs=recipients)
