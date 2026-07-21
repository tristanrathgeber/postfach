"""Demo-Modus: In-Memory-Postfach mit deutschen Beispielmails + regelbasierter Fake-AI.

Zweck: UI ohne Credentials ausprobieren und Ende-zu-Ende testen. Gleiche
Schnittstelle wie Mailbox (Duck-Typing), gleiche Vertragsgarantien.
"""

from __future__ import annotations

import email
from dataclasses import replace
from email.policy import default as default_policy

from .mail_imap import AttachmentFile, AttachmentMeta, ParsedMail

_PDF = b"%PDF-1.4\n% Demo-Rechnung Postfach\n%%EOF\n"

_NEWSLETTER_HTML = (
    '<h1>3D Print Weekly</h1><img src="https://cdn.example/banner.png" alt="Banner">'
    '<p>Diese Woche: <b>PETG-CF im H&auml;rtetest</b>, neue Slicer-Profile und '
    'ein Bambu-Firmware-Deep-Dive.</p><a href="https://3dprintweekly.example/47">Zur Ausgabe</a>'
)


def _mail(uid, subject, from_name, from_addr, body, *, seen=True, html=None, headers=None, attachments=(), references="", date_iso=None, to=("alex@demo.example",)):
    return ParsedMail(
        uid=uid,
        subject=subject,
        from_name=from_name,
        from_addr=from_addr,
        to=tuple(to),
        cc=(),
        reply_to=None,
        message_id=f"<demo-{uid}@demo.example>",
        references=references,
        date_iso=date_iso or f"2026-07-19T09:{uid % 60:02d}:00+02:00",
        seen=seen,
        body_text=body,
        body_html_raw=html,
        attachments=tuple(attachments),
        headers=headers or {},
    )


def _sample_inbox() -> list[ParsedMail]:
    return [
        _mail(114, "Vereinsheim Schlüssel", "Martin Becker", "m.becker@web.example",
              "Hi Alex, hast du den Schlüssel fürs Vereinsheim? Ich komme sonst nicht rein.\nVG Martin"),
        _mail(112, "3D Print Weekly #47 — PETG-CF im Härtetest", "3D Print Weekly", "newsletter@3dprintweekly.example",
              "PETG-CF im Härtetest, neue Slicer-Profile, Bambu-Firmware.", seen=False, html=_NEWSLETTER_HTML,
              headers={"list-unsubscribe": "<https://3dprintweekly.example/unsub>"}),
        _mail(111, "Ihr Style-Update: Sommertrends 2026", "ModeHaus", "news@modehaus.example",
              "20 % auf alles! Die neuen Sommertrends sind da.",
              headers={"list-unsubscribe": "<https://modehaus.example/abmelden>"}),
        _mail(110, "Training am Samstag?", "Martin Becker", "m.becker@web.example",
              "Hi Alex, kannst du am Samstag die Trainingsgruppe übernehmen? Ich bin im Urlaub. VG Martin", seen=False),
        _mail(109, "Ihre Telekom Rechnung Juli 2026", "Telekom", "rechnung@telekom.example",
              "Ihre Rechnung über 39,95 € finden Sie im Anhang.",
              attachments=[AttachmentMeta(0, "Rechnung Juli 39,95€.pdf", "application/pdf", len(_PDF))]),
        _mail(108, "Deine Bestellung wurde versandt", "Amazon", "versand@amazon.example",
              "Dein Paket mit PETG-Filament (2 kg) ist unterwegs. Zustellung: Montag."),
        _mail(107, "[makrhub] PR #142: fix pricing rounding", "GitHub", "notifications@github.example",
              "dein-account merged 3 commits into main."),
        _mail(106, "Vereinsinfo: Sommerfest & Trainingszeiten", "SFC Nahetal", "info@sfcnahetal.example",
              "Liebe Mitglieder, das Sommerfest findet am 15.08. statt. Die Trainingszeiten in den Ferien…", seen=False),
        _mail(105, "Terminbestätigung: Prophylaxe am 24.07., 14:30", "Zahnarztpraxis Dr. Weber", "praxis@drweber.example",
              "Wir bestätigen Ihren Termin am 24.07.2026 um 14:30 Uhr."),
        _mail(104, "Nur heute: 30 % auf Elektronik", "TechDeals", "sale@techdeals.example",
              "Blitzangebote! 30 % Rabatt auf Netzteile, Sensoren, Mikrocontroller.",
              headers={"list-unsubscribe": "<mailto:abmelden@techdeals.example?subject=unsubscribe>"}),
        _mail(103, "Rückfrage zur EÜR 2025", "StB Kanzlei Sommer", "kanzlei@sommer-stb.example",
              "Guten Tag, für den Abschluss fehlt uns noch der Beleg zur Abschreibung des Druckers. "
              "Können Sie ihn uns bis Freitag senden?", seen=False),
        _mail(102, "Ihre Hosting-Rechnung 07/2026", "Hetzner", "billing@hetzner.example",
              "Ihre Rechnung über 14,28 € wurde erstellt.",
              attachments=[AttachmentMeta(0, "hetzner-072026.pdf", "application/pdf", len(_PDF))]),
        _mail(101, "Paket bei mir abgegeben", "Sabine Krause", "s.krause@mail.example",
              "Hallo Alex, dein Paket liegt bei mir. Komm einfach nach 18 Uhr vorbei."),
    ]


