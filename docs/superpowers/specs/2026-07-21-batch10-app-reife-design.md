# Batch 10 — App-Reife & Vertrieb (Design)

Stand: 2026-07-21 · Contract-Addendum: v0.12 (in docs/api-contract.md)

Ziel: aus dem Repo-gebundenen `uv run`-Wrapper ein echtes, portables macOS-Binary
machen (kein uv/Node/Repo zur Laufzeit), mit CI + Release-Pipeline, verifizierbarer
Privatheit und einem englischen README. Batch 9 (Konto per UI + Schlüsselbund) macht
das erst rund: ein frisches Binary startet ohne config.yaml, der Nutzer richtet sein
Konto im Fenster ein.

## 1. Portable App-Grundlage (`paths.py`)

Das Binary hat kein Repo. Zwei getrennte Wurzeln:
- **`resource_dir()`** — mitgebündelte, NUR-lesbare Ressourcen (Frontend-`dist`,
  Stilprofil-Default). Frozen: `sys._MEIPASS`; sonst Repo.
- **`user_data_root()`** — SCHREIBBARE config/data. Frozen:
  `~/Library/Application Support/Postfach` (bei Bedarf angelegt); sonst Repo (mit
  `POSTFACH_ROOT`-Override wie bisher).

`create_app` bezieht config/data aus `user_data_root()`, das Frontend aus
`resource_dir()`. **Null-Konten-Start muss sauber laufen** (frisches Binary: keine
config.yaml, keine .env) — die Onboarding-UI (Batch 9) übernimmt. `.env` wird aus
`user_data_root()` geladen (optional).

## 2. Echtes Binary (PyInstaller)

`postfach.spec`: bündelt das `postfach`- und `email_agent`-Paket, alle Abhängigkeiten
(uvicorn/fastapi/pywebview+pyobjc/imapclient/keyring/icalendar/nh3), das gebaute
Frontend-`dist` als Daten, das `.icns`-Icon. Ergebnis: `dist/Postfach.app` mit
eingebettetem Python — startbar per Doppelklick, ohne uv/Node.

`scripts/build_app.sh` neu: Frontend bauen → Icon → `pyinstaller postfach.spec` →
`.app` mit korrektem Info.plist (Dock-Icon, LSUIElement=false, Version aus
`__version__`). Unsigniert (Rechtsklick→Öffnen dokumentiert).

Bekannte Klippen: pywebview braucht die pyobjc-Hidden-Imports (WKWebView);
`StaticFiles` findet `dist` über `resource_dir()`; das email-agent-Paket muss als
collect_all rein.

## 3. Update-Hinweis + Über-Dialog

`GET /api/version` → `{version, latest?, update_available}`. Der Server vergleicht
die eigene Version mit der neuesten GitHub-Release-Tag — **nur auf ausdrücklichen
Klick** („Nach Updates suchen" im Über-Dialog), nie automatisch beim Start (Privatheit:
kein stiller Netz-Call). Über-Dialog (⌘, oder Menü) zeigt Version, Lizenz, den
Privatheits-Kurztext und den manuellen Update-Check.

## 4. Verifizierbare Privatheit

- **Englisches README** (`README.md`): was Postfach ist, Zero-Telemetrie-Statement,
  Netzwerk-Transparenz-Tabelle (IMAP/SMTP → dein Anbieter; Ollama → localhost;
  Update-Check → nur auf Klick, GitHub; sonst NICHTS), Bau-/Installations-Anleitung.
- **Netzwerk-Transparenz im Code belegbar:** `GET /api/network-info` listet die
  ausgehenden Ziele (Konten-Hosts, Ollama-URL) — die UI zeigt sie im Über-Dialog,
  „Postfach spricht nur mit diesen Servern". Kein Analytics-Endpunkt existiert
  (per Test: kein Modul importiert ein Telemetrie-/Analytics-Paket, keine unerwarteten
  Hosts).

## 5. Startzeit & Speicher

Lokal gemessen (Kaltstart bis Fenster, RSS im Leerlauf), im Batch-Report + README
dokumentiert. Kein Code, nur Messung.

## API (v0.12) — Kurzform

| Route | Zweck |
|---|---|
| `GET /api/version` | `{version, latest?, update_available}` — latest nur bei `?check=1` |
| `GET /api/network-info` | `{accounts:[{host,port}], ollama, note}` — ausgehende Ziele |

## Tests

- `paths.py`: frozen-Simulation (monkeypatch `sys.frozen`/`_MEIPASS`) → resource_dir/
  user_data_root korrekt; Verzeichnis-Anlage.
- `create_app` mit leerem root (keine config/data) → startet, 0 Konten, /accounts=[].
- `/api/version` (ohne Netz: update_available=false, latest weggelassen).
- `/api/network-info` (Demo: leere/Demo-Hosts).
- Safety: kein Telemetrie-Paket importiert; `/api/version`-Check nur bei explizitem Flag.
- Build wird lokal verifiziert (`.app` startet ohne uv/Node) — nicht als Unit-Test.

## Nicht in diesem Batch

Code-Signing/Notarisierung (unsigniert bleibt, dokumentiert), Auto-Update-Installer
(nur Hinweis), Windows/Linux-Binaries (macOS zuerst), automatischer Update-Check beim
Start (bewusst nur manuell — Privatheit).
