# Postfach

Eigene, lokale Mail-Anwendung im Stil von Notion Mail — für beliebige IMAP-Konten
(selbst gehostet, GMX, Gmail, …). Läuft komplett auf deinem Rechner (`127.0.0.1:8722`).

- **AI-Views:** Mails werden per LLM kategorisiert (email-agent-Taxonomie) und als
  Split-Inbox-Views angezeigt; Klassifikation wird gecacht.
- **Sicher lesen:** HTML serverseitig sanitisiert (nh3) + sandboxed iframe; externe
  Bilder standardmäßig blockiert („Bilder laden" auf Klick).
- **Schreiben:** Antworten/Verfassen mit „AI-Entwurf" in deinem Schreibstil;
  **gesendet wird ausschließlich, wenn du klickst** (SMTP + Ablage in Gesendet).
- **Triage:** Archiv (in `AI/<Kategorie>`-Ordner), Papierkorb, gelesen/ungelesen —
  per Hover, Tastatur (j/k/e/#/u/r/c) oder ⌘K-Palette. Endgültiges Löschen gibt es nicht.
- **AI-Grenzen:** Die AI kann klassifizieren und formulieren — niemals senden,
  verschieben oder löschen (per Test erzwungen, `backend/tests/test_safety.py`).

**Emilia** ist der eingebaute lokale KI-Copilot (Ollama): beantwortet Fragen zu deinem
Mail-Bestand (mit Quellen-Chips), korrigiert/verbessert deine Entwürfe und sortiert auf
Wunsch komplett lokal. ⌘J öffnet sie.

## Installation (öffentliches Repo)

Voraussetzungen: macOS, [uv](https://docs.astral.sh/uv/), Node.js ≥ 20.
Optional: [Ollama](https://ollama.com) (`ollama pull llama3.2 && ollama pull all-minilm:l6-v2`)
für Emilia, [Claude Code CLI](https://claude.com/claude-code) für Cloud-Entwürfe.

```bash
# Beide Repos NEBENEINANDER klonen (postfach nutzt email-agent als Path-Dependency):
git clone https://github.com/tristanrathgeber/email-agent
git clone https://github.com/tristanrathgeber/postfach
cd postfach
```

## Als Mac-App (natives Fenster statt Browser)

```bash
./scripts/build_app.sh          # baut dist/Postfach.app
cp -r dist/Postfach.app /Applications/
```

Unsigniert: beim ersten Start Rechtsklick → „Öffnen". Die App startet den lokalen
Server selbst und nutzt einen bereits laufenden mit.

## Sofort ausprobieren (Demo-Modus, keine Credentials nötig)

```bash
cd backend && uv sync && cd ../frontend && npm install && npm run build && cd ..
POSTFACH_DEMO=1 uv run --project backend postfach
# → http://127.0.0.1:8722
```

## Mit echten Konten

1. `config/config.yaml` anlegen (Format wie email-agent, plus SMTP):
   ```yaml
   accounts:
     - name: privat
       address: tristan@meinedomain.de
       imap_host: mail.meinedomain.de
       # smtp_host: mail.meinedomain.de   # Default = imap_host
       # smtp_port: 587                   # 587 STARTTLS (Default) | 465 SSL
   ```
2. Passwörter in `.env`: `MAIL_PRIVAT_PASSWORD=…`
3. Optional `config/style_profile.md` vom email-agent kopieren (AI-Entwürfe in deinem Stil).
4. Starten: `uv run --project backend postfach`

## Entwicklung

- Backend-Tests: `cd backend && uv run pytest` (46 Tests; IMAP/SMTP/LLM gemockt)
- Frontend-Dev: `cd frontend && npm run dev` (Vite, Proxy auf 8722)
- Architektur & API: `docs/superpowers/specs/…`, `docs/api-contract.md` (eingefroren)

## Bekannte Grenzen v0.1 (Roadmap: Spec)

Kein Threading, kein Snooze/Später-senden, keine Anhänge beim Verfassen, kein
Offline-Cache. Ordner-Anlage nutzt `/`-Hierarchie (Dovecot-Standard); für
Courier-Server (`INBOX.`-Präfix) kommt das Namespace-Mapping in v0.2.