class DemoMailbox:
    def __init__(self) -> None:
        self._folders: dict[str, list[ParsedMail]] = {
            "INBOX": _sample_inbox(),
            "Gesendet": [
                # Echte Empfänger: der Screener leitet „bekannt" aus den
                # Gesendet-Empfängern ab — Martin & Co. sind keine Erstkontakte.
                _mail(11, "Re: Vereinsheim Schlüssel", "Alex", "alex@demo.example",
                      "Hi Martin,\n\nklar, ich bringe den Schlüssel mit.\n\nViele Grüße\nAlex",
                      references="<demo-114@demo.example>", date_iso="2026-07-19T10:30:00+02:00",
                      to=("m.becker@web.example",)),
                _mail(10, "Beleg Abschreibung Drucker", "Alex", "alex@demo.example",
                      "Guten Tag, anbei der Beleg zur Abschreibung.\n\nViele Grüße\nAlex Demo",
                      date_iso="2026-07-15T09:00:00+02:00",
                      to=("kanzlei@sommer-stb.example",)),
            ],
            "Papierkorb": [],
            "Archive": [],
            "Spam": [],
        }
        self._next_uid = 500

    # --- Lesen ---

    def list_messages(self, folder: str, limit: int) -> list[ParsedMail]:
        mails = self._folders.get(folder, [])
        return sorted(mails, key=lambda m: m.uid, reverse=True)[:limit]

    def get_message(self, folder: str, uid: int) -> ParsedMail | None:
        for mail in self._folders.get(folder, []):
            if mail.uid == uid:
                return mail
        return None

    def get_messages(self, folder: str, uids: list[int]) -> list[ParsedMail]:
        wanted = set(uids)
        return [m for m in self._folders.get(folder, []) if m.uid in wanted]

    def exists(self, folder: str, uid: int) -> bool:
        return self.get_message(folder, uid) is not None

    def get_attachment_files(self, folder: str, uid: int) -> list[AttachmentFile]:
        mail = self.get_message(folder, uid)
        return [
            AttachmentFile(filename=meta.filename, content_type=meta.content_type, payload=_PDF)
            for meta in (mail.attachments if mail else ())
        ]

    def get_attachment(self, folder: str, uid: int, index: int) -> AttachmentFile | None:
        files = self.get_attachment_files(folder, uid)
        return files[index] if index < len(files) else None

    def search(self, folder: str, query: str) -> list[ParsedMail]:
        needle = query.lower()
        return [
            m for m in self.list_messages(folder, 200)
            if needle in m.subject.lower() or needle in m.body_text.lower()
        ]

    # --- Struktur & Aktionen ---

    def list_folders(self) -> list[str]:
        return list(self._folders)

    def move(self, folder: str, uid: int, target: str, ensure: bool = False) -> None:
        mail = self.get_message(folder, uid)
        if mail is None:
            return
        self._folders[folder] = [m for m in self._folders[folder] if m.uid != uid]
        self._folders.setdefault(target, []).append(mail)

    def move_many(self, folder: str, uids: list[int], target: str, ensure: bool = False) -> None:
        for uid in uids:
            self.move(folder, uid, target, ensure)

    def set_seen(self, folder: str, uid: int, seen: bool) -> None:
        self._folders[folder] = [
            replace(m, seen=seen) if m.uid == uid else m for m in self._folders.get(folder, [])
        ]

    def set_seen_many(self, folder: str, uids: list[int], seen: bool) -> None:
        for uid in uids:
            self.set_seen(folder, uid, seen)

    def trash(self, folder: str, uid: int) -> None:
        self.move(folder, uid, "Papierkorb")

    def archive_folder_default(self) -> str:
        return "Archive"

    def trash_folder(self) -> str:
        return "Papierkorb"

    def junk_folder(self) -> str:
        return "Spam"

    SNOOZE_FOLDER = "Später"

    def find_by_message_id(self, folder: str, message_id: str) -> int | None:
        for mail in self._folders.get(folder, []):
            if mail.message_id == message_id:
                return mail.uid
        return None

    def append_sent(self, mime_bytes: bytes) -> None:
        msg = email.message_from_bytes(mime_bytes, policy=default_policy)
        self._next_uid += 1
        self._folders["Gesendet"].append(
            _mail(
                self._next_uid,
                str(msg.get("Subject", "")),
                "Alex",
                "alex@demo.example",
                str(msg.get_content() if not msg.is_multipart() else ""),
            )
        )

    def logout(self) -> None:
        pass


