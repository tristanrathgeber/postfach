# Batch 4 — Konversations-Threads (Design)

Stand: 2026-07-21 · Contract-Addendum: v0.6 (in docs/api-contract.md)

Zusammengehörige Mails als ein Gesprächsfaden — inklusive der eigenen
Antworten aus „Gesendet". Der Composer setzt seit Batch 1 korrekte
In-Reply-To/References-Header; jetzt werden sie gelesen.

## Datenmodell (Entscheidung)

Threading lebt im Such-Index (`search.db`) — er ist die einzige kontoweite,
ordnerübergreifende Sicht und wird ohnehin bei jedem Scan/Push befüllt:

- `mails` + Spalten `message_id`, `thread_root` (indiziert).
- `thread_root` = erster Eintrag der References-Kette, sonst In-Reply-To,
  sonst eigene Message-ID. Das ist bewusst NICHT der volle JWZ-Algorithmus:
  References[0] identifiziert die Wurzel in >99 % realer Fäden; kaputte
  Ketten zerfallen in getrennte Fäden (ehrlich, nie falsch zusammengeklebt).
- **Betreff-Fallback** (Roadmap): Mails OHNE jede Referenz, deren
  normalisierter Betreff (Re:/Fwd:-Präfixe ab, getrimmt, lowercase) und
  Gegenseite (Absender ODER Empfänger) zu einem existierenden Faden passen,
  werden diesem zugeordnet — nur beim Index-Lauf, nie spekulativ zur
  Suchzeit. Konservativ: nur wenn GENAU EIN Kandidaten-Faden existiert.

Schema-Migration: `ALTER TABLE ... ADD COLUMN` (bestandsschonend); die
Spalten füllt der nächste Voll-Index. `threads ready` = Index ready.

## API (v0.6)

| Route | Verhalten |
|---|---|
| `GET /api/messages/{account}/{uid}/thread?folder=` | Der Faden der Mail: `[Summary]` chronologisch aufsteigend, über alle Ordner (aus dem Index). Enthält die Mail selbst. Ohne vollen Index oder ohne Thread-Daten: `[eigene Summary]` (Ein-Mail-Faden). |
| `GET /api/messages` | `Summary` zusätzlich: `"thread_count": number` (1 = Einzelmail; nur berechnet, wenn Index ready — sonst 1). EIN Bulk-Query pro Liste. |
| `POST /api/batch-action` | unverändert — Thread-Triage nutzt sie mit den UIDs des Fadens (der Client kennt sie aus der Thread-Route). |

## UI

- **Liste:** Zähler-Chip `(n)` an Zeilen mit thread_count > 1.
- **Reader:** Unter dem Kopf eine Konversationsleiste „Konversation (n)":
  alle Mails des Fadens chronologisch als kompakte, klickbare Zeilen
  (Absender · Datum · Ordner-Label; die geöffnete hervorgehoben). Klick
  öffnet die Mail im Reader (gleiches Fenster). Die Roadmap-Idee
  „einklappbare Einzelmails im Langtext" wird auf die Leiste + Ein-Klick-
  Navigation reduziert — schneller, robuster, kein HTML-Stitching.
- **Thread-Triage:** Kopf der Konversationsleiste bietet „Faden archivieren"
  und „Faden in den Papierkorb" (batch-action pro Ordner-Gruppe; Mails aus
  „Gesendet" bleiben unangetastet — die eigene Kopie räumt man nicht weg).

## Nicht in diesem Batch

Thread-Zusammenfassung per Emilia (Batch 7), Thread-Snooze (Batch 5),
Gmail-artiges Kollabieren der Mail-Bodies in einer Scroll-Ansicht.
