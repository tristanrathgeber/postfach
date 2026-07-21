# Batch 1 — Schreiben komplett (Design)

**Datum:** 2026-07-21 · **Status:** Beschlossen · Fahrplan: `docs/ROADMAP.md` Batch 1

## Umfang & Entscheidungen

| Feature | Entscheidung |
|---|---|
| **Weiterleiten** | Composer-Modus `forward` (`f`-Taste): Betreff „Fwd: …" (Präfix-Regel inkl. WG/Fwd), Body = Zitatblock (Von/Datum/Betreff/An + Originaltext). Anhänge des Originals werden **serverseitig** mitgeschickt (`forward_of` im Send-Request — kein erneuter Upload). |
| **BCC** | Feld im Composer. SMTP: `smtplib.send_message` nimmt Bcc-Empfänger in den Envelope und entfernt den Header beim Versand automatisch; die **Gesendet-Kopie behält Bcc** (wie Gmail), damit man später sieht, wer ihn bekam. |
| **Signaturen** | Pro Konto, **Plain-Text** (v1 — Composer ist Text-first; HTML mit Design-Batch). Ablage `data/settings.json`, Bearbeitung in neuem **Einstellungen-Dialog** (Zahnrad). Automatisch angefügt mit `-- `-Trenner; bei Antworten/Weiterleitungen VOR dem Zitat. |
| **Entwürfe** | **Lokal** (`data/drafts.json`): Auto-Save (debounced) bei jeder Änderung, Composer-Schließen verliert nie Text. Sidebar-Ansicht „Entwürfe" (lokal) mit Öffnen/Fortsetzen/Löschen (lokales Artefakt — kein Server-Mail-Löschen, Invariante unberührt). Begründung gegen IMAP-Drafts: IMAP kann Drafts nicht updaten, echte Clients löschen dafür Altversionen — kollidiert mit unserer Garantie. IMAP-Sync als spätere Option. |
| **Anhänge senden** | Dateiauswahl + **Drag & Drop** auf den Composer. `/api/send` akzeptiert zusätzlich multipart (`payload`-JSON + `files[]`). Limit 25 MB gesamt, klare Fehlermeldung. |
| **Kontakte-Autocomplete** | Lokal aus dem Mailbestand: beim Indexieren/Push werden From/To/Cc in eine Kontakte-Tabelle (memory.db) geerntet; Empfänger eigener Sent-Mails zählen doppelt. To/CC/BCC werden **Chip-Felder** mit Vorschlags-Dropdown (Pfeiltasten/Enter, Häufigkeit×Aktualität-Ranking). |
| **Snippets** | `data/snippets.json`, Verwaltung im Einstellungen-Dialog. Auslösung: `;kürzel` + Tab im Body (Superhuman-Muster) sowie über ⌘K. Variablen v1: `{vorname}` (erster Empfänger), `{datum}` (de-DE heute). |

## API-Nachtrag v0.3 (eingefroren, additiv)

```
GET  /api/settings                 → {"signatures": {"<konto>": string}}
PUT  /api/settings                 {"signatures": {...}} → {"ok": true}
GET  /api/contacts?q=&limit=8      → [{"name": string, "addr": string}]
GET  /api/drafts?account=          → [Draft]   Draft = {id, account, to, cc, bcc,
                                     subject, body, mode: "new"|"reply"|"forward",
                                     ref_folder?, ref_uid?, updated: iso}
POST /api/drafts                   Draft ohne id/updated → {"id": string}
DELETE /api/drafts/{id}            → {"ok": true}
GET  /api/snippets                 → [{"abbrev", "title", "text"}]
PUT  /api/snippets                 [items] → {"ok": true}

POST /api/send                     zusätzlich multipart/form-data:
                                   Feld "payload" = bisheriges JSON + {"bcc": [],
                                   "forward_of": {"folder","uid","include_attachments"}},
                                   Felder "files" = Anhänge. JSON-Variante bleibt gültig.
```

## Sicherheit/Invarianten
Unverändert: Senden nur per UI-Doppelklick; KI ohne Send/Move/Trash; Anhang-Uploads
bleiben lokal (multipart an 127.0.0.1). Entwürfe/Snippets/Signaturen sind lokale
Dateien (gitignored, Export = Dateikopie). Draft-DELETE betrifft nur lokale Artefakte.

## Tests
Backend TDD: Forward-MIME (Quoting, Fwd:-Regel, Anhang-Übernahme), BCC (Envelope vs.
Sent-Kopie), Signatur-Anfügung (Position bei Reply), Drafts-Store (CRUD, Auto-Save-
Semantik), Snippets-Store + Variablen, Kontakte-Ernte (Ranking, Sent-Gewichtung),
multipart-Send (Limit, Dateinamen). Frontend: tsc/Build + Browser-E2E aller sieben
Features; abschließend adversarialer Review-Workflow.