class DemoEmiliaLLM:
    """Deterministische Emilia-Antworten ohne Ollama (Demo-Modus)."""

    def complete(self, system: str, prompt: str, purpose: str) -> str:
        if purpose == "improve":
            return prompt.replace("Rechung", "Rechnung").replace("bezalen", "bezahlen")
        return (
            "Demo-Antwort von Emilia: Im echten Betrieb beantworte ich das lokal "
            "über dein Mail-Gedächtnis (llama3.2 + all-minilm)."
        )


def demo_classify(mails: list[ParsedMail]) -> dict[int, dict]:
    """Deterministische Regel-Klassifikation für den Demo-Modus (kein LLM).

    Bulk-Erkennung über dieselbe Heuristik wie die echte Pipeline
    (email_agent.heuristics), damit Demo- und Realverhalten nicht driften.
    """
    from email_agent.heuristics import bulk_signals

    from .ai import to_agent_message

    result: dict[int, dict] = {}
    for m in mails:
        haystack = (m.subject + " " + m.from_addr + " " + m.body_text).lower()
        newsletter = bool(bulk_signals(to_agent_message(m)))
        interesting = newsletter and any(k in haystack for k in ("3d", "print", "maker"))
        needs_reply = not newsletter and ("?" in m.body_text and "@web." in m.from_addr or "können sie" in haystack)
        if any(k in haystack for k in ("github", "vercel", "deploy")):
            category = "Entwicklung"
        elif newsletter:
            category = "Newsletter-Interessant" if interesting else "Newsletter"
        elif "rechnung" in haystack:
            category = "Rechnungen"
        elif any(k in haystack for k in ("bestellung", "versandt", "paket unterwegs")):
            category = "Bestellungen"
        elif any(k in haystack for k in ("verein", "sommerfest", "training")):
            category = "Aktion-nötig" if needs_reply or "?" in m.subject else "Verein"
        elif "termin" in haystack:
            category = "Termine"
        elif any(k in haystack for k in ("rabatt", "sale", "%")):
            category = "Werbung"
        elif needs_reply:
            category = "Aktion-nötig"
        else:
            category = "Sonstiges"
        if category == "Aktion-nötig":
            needs_reply = True
        result[m.uid] = {
            "category": category,
            "is_newsletter": newsletter,
            "interesting": interesting,
            "needs_reply": needs_reply,
            "reason": "Demo-Klassifikation (regelbasiert)",
        }
    return result
