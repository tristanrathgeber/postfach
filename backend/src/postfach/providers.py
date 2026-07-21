"""Provider-Presets: IMAP/SMTP-Eckdaten deutscher (und gängiger) Anbieter.

Rein statische Daten — die UI füllt damit die technischen Felder vor, damit
niemand Hostnamen und Ports nachschlagen muss. `custom` = manuelle Eingabe.
Wichtig bei GMX/web.de: der SMTP-Host ist NICHT der IMAP-Host.
"""

from __future__ import annotations

# Reihenfolge = Anzeige-Reihenfolge (deutsche Anbieter zuerst).
PRESETS: dict[str, dict] = {
    "gmx": {
        "label": "GMX", "imap_host": "imap.gmx.net", "imap_port": 993,
        "smtp_host": "mail.gmx.net", "smtp_port": 587,
        "note": "IMAP muss im GMX-Webmail unter Einstellungen aktiviert sein.",
    },
    "web.de": {
        "label": "web.de", "imap_host": "imap.web.de", "imap_port": 993,
        "smtp_host": "smtp.web.de", "smtp_port": 587,
        "note": "IMAP muss im web.de-Webmail aktiviert sein.",
    },
    "t-online": {
        "label": "T-Online", "imap_host": "secureimap.t-online.de", "imap_port": 993,
        "smtp_host": "securesmtp.t-online.de", "smtp_port": 587,
        "note": "",
    },
    "posteo": {
        "label": "Posteo", "imap_host": "posteo.de", "imap_port": 993,
        "smtp_host": "posteo.de", "smtp_port": 587,
        "note": "",
    },
    "mailbox.org": {
        "label": "mailbox.org", "imap_host": "imap.mailbox.org", "imap_port": 993,
        "smtp_host": "smtp.mailbox.org", "smtp_port": 587,
        "note": "",
    },
    "freenet": {
        "label": "Freenet", "imap_host": "imap.freenet.de", "imap_port": 993,
        "smtp_host": "smtp.freenet.de", "smtp_port": 587,
        "note": "",
    },
    "gmail": {
        "label": "Gmail", "imap_host": "imap.gmail.com", "imap_port": 993,
        "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "note": "Braucht ein App-Passwort (nicht das normale Google-Passwort).",
    },
    "icloud": {
        "label": "iCloud", "imap_host": "imap.mail.me.com", "imap_port": 993,
        "smtp_host": "smtp.mail.me.com", "smtp_port": 587,
        "note": "Braucht ein App-spezifisches Passwort aus den Apple-ID-Einstellungen.",
    },
    "custom": {
        "label": "Anderer (manuell)", "imap_host": "", "imap_port": 993,
        "smtp_host": "", "smtp_port": 587,
        "note": "Host und Port beim Anbieter nachsehen.",
    },
}


def preset_list() -> list[dict]:
    return [{"id": pid, **data} for pid, data in PRESETS.items()]
