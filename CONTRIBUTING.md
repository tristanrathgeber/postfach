# Mitmachen

Postfach ist ein Hobby-Projekt. Fehlerberichte, kleine Fixes und gut begründete
Wünsche sind willkommen — bei größeren Umbauten bitte vorher ein Issue aufmachen,
damit wir nicht aneinander vorbei arbeiten.

Sicherheitslücken **nicht** als Issue melden → siehe [SECURITY.md](SECURITY.md).

## Beide Repos nebeneinander klonen (der nicht offensichtliche Teil)

Das Backend nutzt `email-agent` als **Path-Dependency** (`../../email-agent` in
`backend/pyproject.toml`). Ohne das Schwester-Repo scheitert schon `uv sync`.
Beide Repos müssen also als Geschwister-Verzeichnisse liegen:

```bash
git clone https://github.com/tristanrathgeber/email-agent
git clone https://github.com/tristanrathgeber/postfach
cd postfach
```

Sonst gebraucht: macOS, [uv](https://docs.astral.sh/uv/), Node.js ≥ 20.
(Die CI macht genau dasselbe — sie checkt `email-agent` als Nachbar aus, siehe
`.github/workflows/ci.yml`.)

## Tests

```bash
cd backend && uv run pytest     # IMAP/SMTP/LLM sind gemockt, kein echtes Konto nötig
cd frontend && npm test         # Vitest; npm run lint prüft mit oxlint
```

**Tests müssen grün sein** — die CI läuft Backend- und Frontend-Tests bei jedem
Push und PR. Und: im Projekt wird **TDD** gemacht. Erst der Test, der die Lücke
zeigt, dann der Code. Das ist kein Formalismus, sondern der Grund, warum die
Sicherheits-Invarianten (KI sendet/löscht nie, Passwörter nie im Log) über elf
Feature-Batches gehalten haben — `backend/tests/test_safety.py` und
`test_appreife.py` sind genau dafür da. Wer diese Zusagen anfasst, ändert bitte
den Test bewusst mit und schreibt ins PR, warum.

## Änderungen ausprobieren — ohne eigene Zugangsdaten

Der Demo-Modus füllt die App mit Beispielmails, ohne irgendein Konto oder den
Schlüsselbund anzufassen:

```bash
cd backend && uv sync && cd ../frontend && npm install && npm run build && cd ..
POSTFACH_DEMO=1 uv run --project backend postfach   # → http://127.0.0.1:8722
```

Fürs Frontend-Entwickeln mit Hot Reload: `cd frontend && npm run dev` (Vite,
proxyt auf 8722) — das Backend parallel wie oben starten.

## Sprache

**Deutsch** — für UI-Texte, Code-Kommentare und Commit-Messages. Die App, das
Handbuch und die Nutzer sind deutsch; englische UI-Strings fallen sofort auf.
Ausnahme: das README ist absichtlich englisch (Schaufenster nach außen).
Bezeichner im Code (Funktions-/Variablennamen) bleiben englisch, wie im
Bestand üblich.

Kommentare erklären bitte **warum**, nicht was — Beispiele dafür stehen überall
im Bestand, etwa in `backend/src/postfach/paths.py` oder `sanitize.py`.

## Pull Requests

- Kleine, thematisch geschlossene Commits.
- Was du geändert hast und warum — kurz, aber nachvollziehbar.
- Wenn du ein Verhalten änderst, das im Handbuch (`docs/HANDBUCH.md`) steht:
  Handbuch mit anpassen.
- Die API ist als Vertrag festgeschrieben (`docs/api-contract.md`) — Brüche dort
  bitte im PR benennen.
