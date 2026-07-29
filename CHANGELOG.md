# Changelog

Alle nennenswerten Änderungen an Postfach. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
[Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

—

## [0.10.0] — erste öffentliche Beta

Erste Version, die als Mac-App verteilt wird. Aus elf Feature-Batches (siehe
`docs/ROADMAP.md`) entstanden; alles läuft lokal auf `127.0.0.1:8722`.

### Added

- **Mail-Grundgerüst**: Multi-Account-IMAP mit Unified Inbox, Live-Push über
  IMAP IDLE + SSE, KI-Ansichten je Kategorie, sicheres HTML mit Tracker-Blocking.
- **Schreiben**: Antworten/Weiterleiten mit Anhängen, BCC, Signaturen pro Konto,
  lokale Entwürfe mit Autosave, Anhänge bis 25 MB, Kontakte-Autocomplete,
  Textbausteine.
- **Empfangen & Ordnung**: Mehrfachauswahl und Bulk-Triage (ein IMAP-Request pro
  Konto), Spam-Markierung, korrigierbare Klassifikation (Nutzerkorrektur schlägt
  die KI dauerhaft), sichtbarer Verbindungsstatus, macOS-Benachrichtigungen,
  Sortier-Automatik per launchd.
- **Lokale Volltextsuche**: SQLite-FTS5 über alle Ordner eines Kontos, mit
  Operatoren (`von:` `an:` `betreff:` `vor:` `nach:` `hat:anhang`), korrekten
  Umlauten und 3–13 ms über 6,4k Mails.
- **Konversations-Threads**: Threading über References/In-Reply-To mit
  konservativem Betreff-Fallback, Faden-Ansicht über alle Ordner inkl. Gesendet,
  Faden-Triage.
- **Zeit-Features**: Rückgängig-Senden (0–30 s), Später senden über eine
  neustartfeste lokale Warteschlange, Snooze auf reinem IMAP, Follow-up-Reminder.
- **Posteingangs-Hygiene**: Abo-Manager mit 1-Klick-Abmelden (RFC-8058
  One-Click-POST mit SSRF-Guard, sonst mailto oder Link) und Erstkontakt-Screener
  mit „Aussortiert"-Regel.
- **Emilia (lokaler KI-Copilot über Ollama)**: RAG-Gedächtnis über die eigenen
  Mails mit Quellen-Chips, Streaming-Antworten, natürlichsprachige Suche
  (`?`-Präfix), Sie/Du- und Ton-Umschalter, Thread-Zusammenfassung auf Abruf,
  globaler KI-Aus-Schalter.
- **Kalender & Export**: ICS-Einladungen inline beantworten (echtes RFC-5546
  RSVP), Export einer Mail als Obsidian-taugliches Markdown, lokale
  Struktur-Chips für Beträge, Termine und Sendungsnummern (regelbasiert, kein
  LLM).
- **Onboarding**: Konto-Einrichtung per Formular mit Passwort direkt in den
  macOS-Schlüsselbund, Provider-Presets (GMX, web.de, T-Online, Posteo,
  mailbox.org, Freenet, Gmail, iCloud, manuell), Ordner-Mapping-Assistent,
  progressives Shortcut-Teaching.
- **Mac-App**: echtes PyInstaller-Binary ohne uv/Node zur Laufzeit (~0,5 s
  Kaltstart, ~145 MB im Betrieb), Update-Hinweis nur auf Klick, CI + automatische
  Releases.
- **Nachprüfbare Privatheit**: `/api/network-info` und der Dialog *Über Postfach*
  listen jedes ausgehende Ziel — inklusive Cloud-KI-Host, sobald man sie
  einschaltet; ein Test verbietet Telemetrie-/Analytics-Pakete im Import-Baum.
- **Design**: Dark Mode, in dem Original-Mails auf hellem Papier bleiben,
  Reader-View (Taste `v`), sechs Farbthemen mit eigenem Akzent,
  Per-Konto-Farbcodierung, Dichte-Umschalter.
- **Modell-Assistent**: findet das lokale KI-Modell, das zum Mac passt, lädt es
  und aktiviert es in einem Klick.
- **Anhang-Vorschau** mit zuverlässigem Download.
- **Handbuch**: `docs/HANDBUCH.md` erklärt jede Funktion und jedes Kürzel.

### Fixed

- Nutzerdaten liegen strikt außerhalb des Repos (`~/Library/Application
  Support/Postfach` statt Repo-Wurzel) — ein verrutschtes `.gitignore` kann keine
  Mailbox mehr veröffentlichen.
- Vier Beta-Blocker: DNS-Rebinding-Schutz, Live-Push auch für Konten aus der UI,
  Null-Vektoren im Gedächtnis, tote Links in Mails.
- Gedächtnis-Suche übersteht einen Wechsel des Embedding-Modells.
- Ehrlichere Ordner-Zuordnung und robustere Übersetzung der KI-Suche.
- App-Icon und Favicon (Kuvert-Mark statt „P").
- Follow-up-Test läuft zeitzonenunabhängig; CI auf Node 22.
