"""SMTP-Versand — ausschließlich vom /api/send-Endpunkt aufgerufen (User-Klick).

tests/test_safety.py erzwingt, dass kein AI- oder Automatik-Pfad dieses Modul
importiert. 587 = STARTTLS, 465 = SSL.
"""

from __future__ import annotations

import email
import smtplib
from email.message import EmailMessage as MimeMessage
from email.policy import default as default_policy
from email.utils import make_msgid

from .config import MailAccount
from .mail_imap import ParsedMail

_TIMEOUT = 60


def build_outgoing(
    from_addr: str,
    to: list[str],
    cc: list[str],
    subject: str,
    body: str,
    reply_to_original: ParsedMail | None = None,
) -> bytes:
    """Threading-Header (In-Reply-To/References) werden HIER abgeleitet —
    RFC-5322-Wissen gehört in die Mail-Schicht, nicht in Routen."""
    mime = MimeMessage()
    mime["From"] = from_addr
    mime["To"] = ", ".join(to)
    if cc:
        mime["Cc"] = ", ".join(cc)
    mime["Subject"] = subject
    mime["Message-ID"] = make_msgid()
    if reply_to_original is not None and reply_to_original.message_id:
        mime["In-Reply-To"] = reply_to_original.message_id
        mime["References"] = (
            f"{reply_to_original.references} {reply_to_original.message_id}".strip()
        )
    mime.set_content(body)
    return mime.as_bytes()


def send_mail(account: MailAccount, password: str, mime_bytes: bytes) -> None:
    msg = email.message_from_bytes(mime_bytes, policy=default_policy)
    transport = smtplib.SMTP_SSL if account.smtp_port == 465 else smtplib.SMTP
    with transport(account.smtp_host, account.smtp_port, timeout=_TIMEOUT) as smtp:
        if transport is smtplib.SMTP:
            smtp.starttls()
        smtp.login(account.address, password)
        smtp.send_message(msg)
