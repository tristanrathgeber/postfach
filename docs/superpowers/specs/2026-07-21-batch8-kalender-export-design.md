# Batch 8 — Kalender-Minimum & Export (Design)

Stand: 2026-07-21 · Contract-Addendum: v0.10 (in docs/api-contract.md)

Drei unabhängige, lokal laufende Features, die zusammen den „letzten Meter"
zwischen Mail und Alltag schließen. Alle Verarbeitung passiert offline; ICS-
Inhalte sind UNTRUSTED (defensive Parser, kein Code-Pfad vertraut ihnen).

## 1. ICS-Einladungen inline (RSVP)

**Erkennen:** Der Parser (`mail_imap.parse_full`) erfasst zusätzlich den
`text/calendar`-Teil einer Mail als `ParsedMail.calendar_raw: str | None`
(bevorzugt der Teil mit `METHOD:REQUEST`; Kalender-Anhänge `.ics` zählen mit).
`ParsedMail` bleibt transient — keine Persistenz-/Index-Änderung.

**Parsen** (`invites.py`, mit `icalendar` — Zeitzonen/Faltung/Escaping sind
handgeschrieben fehleranfällig): `parse_invite(calendar_raw) -> Invite | None`
mit `summary, start, end, all_day, location, organizer_name, organizer_email,
method, uid, sequence`. Fehlerhafte/leere ICS → `None` (nie ein 500).

**Anzeigen:** Die Detail-Route (`GET /messages/{account}/{uid}`) liefert ein
`invite`-Objekt, wenn `method == REQUEST`. Die UI zeigt eine Einladungskarte
im Reader (Titel, Zeitraum lesbar, Ort, Organisator) mit drei Knöpfen
**Zusagen · Vielleicht · Absagen**.

**Antworten:** `POST /api/invite/respond` `{account, folder, uid, response:
accepted|tentative|declined}` baut eine RFC-5546-`METHOD:REPLY` (eigener
ATTENDEE mit `PARTSTAT`, Original-UID/SEQUENCE/DTSTART echoen; via
`build_invite_reply` in `mail_send.py`: `multipart/mixed` aus Text +
`text/calendar; method=REPLY`) und sendet sie an den Organisator über den
NORMALEN Versandpfad (`state.smtp_send`, Sent-Ablage). Das ist eine explizite
Nutzer-Aktion (Button) — die einzige erlaubte Send-Quelle; AI-Pfade bleiben
außen vor (test_safety deckt das mit ab). Kein Followup, kein Draft-Löschen.
Demo: smtp_send = No-Op, Antwort landet in „Gesendet".

## 2. Mail → Markdown/Obsidian-Export

`GET /messages/{account}/{uid}/export?folder=` → `{filename, markdown}`.
Markdown mit YAML-Frontmatter (`title, from, date, to, tags: [mail]`) + Body
(bevorzugt `body_text`, sonst `html_to_text`). Dateiname aus Betreff
saniert (`obsidian`-tauglich, keine `/ : \\`, `.md`). Die UI bietet im Reader
**„Als Markdown"**: Kopieren in die Zwischenablage + Download der `.md`-Datei
(Blob, kein Server-Roundtrip fürs Speichern). Reine lokale Umwandlung.

## 3. Struktur-Extraktion lokal (Chips)

`extract.py`: `extract_entities(text) -> list[Entity]` — regelbasiert, KEIN
LLM (schnell, deterministisch, offline). Erkennt:
- **Termine**: deutsche Datums-/Zeitformate (`24.07.2026`, `24. Juli`,
  `14:30 Uhr`) → Chip „Termin".
- **Beträge**: `39,95 €`, `€ 1.200,00`, `EUR 14,28` → Chip „Betrag".
- **Sendungsnummern**: DHL (20-stellig / JD…), DPD, GLS, Hermes, UPS
  (`1Z…`) über bekannte Muster → Chip „Sendung" mit Link auf die
  Tracking-Seite des jeweiligen Anbieters (HOST-Allowlist, kein aus der
  Mail übernommenes Ziel — nur Nummer in bekannte URL eingesetzt).

Die Detail-Route hängt `entities` an (aus `body_text`, gedeckelt). Die UI
zeigt sie als klickbare Chip-Zeile über dem Mail-Body: Termin/Betrag →
Kopieren; Sendung → Tracking-Link (`target=_blank rel=noreferrer`). Nie
etwas automatisch öffnen.

## API (v0.10) — Kurzform

| Route | Zweck |
|---|---|
| `GET /messages/{account}/{uid}` | Detail zusätzlich mit `invite` (nullable) + `entities[]` |
| `POST /api/invite/respond` | `{account, folder, uid, response}` → RSVP senden; `{ok, warning?}` |
| `GET /messages/{account}/{uid}/export?folder=` | `{filename, markdown}` |

`Invite` = `{summary, start, end, all_day, location, organizer_name,
organizer_email, method, uid}`. `Entity` = `{kind: "date"|"amount"|
"tracking", text, value, url?}`.

## Nicht in diesem Batch

Eigene Kalender-Ansicht/Speicherung (bewusst nur RSVP — „Kalender-App-Falle"
vermeiden), wiederkehrende Termine (RRULE nur anzeigen, nicht auflösen),
Kalender-Abo/CalDAV, Export ganzer Ordner (nur Einzelmail), ICS-Erzeugung
für eigene neue Termine.
