# Batch 2 — Empfangen & Ordnung (Design)

Stand: 2026-07-21 · Contract-Addendum: v0.4 (in docs/api-contract.md)

Sechs Punkte aus docs/ROADMAP.md, alle empfangsseitig. Leitplanken unverändert:
KI sendet/verschiebt/löscht nie selbst; kein endgültiges Löschen; Fehler nie still.

## 1. macOS-Benachrichtigungen

**Was:** Bei neuer Mail (vorhandener IMAP-IDLE-Push-Kanal) eine native
macOS-Benachrichtigung: Titel = Absender, Text = Betreff. Pro Konto schaltbar,
Standard: an. Nur im echten Betrieb (nie Demo, nie Tests).

**Wie (Entscheidung):** `osascript -e 'display notification …'` aus dem
Watcher-Callback. Begründung: funktioniert ohne Code-Signing (UNUserNotification-
Center verweigert unsignierten Apps den Dienst), null neue Abhängigkeiten.
Klick-Aktionen gibt es damit nicht — akzeptiert, v1-Umfang. Absender/Betreff
werden für AppleScript escaped (Injection: Mail-Inhalte sind untrusted!) und
via argv übergeben, nie in den Skript-String interpoliert.

**Schalter:** `settings.json` → `"notifications": {"<konto>": true|false}`;
Settings-Modal bekommt pro Konto einen Toggle. Fehlt der Eintrag → an.

## 2. Spam-Markierung

**Was:** Aktion „spam" verschiebt in den Spam-Ordner des Kontos (SPECIAL-USE
`\Junk`, sonst Namenssuche: spam/junk/spamverdacht/werbung, sonst anlegen
„Spam"). Aktion „unspam" verschiebt zurück in die INBOX. Kein endgültiges
Löschen, keine Automatik — nur explizite UI-Aktion.

**UI:** Reader-Button „Spam" (im Spam-Ordner: „Kein Spam"), Taste `!`.
In der Liste wirkt `!` auf die Auswahl (siehe Bulk).

## 3. Mehrfachauswahl & Bulk-Triage

**Was:** Auswahl mehrerer Mails in der Liste; Aktionen Archivieren, Papierkorb,
Gelesen/Ungelesen, Spam auf alle. Auswahl per Taste `x` (Zeile togglen),
Shift-Klick (Bereich), Klick auf den Auswahlpunkt der Zeile. Aktionsleiste
erscheint über der Liste („3 ausgewählt · Archivieren · Papierkorb · …").
Esc leert die Auswahl.

**Backend (Entscheidung):** Neuer Endpunkt `POST /api/batch-action`
`{account, folder, uids[], action}` — EINE IMAP-Verbindung, EIN move/flag-Aufruf
mit UID-Liste (IMAPClient kann Listen nativ; 50 Einzel-Requests wären 50 Connects).
Antwort: `{ok, done: n}`; Teilfehler → 502 mit Klartext, nichts still.
Erlaubte Aktionen: read/unread/archive/trash/spam/unspam — bewusst KEIN send.
Bei „archive" gilt das Kategorie-Mapping pro Mail (wie Einzel-Archiv).

## 4. Klassifikation korrigierbar

**Was:** Die Kategorie einer Mail lässt sich per UI ändern; der Klassifikations-
Cache wird überschrieben (Quelle „user" schlägt „ai" und wird nie mehr von der
KI überschrieben). Fyxer-Lektion: falsche Ablage ist der Vertrauenskiller —
eine falsche Kategorie muss in einem Handgriff korrigierbar sein.

**Backend:** `POST /api/classify/override` `{account, folder, uid, category}`.
`category` muss eine der konfigurierten Kategorien sein (422 sonst).
AiService merkt Overrides im Cache mit `"source": "user"`; classify() lässt
solche Einträge unangetastet.

**UI:** Im Reader wird das Kategorie-Badge klickbar → Menü mit allen Kategorien.

## 5. Verbindungsstatus sichtbar

**Was:** „GMX getrennt 14:32, neu verbunden" — nie still scheitern. Der
IDLE-Watcher meldet Zustandswechsel (connected/disconnected + Zeitstempel +
letzter Fehler) in LiveState; `GET /api/status` liefert sie; Zustandswechsel
gehen zusätzlich als SSE-Event (`type: "status"`) an die UI.

**UI:** Punkt in der Sidebar neben dem Konto (grün = verbunden, rot = getrennt
mit Uhrzeit im Tooltip und Klartext-Zeile unter dem Kontonamen, solange getrennt).

## 6. Sortier-Automatik (launchd)

**Was:** Der email-agent sortiert alle 30 Minuten neu ankommende Mails
(`--no-drafts`, echte Ausführung). LaunchAgent im User-Scope:
`~/Library/LaunchAgents/de.postfach.email-agent.plist`, Logs nach
`~/Library/Logs/postfach-email-agent.log`.

**Wie:** `scripts/install_automation.sh` (generiert plist mit korrekten Pfaden,
`launchctl bootstrap`), `scripts/uninstall_automation.sh` (bootout + rm).
Wird im Repo mitgeliefert; die Installation auf Tristans Mac ist Teil dieses
Batches (reversibel, User-Scope).

## Nicht in diesem Batch

Klick-Aktionen in Benachrichtigungen (braucht Signing), Bulk-„Verschieben in
Ordner X" (kommt mit dem View-Builder), Spam-KI (nur manuelle Markierung),
Undo (Batch 5).
