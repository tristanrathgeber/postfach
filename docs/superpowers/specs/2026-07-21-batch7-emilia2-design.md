# Batch 7 — Emilia II: Streaming, NL-Suche, Ton, Zusammenfassung, KI-Schalter (Design)

Stand: 2026-07-21 · Contract-Addendum: v0.9 (in docs/api-contract.md)

Leitplanke unverändert: Emilia liest und formuliert ausschließlich — kein Zugriff
auf Versand-/Verschiebe-/Lösch-Pfade (test_safety.py erzwingt das). Alle
LLM-Aufrufe lokal (Ollama). Mail-Inhalte sind UNTRUSTED (EMILIA_GUARD in jedem
Prompt).

## 1. Streaming-Antworten

`POST /api/emilia/chat/stream` liefert **NDJSON** (eine JSON-Zeile pro Ereignis,
`application/x-ndjson`): zuerst `{"sources":[…]}` (die Gedächtnis-Treffer, damit
die UI sie sofort zeigt), dann `{"delta":"…"}` pro Textstück, abschließend
`{"done":true}` — bei Fehlern mitten im Stream `{"error":"…"}` statt done.
SSE/EventSource scheidet aus (nur GET); die UI liest per `fetch` +
`ReadableStream`.

`OllamaBackend` (email-agent) bekommt eine `stream(system, prompt, purpose)`-
Generator-Methode (`/api/chat` mit `stream:true`, `think:false`). Postfach
fällt per `hasattr` auf `complete()` als Ein-Chunk-Stream zurück; die
`DemoEmiliaLLM` streamt wortweise (Demo zeigt echtes Streaming-Gefühl).
Der bisherige `POST /api/emilia/chat` bleibt unverändert bestehen (Contract).

## 2. Natürlichsprachige Suche

`GET /api/search/nl?account=&q=` → `{"query":"<Operator-Query>","hits":[…]}`.
Emilia übersetzt die natürliche Frage in unsere dokumentierten Suchoperatoren
(`von:/an:/betreff:/vor:/nach:/hat:anhang` + Volltext; Prompt enthält das
heutige Datum und Few-Shot-Beispiele, purpose=`nl_search`). Ausgeführt wird die
übersetzte Query über den NORMALEN FTS-Pfad — deterministisch, transparent,
und durch `parse_query` gequotet (die LLM-Ausgabe kann nichts injizieren,
unbekannte Operatoren sind schlicht Volltext-Literale). Nur bei `ready`-Index
(kein IMAP-Fallback für NL). Die UI zeigt die übersetzte Query als Chip
(„Emilia sucht: …") — Klick übernimmt sie ins Suchfeld zum Verfeinern.

**Suchmodus in der UI:** Beginnt die Eingabe mit `?` (z. B.
„? rechnungen von hetzner mit anhang"), läuft sie über die NL-Route; sonst
alles wie bisher. Placeholder erklärt das.

Demo: `DemoEmiliaLLM` übersetzt regelbasiert (Muster „von X", „mit anhang",
„rechnung(en)") — deterministisch testbar.

## 3. Sie/Du- & Ton-Umschalter (Verbessern II)

`_SYSTEM_IMPROVE` wächst um drei Modi: `sie` (durchgängig förmliches Sie,
Ton professionell, Inhalt unverändert), `du` (durchgängig Du, locker-freundlich,
Inhalt unverändert), `kuerzer` (auf das Wesentliche kürzen, Kernaussagen und
Ton behalten). `POST /api/emilia/improve` akzeptiert die neuen Modi; das
Composer-Menü zeigt: Korrigieren · Verbessern · Förmlich (Sie) · Locker (Du) ·
Kürzer. Deutschland-Feature: kein US-Client kann Sie/Du.

## 4. Langthread-Zusammenfassung auf Abruf

`POST /api/emilia/thread_summary` `{account, folder, uid}` →
`{"summary":"…","mails":n}`. Quelle ist der Such-Index: neue Methode
`search.thread_texts(account, root)` liefert chronologisch
`{from_name, date, body[:1500]}` je Mail (Bodies liegen im Index, kein
IMAP-Roundtrip). Prompt: nüchterne deutsche Zusammenfassung — wer will was,
was ist offen, was wurde entschieden; EMILIA_GUARD. UI: Knopf „Faden
zusammenfassen" in der ThreadRail ab 3 Mails, Ergebnis als einklappbarer
Block über dem Faden. NIEMALS automatisch (Gemini-Backlash) — nur auf Klick.

## 5. Globaler, sichtbarer KI-Aus-Schalter

`settings.ai_enabled` (Default `true`, Teil-Update-fähig wie alle Settings).
Aus heißt aus: `/api/classify`, `/api/classify/override` bleibt (reine
Nutzer-Aktion), `/api/draft`, alle `/api/emilia/*`-Routen und `/api/search/nl`
antworten 403 `{"detail":"KI ist in den Einstellungen deaktiviert"}`; die
Watcher-Pipeline klassifiziert nicht mehr (Cache bleibt lesbar — vorhandene
Kategorien verschwinden nicht). UI: Schalter prominent in den Einstellungen
(„Emilia & KI"), bei aus verschwinden Emilia-Knopf (⌘J), Composer-KI-Leiste,
NL-Suche; Kategorie-Badges aus dem Cache bleiben sichtbar.

## 6. Deutsches Embedding-Modell (vorbereitet, Download braucht Freigabe)

`emilia.embed_model` ist bereits konfigurierbar. Empfehlung:
`jina/jina-embeddings-v2-base-de` (~160 MB, deutsch+englisch, klar besser als
all-minilm für deutsche Mails). Umstieg = `ollama pull` + config-Zeile +
Neu-Index. Wird im Batch-Report als Ein-Befehl-Anleitung dokumentiert;
Ausführung erst nach Tristans Download-Freigabe.

## API (v0.9) — Kurzform

| Route | Zweck |
|---|---|
| `POST /api/emilia/chat/stream` | NDJSON: `{"sources"}` → `{"delta"}`× → `{"done"}`/`{"error"}` |
| `GET /api/search/nl?account=&q=` | `{"query", "hits"}` — nur bei ready-Index |
| `POST /api/emilia/improve` | Modi neu: `sie` \| `du` \| `kuerzer` |
| `POST /api/emilia/thread_summary` | `{account, folder, uid}` → `{"summary", "mails"}` |
| `PUT /api/settings` | neu: `ai_enabled` (Teil-Update) |

## Nicht in diesem Batch

Embedding-Modell-Download (Freigabe nötig), Streaming für improve/summary
(Ein-Shot reicht dort), NL-Suche ohne Index (IMAP-Fallback), automatische
Zusammenfassungen.
