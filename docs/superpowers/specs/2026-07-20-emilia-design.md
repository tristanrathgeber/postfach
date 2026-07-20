# Emilia — lokaler Mail-Copilot (Design)

**Datum:** 2026-07-20 · **Status:** Beschlossen · Ergänzt die Postfach-v0.1-Spec.

## Idee

„Emilia" ist der lokale KI-Agent in Postfach: Sie sortiert, formuliert vor, beantwortet
Fragen zum Mail-Bestand und verbessert selbst geschriebene Mails — **vollständig auf
Tristans Rechner** (Ollama: `llama3.2` fürs Sprechen, `all-minilm:l6-v2` fürs Erinnern).
Mail-Inhalte verlassen für Emilia-Funktionen nie den Rechner.

## Fähigkeiten v1

| Fähigkeit | Umsetzung |
|---|---|
| **Sortieren (lokal)** | Schalter `emilia.sort_local: true` → die bestehende Klassifikation läuft über Ollama statt Claude. Entwürfe bleiben per Default auf Claude (3B-Qualität reicht fürs Einordnen, nicht fürs Schreiben; `emilia.draft_local` zum Umstellen). |
| **Mail-Gedächtnis (RAG)** | Indexer holt alle Mails der Hauptordner (read-only), speichert Metadaten + Text-Snippet + Embedding in `data/memory.db` (SQLite). Frage → Embedding → Cosine-Top-K → llama3.2 antwortet auf Deutsch **mit Quellen** (klickbare Mail-Chips im Panel). |
| **Chat-Panel** | Rechte Seitenleiste („Emilia", ⌘J), Chat-Verlauf sessionlokal, Kontext der geöffneten Mail wird mitgegeben. |
| **Verbessern/Korrigieren** | Zwei Buttons im Composer → `/api/emilia/improve` (Modus `korrigieren` = nur Fehler, `verbessern` = Stil + Fehler). Ergebnis ersetzt den Text; Original per Rückgängig-Toast. |

## Sicherheitsmodell (unverändert hart)

Emilia **liest und formuliert nur**: keinerlei Send-/Move-/Trash-Pfade aus Emilia-Code
erreichbar (Safety-Test erweitert). RAG-Kontext ist untrusted → Injection-Guard, kein
Tool-Zugriff des LLM. Das Gedächtnis (`data/memory.db`) ist lokal und gitignored.

## API-Nachtrag (eingefroren)

```
POST /api/emilia/chat    {account, message, folder?, uid?}
                         → {reply, sources: [{account, folder, uid, subject, from_name, date}]}
POST /api/emilia/improve {text, mode: "korrigieren"|"verbessern"} → {text}
POST /api/emilia/index   {account} → {indexed}
GET  /api/emilia/status  → {model, embed_model, indexed_mails, sort_local}
```

Demo-Modus: deterministischer Fake (kein Ollama nötig), gleiche Endpunkte.

## Konfiguration (`config/config.yaml`)

```yaml
emilia:
  model: llama3.2            # lokales Chat-/Korrektur-Modell
  embed_model: all-minilm:l6-v2
  sort_local: true           # Klassifikation lokal (Wunsch: „lokale KI sortiert")
  draft_local: false         # Antwortentwürfe weiter über Claude (Qualität)
```

Empfehlung dokumentiert: ein stärkeres lokales Modell (z. B. `qwen3:8b`, ~5 GB Download)
verbessert Chat/Verbessern deutlich — Download nur nach expliziter Freigabe.

## Tests

Memory-Store (Insert/Suche/Cosine, Fake-Embedder), Chat-Route (Fake-LLM: Quellen aus
Top-K, Injection-Guard im Prompt), Improve-Route (Modus-Prompts, Textlängen-Schutz),
Index-Route (idempotent, zählt), Status, Safety (Emilia-Module ohne Send/Move-Pfade),
Demo-Fake deterministisch. E2E: real gegen lokales Ollama + Browser-Klickstrecke.
