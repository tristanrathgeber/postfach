# Batch 9 — Onboarding & deutsche Provider (Design)

Stand: 2026-07-21 · Contract-Addendum: v0.11 (in docs/api-contract.md)

Ziel: ein Konto einrichten, ohne `config.yaml` und `.env` von Hand zu editieren.
Passwörter landen im macOS-Schlüsselbund statt im Klartext. Dazu ein
Ordner-Mapping-Assistent und behutsames Shortcut-Teaching.

## Sicherheitsrahmen (unverhandelbar)

- Das Passwort gibt **der Nutzer** in **seiner eigenen, lokalen** App ein. Es
  wandert direkt in den **macOS-Schlüsselbund** (`keyring`, Service `postfach`,
  Username = Kontoname) — **nie** in `config.yaml`, **nie** in einen JSON-Store,
  **nie** in den Such-Index, **nie** ins Log.
- Der Test-/Speicher-Endpunkt nimmt das Passwort nur im Request-Body (127.0.0.1,
  lokal), nutzt es transient und wirft es weg, wenn nicht gespeichert wird.
- Tristans bestehende `.env`-Einrichtung bleibt: die Passwort-Auflösung ist
  **erst Env-Variable, dann Schlüsselbund** (`resolve_password(account)`), zentral
  an einer Stelle (bisher zweimal `os.environ.get`).
- **Nicht-destruktiv:** UI-Konten liegen in `data/accounts.json` (von Postfach
  verwaltet), die hand-editierte `config.yaml` wird nie überschrieben. Beim Laden
  werden config.yaml-Konten und verwaltete Konten gemischt (Namens-Eindeutigkeit
  erzwungen).

## 1. Provider-Presets + Konto-Einrichtung

**`providers.py`** — statische Preset-Tabelle (imap/smtp Host+Port, SSL-Hinweis):
GMX, web.de, T-Online, Posteo, mailbox.org, Freenet, Gmail, iCloud, „Anderer
(manuell)". `GET /api/providers` liefert sie.

**Flow (UI-Dialog „Konto hinzufügen"):** Name · E-Mail · Provider-Auswahl
(füllt Host/Port automatisch, bei „manuell" editierbar) · Passwort. Zwei Schritte:
1. **`POST /api/accounts/test`** `{provider, address, imap_host, imap_port,
   smtp_host, smtp_port, password}` → testet IMAP-Login **und** SMTP-Verbindung
   (login) ohne zu speichern; `{ok, imap, smtp, error?}`. Im Demo-Modus
   übersprungen (`{ok:true, demo:true}`).
2. **`POST /api/accounts`** (gleicher Body + `name`, `sent_folder?`) → validiert
   (Name eindeutig, Adresse @, Host bei imap), Passwort → Schlüsselbund, Konto →
   `data/accounts.json`, **live** in `app.state.accounts` (sofort les-/sendbar);
   `{ok, watcher_pending:true}` (Live-Push-Watcher erst nach Neustart — ehrlich).

**`DELETE /api/accounts/{name}`** — nur verwaltete Konten; entfernt Store-Eintrag,
Schlüsselbund-Passwort und den Live-Eintrag (config.yaml-Konten sind
schreibgeschützt → 409).

## 2. Ordner-Mapping-Assistent

Kategorie → bestehender Ordner (statt `AI/<Kategorie>`). Wichtig für GMX (Ordner-
Limit). Verwalteter Overlay `data/folder_map.json` (`{category: folder}`), im
App-State als `FolderMap`; die Archiv-Route konsultiert **erst** das Overlay,
dann `agent_config.folder_for`. `GET /api/folder-map?account=` → `{categories,
folders, mapping}`; `PUT /api/folder-map` `{mapping}`. UI: Einstellungen-Sektion
„Ordner-Zuordnung" — je Kategorie ein Dropdown der echten Ordner (oder „AI/…"-
Standard). Rein additiv, ändert nie den Klassifikator.

## 3. Progressives Shortcut-Teaching

Reines Frontend (localStorage). Führt der Nutzer eine Aktion wiederholt **per
Maus** aus (Archivieren, Antworten, Papierkorb, Ungelesen), zählt ein Hook mit;
ab der 3. Wiederholung EIN dezenter Hinweis-Toast („Tipp: Taste **e**
archiviert") — danach nie wieder für diese Aktion (gelernt/gemerkt in
localStorage). Kein Nagging, global abschaltbar über einen bestehenden Pfad:
respektiert den Reduced-Motion-/Ruhewunsch nicht nötig, aber der Hinweis
erscheint höchstens einmal pro Aktion und verschwindet nach 6 s.

## API (v0.11) — Kurzform

| Route | Zweck |
|---|---|
| `GET /api/providers` | Preset-Liste (Host/Port je Anbieter) |
| `POST /api/accounts/test` | IMAP+SMTP prüfen, nichts speichern |
| `POST /api/accounts` | Konto speichern (Passwort → Schlüsselbund) |
| `DELETE /api/accounts/{name}` | verwaltetes Konto entfernen |
| `GET /api/folder-map?account=` | `{categories, folders, mapping}` |
| `PUT /api/folder-map` | `{mapping}` speichern |

## Nicht in diesem Batch

Live-Push-Watcher für frisch hinzugefügte Konten ohne Neustart (Thread-Start-
Refactor — Konto ist sofort les-/sendbar, nur Echtzeit-Meldungen warten),
OAuth (Gmail/iCloud nutzen App-Passwörter — Hinweis in der UI), Konto-Bearbeiten
(nur Hinzufügen/Löschen), Passwort-Rotation, Import bestehender `.env`-Konten in
den Schlüsselbund.
