# Postfach — Fahrplan (Stand 2026-07-21)

Quelle: Wettbewerbs-Recherche (Superhuman, Notion Mail †, Apple/Gmail/Outlook,
Thunderbird/Mimestream/Spark/HEY/Proton, Shortwave/Fyxer/Gemini/Copilot,
Nutzerbeschwerden) + interne Lücken-Inventur. Reihenfolge = Bearbeitungsreihenfolge.
Große Features als eigener Batch, Kleinigkeiten gebündelt, Design ganz am Ende.

Leitplanken (gelten für jeden Batch):
- Sicherheits-Invarianten unantastbar: KI sendet/verschiebt/löscht nie; endgültiges Löschen gibt es nicht.
- KI: nur auf Abruf oder vorberechnet, immer abschaltbar, nie Latenz auf Kernaktionen, nie Auto-Summaries.
- Fehler nie still (Verbindungsstatus sichtbar); keine Feature-Entfernung ohne Ersatz; TDD.

## Batch 1 — Schreiben komplett (Table Stakes I)
- [ ] **Weiterleiten** (mit Anhängen, korrektem Quoting, „Fwd:"-Regel)
- [ ] **BCC** im Composer
- [ ] **Signaturen** pro Konto (Editor in der App, automatische Anfügung)
- [ ] **Entwürfe speichern** (automatisch lokal + in den IMAP-Entwürfe-Ordner; Wiederöffnen)
- [ ] **Anhänge senden** (Dateiauswahl + Drag & Drop in den Composer)
- [ ] **Kontakte-Autocomplete** (lokal aus bisherigen Mails aufgebaut)
- [ ] **Snippets** (Textbausteine mit Variablen, per Kürzel — Superhuman-Learning)

## Batch 2 — Empfangen & Ordnung (Table Stakes II)
- [ ] **macOS-Benachrichtigungen** (nativ, aus dem vorhandenen Push-Kanal; pro Konto schaltbar)
- [ ] **Spam-Markierung** („Spam" → Spamverdacht-Ordner, „Kein Spam" zurück)
- [ ] **Mehrfachauswahl & Bulk-Triage** (Auswahl per Klick/Shift/`x`, Aktionen auf alle)
- [ ] **Klassifikation korrigierbar** (Kategorie per UI ändern → Cache-Update; „falsch einsortiert" = 1 Tastendruck zurück — Fyxer-Lektion: falsche Ablage ist der Vertrauenskiller)
- [ ] **Verbindungsstatus sichtbar** („GMX getrennt 14:32, neu verbunden" — nie still scheitern)
- [ ] **Sortier-Automatik scharf schalten** (launchd alle 30 Min für den email-agent)

## Batch 3 — Lokale Volltextsuche (Leuchtturm, groß)
- [ ] SQLite-FTS5-Index über den kompletten lokalen Bestand, Ziel **< 50 ms über 100k Mails**
- [ ] Exakte Phrasen, Umlaute/Unicode korrekt, Operatoren (von:, an:, betreff:, vor:/nach:, hat:anhang)
- [ ] Immer aktuell über den Push-Hook; IMAP-SEARCH nur noch Fallback
- [ ] Begründung: Suche ist laut Recherche der #1-Wechselgrund; local-first kann hier strukturell gewinnen

## Batch 4 — Konversations-Threads (groß)
- [ ] Threading über References/In-Reply-To (+ Betreff-Fallback), saubere Thread-Trennung
- [ ] Thread-Ansicht im Reader (chronologisch, einklappbare Einzelmails)
- [ ] Thread-Triage (Archiv/Papierkorb für ganzen Thread), Zähler in der Liste

## Batch 5 — Zeit-Features (groß): Undo, Später, Snooze, Follow-up
- [ ] **Undo-Send** (verzögertes Senden, konfigurierbar 10–30 s)
- [ ] **Später senden** (lokale Warteschlange + Scheduler)
- [ ] **Snooze auf Plain-IMAP** (lokale Wiedervorlage — laut Recherche echte Marktlücke: Gmail-Clients können es, IMAP-Clients nicht)
- [ ] **Follow-up-Reminder** („erinnere mich, wenn keine Antwort in 3 Tagen")

## Batch 6 — Posteingangs-Hygiene: Abo-Manager + Screener
- [ ] **Abo-Manager**: alle Newsletter als Liste (Absender, Frequenz) + **1-Klick-Abmelden** via List-Unsubscribe (parsen wir bereits!)
- [ ] **Screener** (HEY-Learning): Erstkontakt-Absender landen in einer Prüfliste — zulassen/ablehnen, KI schlägt lokal vor, Entscheidung merkt sich die App

## Batch 7 — Emilia II (KI-Ausbau)
- [ ] **Streaming-Antworten** (Text erscheint beim Generieren)
- [ ] **Natürlichsprachige Suche** als Suchmodus (Shortwave-Learning: das meistbehaltene KI-Feature)
- [ ] **Sie/Du- & Ton-Umschalter** beim Verbessern (deutschlandspezifisch, kein US-Client kann das)
- [ ] **Langthread-Zusammenfassung auf Abruf** (niemals automatisch — Gemini-Backlash)
- [ ] Besseres deutsches Embedding-Modell (nach Download-Freigabe)
- [ ] Globaler, sichtbarer KI-Aus-Schalter (Anti-Superhuman: alles abschaltbar)

## Batch 8 — Kalender-Minimum & Export
- [ ] **ICS-Einladungen inline** mit Zusagen/Ablehnen (sendet echte Antwort) — deckt ~80 % des Kalenderbedarfs ohne Kalender-App-Falle
- [ ] **Mail → Task/Markdown/Obsidian-Export** (die Integration, die Notion Mail nie geliefert hat)
- [ ] Struktur-Extraktion lokal: Termine, Beträge, Tracking-Nummern als klickbare Chips

## Batch 9 — Onboarding & deutsche Provider
- [ ] **Konto-Einrichtung per UI** (Formular statt YAML), Passwörter in den macOS-Schlüsselbund
- [ ] **Provider-Presets**: GMX, web.de, T-Online, Posteo, mailbox.org, Freenet („GMX ohne Werbung"-Wedge)
- [ ] Ordner-Mapping-Assistent (bestehende Ordner ↔ Kategorien)
- [ ] Progressives Shortcut-Teaching (Superhuman-Learning: Aktivierung entscheidet)

## Batch 10 — App-Reife & Vertrieb
- [ ] **Echtes Binary** (PyInstaller): korrektes Dock-Icon, keine uv/Node-Voraussetzung
- [ ] **CI + Releases**: GitHub Actions (Tests, Build), fertige .app als Release-Download
- [ ] Update-Hinweis in der App; Startzeit/Speicher messen und publizieren
- [ ] Verifizierbare Privatheit: offener Netzwerk-Log, Null-Telemetrie-Statement, englisches README

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
