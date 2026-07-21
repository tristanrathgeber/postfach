# Batch 5 — Zeit-Features: Undo, Später, Snooze, Follow-up (Design)

Stand: 2026-07-21 · Contract-Addendum: v0.7 (in docs/api-contract.md)

Alle vier Features teilen EINE Infrastruktur: eine lokale Job-Warteschlange
(`data/schedule.json`, Muster wie DraftStore) + ein Scheduler-Thread, der
fällige Jobs abarbeitet. Kern (`scheduler.py`) ist synchron testbar
(`process_due(now)`); der Thread tickt alle 20 s. Jobs sind idempotent und
überleben App-Neustarts. Demo bekommt denselben Scheduler (eigener Store).

## 1. Undo-Send (konfigurierbar, Default 15 s)

`POST /api/send` legt bei `settings.undo_seconds > 0` statt sofortigem
Versand einen `send`-Job an (due = jetzt + Verzögerung) und antwortet
`{"ok": true, "scheduled": {"id", "due", "kind": "undo"}}`. Payload inkl.
hochgeladener Anhänge landet in `data/outbox/<id>/` (JSON + Blobs).
Der zugehörige Entwurf wird erst beim TATSÄCHLICHEN Versand gelöscht —
Storno (`DELETE /api/outbox/{id}`) lässt ihn als Sicherheitsnetz stehen.
UI: Toast „Wird gesendet … Rückgängig (15 s)"; Rückgängig storniert und
öffnet den Entwurf wieder. Einstellung im Settings-Modal (0/10/15/20/30 s).

## 2. Später senden

Composer-Sekundäraktion „Später": Vorschläge (Heute 18:00, Morgen 08:00,
Montag 08:00) + freie Datum/Zeit-Wahl → gleicher `send`-Job mit fernem due.
Sidebar-Ansicht **„Ausgang (n)"** listet geplante Sends (Empfänger, Betreff,
Zeit) mit „Stornieren" (→ Entwurf bleibt) — nichts geht still raus.

## 3. Snooze auf Plain-IMAP (Marktlücke)

„Später"-Aktion auf einer Mail (Reader-Button + Taste `z`, Menü: Heute 18:00,
Morgen 08:00, Samstag 09:00, Montag 08:00, eigene Zeit):

- Mail wird in den Ordner **„Später"** verschoben (resolve/create).
- Job merkt sich **Message-ID** (nicht UID — IMAP vergibt beim Move neue
  UIDs, Batch-4-Lektion) + Betreff + due.
- Beim Fälligwerden: IMAP-SEARCH nach der Message-ID im „Später"-Ordner →
  zurück in die INBOX + als UNGELESEN markieren (neue hohe UID = erscheint
  oben) + macOS-Notification „Wiedervorlage: <Betreff>". Mail nicht mehr
  auffindbar (extern verschoben) → Job löschen, Notification mit Hinweis.

## 4. Follow-up-Reminder

Composer-Option „Erinnern, falls keine Antwort" (aus/3 Tage/1 Woche/eigene):
Beim Versand wird die Message-ID der ausgehenden Mail zum `followup`-Job
(build_outgoing liefert sie jetzt zurück). Beim Fälligwerden prüft der
Scheduler über den Thread-Index, ob im Faden eine FREMDE Mail neuer als der
Versandzeitpunkt existiert — wenn ja, löscht sich der Job still; wenn nein:
macOS-Notification + Eintrag in der Ansicht **„Wiedervorlage"** (Sidebar,
mit Badge): Betreff, Empfänger, „seit n Tagen ohne Antwort", Knöpfe
„Erledigt" und „Öffnen" (springt zum Faden).

## API (v0.7) — Kurzform

| Route | Zweck |
|---|---|
| `POST /api/send` | zusätzlich `"send_at"?: iso`, `"followup_days"?: number`; Antwort ggf. `{"ok","scheduled":{...}}` |
| `GET /api/outbox?account=` | geplante Sends |
| `DELETE /api/outbox/{id}` | Storno (Entwurf bleibt) |
| `POST /api/messages/{account}/{uid}/snooze` | `{"folder","until": iso}` |
| `GET /api/reminders?account=` | fällige + anstehende Follow-ups/Snoozes |
| `POST /api/reminders/{id}/done` | Erledigt |
| Settings | zusätzlich `"undo_seconds": number` (Default 15) |

Sicherheits-Invarianten unverändert: Der Scheduler versendet AUSSCHLIESSLICH
Jobs, die eine explizite UI-Aktion (Senden-Klick) angelegt hat; kein
KI-Pfad erreicht die Warteschlange (test_safety erweitert). Kein expunge.

## Nicht in diesem Batch

Snooze für ganze Fäden, wiederkehrende Erinnerungen, „Boomerang wenn
ungelesen", Kalender-Integration (Batch 8).
