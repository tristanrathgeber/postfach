"""Mail → Markdown (Obsidian-tauglich): YAML-Frontmatter + Klartext-Body.

Reine lokale Umwandlung — die UI lädt das Ergebnis als .md-Datei herunter oder
kopiert es. Frontmatter-Werte werden entschärft (Doppelpunkte/Zeilenumbrüche),
damit das YAML gültig bleibt.
"""

from __future__ import annotations

import re

from email_agent.textutil import html_to_text

from .mail_imap import ParsedMail

_INVALID_FILENAME = re.compile(r'[\\/:*?"<>|\n\r\t]+')


def _slug(subject: str) -> str:
    name = _INVALID_FILENAME.sub(" ", subject or "").strip()
    name = re.sub(r"\s+", " ", name)[:80].strip()
    return (name or "Mail") + ".md"


def _yaml_value(value: str) -> str:
    """YAML-sicher als Double-Quote-Scalar: Backslash ZUERST escapen (sonst
    ist `C:\\temp` oder ein abschließender `\\` ungültiges YAML), dann eigene
    Anführungszeichen ersetzen und Whitespace/Zeilenumbrüche falten."""
    clean = (value or "").replace("\\", "\\\\").replace('"', "'")
    clean = re.sub(r"\s+", " ", clean).strip()
    return f'"{clean}"'


def to_markdown(mail: ParsedMail) -> tuple[str, str]:
    """(filename, markdown). Body bevorzugt Klartext, sonst HTML→Text."""
    body = mail.body_text.strip() or (
        html_to_text(mail.body_html_raw).strip() if mail.body_html_raw else ""
    )
    recipients = ", ".join(mail.to) if mail.to else ""
    frontmatter = "\n".join(
        [
            "---",
            f"title: {_yaml_value(mail.subject)}",
            f"from: {_yaml_value(f'{mail.from_name} <{mail.from_addr}>'.strip())}",
            f"to: {_yaml_value(recipients)}",
            f"date: {_yaml_value(mail.date_iso)}",
            "tags: [mail]",
            "---",
        ]
    )
    heading = f"# {mail.subject.strip() or '(Kein Betreff)'}"
    return _slug(mail.subject), f"{frontmatter}\n\n{heading}\n\n{body}\n"
