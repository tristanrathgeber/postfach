# Batch 3 — Lokale Volltextsuche (Design)

Stand: 2026-07-21 · Contract-Addendum: v0.5 (in docs/api-contract.md)

Suche ist der #1-Wechselgrund bei Mail-Apps (Markt-Recherche 07/2026). Ziel:
Treffer in < 50 ms über 100k Mails, über ALLE Ordner eines Kontos, mit
Operatoren — lokal, ohne Server-Roundtrip zur Suchzeit.

## Architektur

**Neues Modul `search.py`** mit eigener SQLite-DB `data/search.db`
(Demo: `data/demo/search.db`):

- Tabelle `mails(account, folder, uid, subject, from_name, from_addr,
  recipients, date_iso, has_attachments, seen, snippet)` mit
  PRIMARY KEY (account, folder, uid).
- FTS5-Tabelle `mails_fts(subject, from_text, recipients, body)` als
  external-content auf `mails` gekoppelt (rowid), Tokenizer
  `unicode61 remove_diacritics 2` (Umlaute korrekt; „muller" findet „Müller"),
  `prefix='2 3'` für Tipp-Suche.
- Body wird auf 32 kB gekappt (FTS-Index-Größe; längere Bodies sind
  praktisch immer Anhang-/HTML-Reste).

**Befüllung — Orchestrierung liegt in Route/Hook, nicht in Emilia**
(Altitude-Lektion aus Batch 2):

- `POST /api/emilia/index` füttert beide: Emilia-Gedächtnis UND Such-Index
  (die Mails sind ohnehin geladen). Doku: „index" = Voll-Index für Gedächtnis+Suche.
- Der Watcher-Hook indexiert neue Mails live mit (derselbe eine Fetch).
- Move-Aktionen (archive/trash/spam/unspam, einzeln und Batch) ziehen den
  Index-Eintrag Best Effort in den Zielordner um (`move_mails`) — der Index
  bleibt zwischen Voll-Läufen brauchbar aktuell. `read/unread` aktualisiert
  `seen` im Index NICHT (kosmetisch, nächster Voll-Lauf korrigiert).

## Query-Sprache

`parse_query(q)` (pure Funktion, deutsch dokumentiert):

| Operator | Bedeutung |
|---|---|
| `von:tanja` | Absender (Name oder Adresse) |
| `an:info@x.de` | Empfänger (to/cc) |
| `betreff:rechnung` | nur im Betreff |
| `vor:2026-07-01` / `nach:2026-01-01` | Datum (ISO, lexikografisch) |
| `hat:anhang` | nur Mails mit Anhang |
| `"exakte phrase"` | Phrase |
| Rest | Volltext über Betreff+Absender+Empfänger+Body |

**FTS-Injection:** Nutzertext wird NIE roh in den MATCH-String gebaut —
jedes Token wird als `"…"`-Literal gequotet (FTS-Syntax AND/OR/NEAR/* ist
sonst von außen steuerbar → Fehler/Verhalten). Doppelquotes im Token werden
verdoppelt. Datums-/hat-Filter laufen als WHERE-Klauseln, nicht durch FTS.

## API (v0.5)

`GET /api/search?account=&q=&folder=` — Response bleibt `Summary[]`
(kein Frontend-Bruch). NEU:

- Der lokale Index ist die primäre Quelle und sucht über ALLE Ordner des
  Kontos (Treffer tragen ihren echten `folder`); `folder=` wird zum
  optionalen Filter statt Pflicht-Scope.
- Ranking: FTS5 bm25, Betreff > Absender/Empfänger > Body gewichtet;
  bei gleichem Score neuere zuerst. Limit 50.
- Ist der Index für das Konto leer (nie indexiert), fällt die Route auf die
  bestehende IMAP-Suche im übergebenen Ordner zurück — Verhalten wie v0.4.
- `seen`/`has_attachments` kommen aus dem Index (Stand des letzten
  Index-Laufs; `seen` kann kurz stale sein — bewusst akzeptiert).
- `GET /api/search/status?account=` → `{"indexed": n}` (UI-Hinweis, ob die
  schnelle Suche aktiv ist).

## Frontend

- Suche funktioniert unverändert über das Suchfeld (`/`); Platzhalter zeigt
  die Operatoren an, ein Hinweis unter dem Feld bei aktiver Suche
  („Suche im ganzen Konto · von: an: betreff: vor: nach: hat:anhang").
- Trefferzeilen zeigen den Ordner der Mail (kleines Mono-Label), weil
  Treffer jetzt aus allen Ordnern kommen.

## Performance

Ziel < 50 ms bei 100k. Test: synthetischer Bestand (5k Mails) im Unit-Test,
Suche < 200 ms (CI-Toleranz); real gemessen auf Tristans Bestand (6,4k) im
E2E. FTS5 mit external content + prefix-Index liegt typisch bei einstelligen
Millisekunden.

## Nicht in diesem Batch

Suchhistorie/gespeicherte Suchen (View-Builder-Batch), Fuzzy/Tippfehler-
Toleranz, Index-Verschlüsselung, `ist:ungelesen`-Operator (kommt mit
zuverlässigem seen-Sync).
