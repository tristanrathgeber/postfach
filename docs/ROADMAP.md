# Postfach — Fahrplan (Stand 2026-07-21)

Quelle: Wettbewerbs-Recherche (Superhuman, Notion Mail †, Apple/Gmail/Outlook,
Thunderbird/Mimestream/Spark/HEY/Proton, Shortwave/Fyxer/Gemini/Copilot,
Nutzerbeschwerden) + interne Lücken-Inventur. Reihenfolge = Bearbeitungsreihenfolge.
Große Features als eigener Batch, Kleinigkeiten gebündelt, Design ganz am Ende.

Leitplanken (gelten für jeden Batch):
- Sicherheits-Invarianten unantastbar: KI sendet/verschiebt/löscht nie; endgültiges Löschen gibt es nicht.
- KI: nur auf Abruf oder vorberechnet, immer abschaltbar, nie Latenz auf Kernaktionen, nie Auto-Summaries.
- Fehler nie still (Verbindungsstatus sichtbar); keine Feature-Entfernung ohne Ersatz; TDD.

## Batch 1 — Schreiben komplett (Table Stakes I) ✅ 2026-07-21
- [x] **Weiterleiten** (mit Anhängen, korrektem Quoting, „Fwd:"-Regel)
- [x] **BCC** im Composer (Bcc-Header bleibt in der Sent-Kopie, SMTP entfernt ihn beim Versand)
- [x] **Signaturen** pro Konto (Editor in der App, automatische Anfügung mit „-- “-Trenner)
- [x] **Entwürfe speichern** (automatisch lokal, Wiederöffnen/Löschen; IMAP-Entwürfe-Ordner
  bewusst verschoben — IMAP kann Drafts nicht updaten, Altversionen-Löschen kollidiert mit
  unserer Nie-Löschen-Garantie, siehe Spec 2026-07-21)
- [x] **Anhänge senden** (Dateiauswahl + Drag & Drop, 25-MB-Limit client- und serverseitig)
- [x] **Kontakte-Autocomplete** (lokal aus bisherigen Mails aufgebaut, Ranking nach Häufigkeit×Aktualität)
- [x] **Snippets** (Textbausteine mit {vorname}/{datum}, per ;kürzel+Tab und ⌘K)

## Batch 2 — Empfangen & Ordnung (Table Stakes II) ✅ 2026-07-21
- [x] **macOS-Benachrichtigungen** (osascript, argv-sicher; UID-Wasserstand gegen Doppel-Meldungen; pro Konto schaltbar)
- [x] **Spam-Markierung** (`!` bzw. Reader-Button; SPECIAL-USE \Junk → Namenssuche inkl. GMX „Spamverdacht"; „Kein Spam" zurück in die Inbox)
- [x] **Mehrfachauswahl & Bulk-Triage** (`x`/Shift-Klick/Auswahlkreis, Aktionsleiste; EIN IMAP-Request pro Konto via /api/batch-action)
- [x] **Klassifikation korrigierbar** (Kategorie-Badge im Reader ist ein Menü; Nutzer-Korrektur schlägt die KI dauerhaft — auch gegen laufende Klassifikations-Läufe)
- [x] **Verbindungsstatus sichtbar** (Punkt + „getrennt seit HH:MM" in der Sidebar, SSE-Status-Events, /api/status)
- [x] **Sortier-Automatik scharf** (launchd alle 30 Min, --no-drafts; Log unter ~/Library/Logs/postfach-email-agent.log)

## Batch 3 — Lokale Volltextsuche (Leuchtturm, groß) ✅ 2026-07-21
- [x] SQLite-FTS5-Index über den kompletten Bestand — real gemessen: **3–13 ms über 6,4k Mails** (End-to-End inkl. HTTP)
- [x] Exakte Phrasen, Umlaute korrekt (remove_diacritics: „muller" findet „Müller"), Operatoren von:/an:/betreff:/vor:/nach:/hat:anhang; Nutzertext ist nie FTS-Syntax
- [x] Suche über ALLE Ordner des Kontos (Treffer zeigen ihren Ordner); live über den Push-Hook, Move-Aktionen räumen Einträge, Voll-Lauf prunt; IMAP-SEARCH nur noch Fallback vor dem ersten Index
- [ ] Begründung: Suche ist laut Recherche der #1-Wechselgrund; local-first kann hier strukturell gewinnen

## Batch 4 — Konversations-Threads (groß) ✅ 2026-07-21
- [x] Threading über References/In-Reply-To + konservativer Betreff-Fallback (nur eindeutiger Kandidat mit passender Gegenseite); leere Message-IDs und kaputte Ketten zerfallen sauber statt falsch zu verkleben
- [x] Konversationsleiste im Reader: chronologisch über ALLE Ordner inkl. Gesendet, klickbare Zeilen mit Ordner-Label, aktuelle hervorgehoben
- [x] Faden-Triage (Archiv/Papierkorb — Gesendet-Kopien bleiben verschont) + (n)-Zähler in der Liste

## Batch 5 — Zeit-Features (groß): Undo, Später, Snooze, Follow-up ✅ 2026-07-21
- [x] **Undo-Send** (konfigurierbar 0–30 s, Default 15; Storno stellt den Entwurf garantiert wieder her)
- [x] **Später senden** (lokale Warteschlange, neustartfest; Ansicht „Ausgang" mit Stornieren; 3×-Fehler-Deckel + Meldung)
- [x] **Snooze auf Plain-IMAP** (Taste z / Reader-Menü; Ordner „Später", Rückkehr per Message-ID ungelesen in die Inbox — die Marktlücke ist zu)
- [x] **Follow-up-Reminder** (beim Senden 3/7 Tage; löst sich still bei fremder Antwort im Faden, sonst Ansicht „Wiedervorlage" + Meldung)

## Batch 6 — Posteingangs-Hygiene: Abo-Manager + Screener ✅ (2026-07-21)
- [x] **Abo-Manager**: alle Newsletter als Liste (Absender, Frequenz) + **1-Klick-Abmelden** via List-Unsubscribe (parsen wir bereits!)
  - Index-Spalten `list_unsubscribe`/`list_unsubscribe_post`/`is_sent` + Migration mit is_sent-Backfill; Header-Paar konsistent aus der neuesten Mail (ROW_NUMBER)
  - Strategie: RFC-8058-One-Click-POST (nur https, SSRF-Guard: keine privaten Ziele, keine Redirects) → mailto über den SMTP-Pfad → Link im Browser
  - Zweitklick-Bestätigung mit Doppelklick-Karenz; Abmeldungen in `data/subscriptions.json` (409 bei Doppelung); real: 112 Abos erkannt
- [x] **Screener** (HEY-Learning): Erstkontakt-Absender landen in einer Prüfliste — zulassen/ablehnen, KI schlägt lokal vor, Entscheidung merkt sich die App
  - Erstkontakt = erste Mail < 30 Tage + nie Gesendet-Empfänger (Token-Match) + keine Entscheidung; Spam/Papierkorb zählen nicht
  - Vorschlag ehrlich regelbasiert (Abmelde-Header / geteilter NOREPLY_RE) — kein LLM-Call; „Ablehnen" = Nutzer-Regel: Watcher verschiebt künftige Mails nach „Aussortiert" (nie Papierkorb), ohne Notification
  - Entscheidungen in `data/screener.json`; real: 30 Kandidaten in 30 Tagen

## Batch 7 — Emilia II (KI-Ausbau) ✅ (2026-07-21, Embedding-Modell wartet auf Freigabe)
- [x] **Streaming-Antworten** (Text erscheint beim Generieren)
  - NDJSON über POST /emilia/chat/stream ({"sources"} → {"delta"}× → {"done"}/{"error"}); OllamaBackend.stream() im email-agent (error-Zeilen mit HTTP 200 → LLMError!); Client-Disconnect kappt den Ollama-Stream via BackgroundTask(generator.close); UI: fetch + ReadableStream, AbortController beim Schließen
- [x] **Natürlichsprachige Suche** als Suchmodus (Shortwave-Learning: das meistbehaltene KI-Feature)
  - ?-Präfix im Suchfeld → GET /search/nl: Emilia übersetzt in Operatoren (Prompt mit Datum + Few-Shots, Fence-/Plauder-tolerant), Ausführung über den normalen FTS-Pfad (parse_query quotet — injektionsfest); Chip „Emilia sucht: …" mit Klick-Übernahme; nur bei ready-Index (409)
- [x] **Sie/Du- & Ton-Umschalter** beim Verbessern (deutschlandspezifisch, kein US-Client kann das)
  - improve-Modi sie/du/kuerzer; Composer-Menü „Ton ändern …"
- [x] **Langthread-Zusammenfassung auf Abruf** (niemals automatisch — Gemini-Backlash)
  - POST /emilia/thread_summary; Bodies aus dem Such-Index (thread_texts, neueste 30, chronologisch); UI-Knopf in der ThreadRail ab 3 Mails
- [ ] Besseres deutsches Embedding-Modell (nach Download-Freigabe) — Empfehlung: `jina/jina-embeddings-v2-base-de` (~160 MB); Umstieg = ollama pull + config `embed_model` + Voll-Index
- [x] Globaler, sichtbarer KI-Aus-Schalter (Anti-Superhuman: alles abschaltbar)
  - settings.ai_enabled: 403 auf classify/draft/emilia/*/search/nl (außer index/status — FTS + Kontakte sind keine KI); UI blendet alles KI-hafte aus; Kategorie-Cache bleibt lesbar

## Batch 8 — Kalender-Minimum & Export ✅ (2026-07-21)
- [x] **ICS-Einladungen inline** mit Zusagen/Ablehnen (sendet echte Antwort) — deckt ~80 % des Kalenderbedarfs ohne Kalender-App-Falle
  - invites.py (icalendar): parse_invite (untrusted → None, all-day/TZID), build_invite_reply_ics (RFC-5546 REPLY, PARTSTAT); ParsedMail.calendar_raw; Einladungskarte im Reader (Zusagen/Vielleicht/Absagen); POST /invite/respond → RSVP an Organisator über Versandpfad (Sent-Ablage); organizer_email auf genau eine Adresse geprüft (kein Auffächern)
- [x] **Mail → Task/Markdown/Obsidian-Export** (die Integration, die Notion Mail nie geliefert hat)
  - mdexport.py: YAML-Frontmatter (Backslash-sicher) + Klartext-Body; GET .../export → {filename, markdown}; UI „Als Markdown" (Blob-Download + Clipboard)
- [x] Struktur-Extraktion lokal: Termine, Beträge, Tracking-Nummern als klickbare Chips
  - extract.py: regelbasiert (kein LLM), possessive Regex + 10k-Cap gegen ReDoS; Sendungsnummern UPS/DHL/Hermes/DPD → Anbieter-Tracking (Host-Allowlist); Chips im Reader (Kopieren / Tracking-Link). Real: „11,88 €" auf Hetzner-Rechnung erkannt

## Batch 9 — Onboarding & deutsche Provider ✅ (2026-07-21)
- [x] **Konto-Einrichtung per UI** (Formular statt YAML), Passwörter in den macOS-Schlüsselbund
  - credentials.py: resolve_password (Env→Schlüsselbund, kein Fallback bei deklariertem password_env); accounts_store.py (data/accounts.json, nie ein Passwortfeld); config.yaml unberührt; AddAccountDialog (testen→speichern), config_account_names schützt config-Konten vor Löschung; Demo fasst den echten Schlüsselbund nie an; 422-Handler redigiert Passwörter
- [x] **Provider-Presets**: GMX, web.de, T-Online, Posteo, mailbox.org, Freenet, Gmail, iCloud, manuell (SMTP-Host ≠ IMAP-Host bei GMX/web.de!)
- [x] Ordner-Mapping-Assistent (bestehende Ordner ↔ Kategorien)
  - folder_map.py-Overlay über agent_config.folder_for; Einstellungen-Sektion je Kategorie ein Ziel-Ordner (real: 12 Kategorien × 18 GMX-Ordner)
- [x] Progressives Shortcut-Teaching (Superhuman-Learning: Aktivierung entscheidet)
  - lib/shortcutTeach.ts: 3× Maus-Wiederholung → EIN Tastatur-Tipp, danach nie wieder (localStorage); nur an Maus-Klicks, nicht an Tastatur-Handlern

## Batch 10 — App-Reife & Vertrieb ✅ (2026-07-21)
- [x] **Echtes Binary** (PyInstaller): korrektes Dock-Icon, keine uv/Node-Voraussetzung
  - postfach.spec (bündelt postfach+email_agent+Frontend-dist+pyobjc); paths.py trennt resource_dir() (gebündelt) und user_data_root() (~/Library/Application Support/Postfach); Null-Konten-Start (Onboarding-UI übernimmt). Real: startet mit LEERER PATH, 0,51 s Kaltstart, 144 MB, 45 MB Bundle
- [x] **CI + Releases**: GitHub Actions (Tests, Build), fertige .app als Release-Download
  - ci.yml (Backend+Frontend, email-agent als Nachbar-Checkout), release.yml (Tag v* → .app bauen/zippen/Release)
- [x] Update-Hinweis in der App; Startzeit/Speicher messen und publizieren
  - /api/version (Update-Check NUR auf Klick, checked-Flag); Über-Dialog (⌘K); Messwerte im README/Report
- [x] Verifizierbare Privatheit: offener Netzwerk-Log, Null-Telemetrie-Statement, englisches README
  - /api/network-info listet ALLE ausgehenden Ziele (inkl. Cloud-LLM-Host, sobald sort_local/draft_local=false — kann nie lügen); Defaults jetzt lokal (kein Cloud-Call out-of-the-box); englisches README mit Zero-Telemetrie + Transparenz-Tabelle; test_no_telemetry_packages_imported

## Batch 11 — Design (bewusst zum Schluss)
- [ ] **Dark Mode richtig**: Original-Mail im hellen Papier-Container, Smart-Darkening als Opt-in pro Mail/Absender, Bilder nie invertieren
- [ ] **Reader-View** (eine Taste: Klartext/vereinfacht)
- [ ] Per-Konto-Farbcodierung in Liste & Unified Inbox
- [ ] Dichte-Umschalter (kompakt/komfortabel), Leerzustände, Toast-/Motion-Feinschliff
- [ ] Icon-Verfeinerung + durchgängiger Polish-Pass mit Design-Review

---
Erledigt bis hier: Multi-Account-IMAP · AI-Views · sicheres HTML + Tracker-Blocking ·
Emilia (RAG-Gedächtnis, Korrigieren/Verbessern, lokal via qwen3) · Live-Push (IDLE+SSE) ·
Mac-App · Demo-Modus · öffentliche Repos (MIT).
