# Changelog

Alle nennenswerten Änderungen an Postfach. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
[Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

—

## [0.11.0] — erste öffentliche Beta

Die Version, die als Installer veröffentlicht wird. Schwerpunkt: Einrichtung
ohne Handarbeit, verlässlicher Versand und nachvollziehbare Fehler.

### Added

- **Installation per DMG**: „Postfach" auf „Programme" ziehen — kein Entpacken,
  kein Terminal. Beim ersten Start öffnet sich der Konto-Dialog von selbst.
- **Ollama richtet sich selbst ein**: Knopf im Modell-Assistenten lädt die
  offizielle Ausgabe (~145 MB), prüft die SHA-256-Summe von GitHub und legt sie
  in Postfachs eigenen Ordner — ohne Administrator, ohne manuellen Download.
  Läuft bereits ein Ollama-Server, wird der benutzt.
- **Anhang-Vorschau**: Klick auf einen Anhang öffnet Bilder, PDFs und Text
  direkt in der App; ‹ › blättert, Esc/✕ schließt. „Herunterladen" legt
  zuverlässig in `~/Downloads` ab (der alte Download-Link funktionierte im
  App-Fenster nicht).
- **Sechs Farbthemen** (Schreibtisch, Nord, Sepia, Wald, Rosé, Graphit) je in
  hell und dunkel, dazu ein frei wählbarer Akzent.
- **Modell-Assistent**: scannt den Mac und empfiehlt das Modell, das am besten
  zu Postfach passt *und* auf dem vorhandenen Arbeitsspeicher läuft.
- **Protokoll & Diagnose**: rotierende Logdatei unter
  `~/Library/Application Support/Postfach/logs/`, „Für Fehlerberichte" mit
  Kopier-Knopf im Über-Dialog, sichtbares Fenster bei Startfehlern.
- **Gescheiterte Sends wiederholen** statt nur verwerfen.

### Fixed

- **Sicherheit**: Die lokale API prüfte weder `Host`- noch `Origin`-Header. Eine
  bösartige Webseite hätte per DNS-Rebinding das Postfach lesen und in deinem
  Namen senden können. Jetzt nur noch localhost, fremde Herkunft wird abgelehnt.
- **Kein Doppelversand mehr**: Schlug ein Schritt *nach* erfolgreichem SMTP fehl
  (z. B. Verbindungsabbruch), reihte der Scheduler den Job erneut ein — der
  Empfänger bekam die Mail bis zu dreimal.
- **Per UI angelegte Konten** bekamen nie Live-Push, Benachrichtigungen oder
  Auto-Indexierung — also genau die Konten, die das Onboarding anlegt.
- **Tote Links in HTML-Mails**: `target="_blank"` konnte in der Sandbox nichts
  öffnen; ein Klick tat kommentarlos nichts.
- **Emilias Gedächtnis** schrieb bei fehlendem Embedding-Modell dauerhaft
  Null-Vektoren, meldete aber Erfolg. Jetzt klarer Fehler samt Befehl.
- **Nutzerdaten liegen nie mehr im Repo-Verzeichnis** (immer Application
  Support) — vorher lagen Mail-Index, Konfiguration und `.env` im
  Arbeitsverzeichnis eines öffentlichen Repos.
- Versionsnummern kommen jetzt aus einer einzigen Quelle; das Bundle meldete
  dem Update-Check sonst eine falsche Version.
- Gatekeeper-Anleitung korrigiert: „Rechtsklick → Öffnen" wirkt seit macOS 15
  nicht mehr.

## [0.10.0] — interne Vorstufe

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
