# Postfach — Handbuch

Das vollständige Benutzerhandbuch zu **Postfach**, der local-first Mail-App für
deinen Mac, und **Emilia**, dem eingebauten KI-Copiloten, der komplett lokal
läuft. Dieses Handbuch erklärt jede Funktion — von den ersten Schritten bis zu
jedem Tastaturkürzel.

> **Kurz gesagt:** Postfach läuft ausschließlich auf deinem Mac. Kein Konto bei
> uns, keine Telemetrie, und standardmäßig keine Cloud — die KI rechnet lokal
> über [Ollama](https://ollama.com). Was nach außen geht, kannst du jederzeit im
> Dialog **Über Postfach** nachlesen.

---

## Inhalt

1. [Was ist Postfach?](#1-was-ist-postfach)
2. [Erste Schritte](#2-erste-schritte)
3. [Konten einrichten](#3-konten-einrichten)
4. [Die Oberfläche im Überblick](#4-die-oberfläche-im-überblick)
5. [Lesen](#5-lesen)
6. [Schreiben & Antworten](#6-schreiben--antworten)
7. [Senden mit Netz — Undo, Später, Wiedervorlage](#7-senden-mit-netz--undo-später-wiedervorlage)
8. [Ordnung halten — Kategorien, Bulk, Spam](#8-ordnung-halten--kategorien-bulk-spam)
9. [Suchen](#9-suchen)
10. [Posteingang aufräumen — Abos & Screener](#10-posteingang-aufräumen--abos--screener)
11. [Emilia — der lokale KI-Copilot](#11-emilia--der-lokale-ki-copilot)
12. [Kalender-Einladungen & Export](#12-kalender-einladungen--export)
13. [Farbthemen & Erscheinungsbild](#13-farbthemen--erscheinungsbild)
14. [Modell-Assistent (Cookbook)](#14-modell-assistent-cookbook)
15. [Benachrichtigungen & Live-Push](#15-benachrichtigungen--live-push)
16. [Privatsphäre — nachprüfbar](#16-privatsphäre--nachprüfbar)
17. [Einstellungen (Referenz)](#17-einstellungen-referenz)
18. [Tastaturkürzel (Referenz)](#18-tastaturkürzel-referenz)
19. [Diagnose & Fehlerberichte](#19-diagnose--fehlerberichte)
20. [Häufige Fragen & Problemlösung](#20-häufige-fragen--problemlösung)

---

## 1. Was ist Postfach?

Postfach ist ein E-Mail-Programm im Geist von Notion Mail — für **jedes
IMAP-Konto** (selbst gehostet, GMX, web.de, T-Online, Gmail, iCloud …). Es ist
**local-first**: die App läuft auf `127.0.0.1:8722` auf deinem Mac, speichert
alles lokal und verlangt kein Konto bei uns.

Drei Dinge machen Postfach besonders:

- **Emilia**, ein KI-Copilot, der **vollständig lokal** über Ollama rechnet: Fragen
  zum Postfach beantworten (mit Quellen-Chips), Entwürfe in deinem Ton umformulieren,
  auf Deutsch suchen, lange Fäden zusammenfassen — alles offline.
- **Senden mit Netz**: Rückgängig-Senden, Später senden, Snooze und Wiedervorlage —
  neustartfest in einer lokalen Warteschlange.
- **Nachprüfbare Privatheit**: keine Telemetrie, und der Dialog *Über Postfach* zeigt
  jede ausgehende Verbindung ehrlich an — inklusive Cloud-KI, falls du sie einschaltest.

---

## 2. Erste Schritte

**Installieren.** Postfach kommt als **DMG**. Ein Doppelklick öffnet ein Fenster
mit der App und einer Verknüpfung **Programme** — zieh **„Postfach" auf
„Programme"**, das war die Installation. Kein Entpacken, kein Terminal. Dieselbe
Anleitung liegt als *Zuerst lesen.txt* sichtbar im Fenster daneben.

Beim ersten Öffnen meldet macOS, die App sei „nicht überprüft": Postfach ist
unsigniert (Notarisierung verlangt ein kostenpflichtiges Apple-Entwicklerkonto).
Einmalig **Systemeinstellungen → Datenschutz & Sicherheit** öffnen und unten bei
der Meldung zu Postfach auf **„Trotzdem öffnen"** klicken — danach startet die
App normal. (Rechtsklick → Öffnen umgeht das auf aktuellem macOS nicht mehr.)

**Starten.** Öffne die App `Postfach.app`. Sie startet im Hintergrund einen
lokalen Server und öffnet das Fenster. Solange die App läuft, hält sie eine
Push-Verbindung (IMAP IDLE) zu deinem Postfach, damit neue Mail sofort erscheint.
Hat Postfach sich sein eigenes Ollama eingerichtet, fährt es das dabei gleich mit
hoch (→ [Kap. 14](#14-modell-assistent-cookbook)).

**Erster Start.** Ohne Konto ist die App leer — deshalb öffnet sich der
Konto-Dialog **von selbst**, einmal pro Sitzung. Schließt du ihn bewusst, kommt
er nicht wieder; der Knopf **+ Konto hinzufügen** links bleibt
(→ [Konten einrichten](#3-konten-einrichten)).

**Wo alles liegt.** Konfiguration, lokale Daten und das Protokoll stehen immer in
`~/Library/Application Support/Postfach` — auch bei einer Installation aus dem
Quellcode. Passwörter liegen nicht dort, sondern im macOS-Schlüsselbund.

**Zum Ausprobieren ohne eigenes Konto** gibt es einen Demo-Modus mit Beispiel-Mails
(kein Versand, keine echten Server).

**Befehle finden.** Mit **⌘K** öffnest du die Befehlspalette — die schnellste Art,
jede Funktion zu erreichen. Tippe, wonach du suchst („Verfassen", „Einstellungen",
„Modell-Assistent" …). Am unteren Rand steht immer der Hinweis „⌘K Befehle".

---

## 3. Konten einrichten

Klicke in der Seitenleiste auf **+ Konto hinzufügen**. Beim allerersten Start
öffnet Postfach diesen Dialog von sich aus — du musst nichts suchen und keine
YAML-Datei anfassen.

**Formularfelder**

| Feld | Bedeutung |
|---|---|
| **Anbieter** | Wähle deinen Provider — die Serverdaten werden vorausgefüllt. |
| **Name** | Frei wählbarer Anzeigename (z. B. „Privat", „Verein"). |
| **E-Mail** | Deine Adresse. |
| **Passwort** | Bleibt im **macOS-Schlüsselbund** — Postfach speichert es nie im Klartext. |
| **Server** | IMAP-Host/-Port und SMTP-Host/-Port. Nur bei „Anderer (manuell)" frei editierbar. |

**Vorlagen für Anbieter:** GMX, web.de, T-Online, Posteo, mailbox.org, Freenet,
Gmail, iCloud und „Anderer (manuell)". Jede bringt die richtigen Server + einen
Hinweis mit. Beispiele:

- **GMX / web.de:** IMAP muss im Webmail unter *Einstellungen → POP3/IMAP* erst
  aktiviert werden. (GMX nutzt `imap.gmx.net` zum Empfangen, `mail.gmx.net` zum Senden.)
- **Gmail / iCloud:** brauchen ein **App-spezifisches Passwort** (nicht dein normales),
  weil sie normale Passwörter für Fremd-Clients sperren.

**Ablauf:** Erst **Verbindung testen** (loggt sich in IMAP *und* SMTP ein, ohne zu
speichern), dann **Speichern** — das Speichern verlangt einen erfolgreichen Test.
Danach: *„Konto gespeichert. Live-Benachrichtigungen ab dem nächsten Neustart."*

Standard-Ports: IMAP **993** (SSL), SMTP **587** (STARTTLS; 465 = SSL).

Über die App hinzugefügte Konten kannst du in den Einstellungen wieder entfernen.
In `config.yaml` eingetragene Konten sind schreibgeschützt.

---

## 4. Die Oberfläche im Überblick

Postfach hat drei Spalten:

- **Seitenleiste (links):** Konten, Ansichten (Inbox, Ungelesen, Entwürfe, Ausgang,
  Wiedervorlage), der Bereich **Hygiene** (Abos, Screener), Kategorien und der
  vollständige IMAP-Ordnerbaum. Unten: Einstellungen (Zahnrad) und der Hinweis
  „⌘K Befehle".
- **Nachrichtenliste (Mitte):** die Mails der gewählten Ansicht mit Suchfeld,
  Sortieren-Knopf und der Bulk-Leiste bei Mehrfachauswahl.
- **Leseansicht (rechts):** die geöffnete Mail mit Aktionsleiste, Kategorie-Chip,
  Entitäts-Chips (Termine/Beträge/Sendungen) und ggf. dem Gesprächsfaden.

Oben rechts erreichst du **Emilia** (Knopf oder ⌘J). In der Ansicht *Alle Konten*
zeigt ein farbiger Punkt pro Zeile, aus welchem Konto die Mail stammt.

---

## 5. Lesen

**Öffnen:** Klicke eine Mail an oder wähle sie mit `j`/`k` und drücke `Enter`/`o`.

**Lesen-Ansicht (Taste `v` oder Knopf „Lesen").** Schaltet in eine ruhige
Serifen-Ansicht, die nur den *neuen* Text zeigt und den zitierten Verlauf
ausblendet („Zitierter Verlauf ausgeblendet — Taste v zeigt das Original"). Ideal
für lange Antwort-Ketten. Der Hinweis erscheint nur, wenn wirklich etwas
eingeklappt wurde.

**Externe Bilder** sind zunächst blockiert („Externe Bilder blockiert"). Ein Klick
auf **Bilder laden** zeigt sie — aber nur für genau diese eine Mail. HTML-Mails
werden in einem abgeschotteten Rahmen ohne Skripte gerendert und stehen in **jedem
Theme auf hellem Papier** (E-Mails sind für Weiß gestaltet).

**Anhänge ansehen.** Unter der Mail steht jeder Anhang als Knopf mit Name und
Größe; ein Auge-Symbol zeigt, dass sich eine Vorschau öffnen lässt. Ein Klick
öffnet die **Vorschau als Overlay** über der App:

- **Bilder**, **PDF** und **Text/CSV** werden direkt angezeigt.
- Bei mehreren Anhängen blätterst du mit **‹ ›** oder **←/→**; oben steht
  „{Name} · 3 von 5".
- **Esc**, das **✕** oben rechts oder ein Klick auf den dunklen Rand schließen.
  Solange die Vorschau offen ist, erreicht keine Taste die Mail darunter — `e`
  archiviert also nichts aus Versehen.
- **Herunterladen** legt die Datei zuverlässig in **`~/Downloads`** ab („In
  ‚Downloads' gespeichert: …"). Ein schon vorhandener Name wird nicht
  überschrieben, sondern zu `Rechnung (1).pdf`.
- Dateitypen, die im Browser Skripte ausführen könnten (**HTML, SVG, XML**),
  zeigt Postfach bewusst **nicht** an: dort steht „Keine Vorschau möglich" mit dem
  Download-Knopf. Der Server liefert solche Anhänge grundsätzlich nur als Download
  aus, nie zur Anzeige.

**Gesprächsfäden (Threads).** Gehört eine Mail zu einem Faden (> 1 Nachricht),
erscheint rechts die Leiste **Konversation (N)**. Klicke eine Mail darin an, um sie
zu öffnen. Mit **Faden archivieren** / **Papierkorb** räumst du den ganzen Verlauf
(nur empfangene Kopien; deine gesendeten bleiben).

**Entitäts-Chips.** Postfach erkennt lokal (ohne KI) **Termine** (Datum/Uhrzeit),
**Beträge** (€/EUR) und **Sendungen** (Sendungsnummern von UPS/DHL/Hermes/DPD →
öffnet die Sendungsverfolgung). Andere Chips kopieren beim Klick in die Zwischenablage.

**Kategorie ändern.** Über den Kategorie-Chip korrigierst du die Einordnung per
Dropdown — deine Korrektur bleibt, die KI überschreibt sie nie.

**Zusammenfassen** (nur mit KI und ab 3 Mails im Faden, nur auf Klick) → siehe
[Emilia](#11-emilia--der-lokale-ki-copilot).

---

## 6. Schreiben & Antworten

Der Verfassen-Bereich öffnet sich als Panel von rechts.

- **Neu:** Taste `c` oder ⌘K → „Verfassen".
- **Antworten:** Taste `r`. Empfänger und `Re:`-Betreff werden vorbelegt (kein
  doppeltes `Re:`/`AW:`).
- **Weiterleiten:** Taste `f`. `Fwd:`-Betreff + zitiertes Original. Mit der Checkbox
  **Original-Anhänge mitsenden (N)** nimmst du die Anhänge mit.
- **CC / BCC:** Über **+ CC** / **+ BCC** einblenden. BCC ist ein vollwertiges Feld.
- **Empfänger** gibst du als Chips ein; ab 2 Zeichen schlägt Postfach Kontakte vor.
  Komma, Semikolon oder Einfügen trennt mehrere Adressen.

**Signaturen (pro Konto).** Werden automatisch mit `-- `-Trenner angefügt, bei
Antworten vor dem Zitat, und wechseln mit, wenn du das „Von"-Konto änderst. Pflege
sie in den [Einstellungen](#17-einstellungen-referenz).

**Entwürfe (Auto-Speichern).** Änderungen werden ~1,5 s nach der letzten Eingabe
automatisch gesichert; beim Schließen bleibt ein nicht-leerer Entwurf erhalten,
ein leerer wird verworfen. **Anhänge werden nicht im Entwurf gespeichert** (ein
Hinweis warnt dich). Nach erfolgreichem Versand löscht der Server den Entwurf.

**Anhänge.** Über den Knopf oder per Drag-and-drop auf das Panel. Grenze: **25 MB
gesamt** (Uploads *plus* mitgesendete Original-Anhänge); darüber lehnt der Server ab.

**Textbausteine (Snippets).** Tippe `;kürzel` und drücke `Tab`, oder füge sie per
⌘K ein. Platzhalter: `{vorname}` (Vorname des ersten Empfängers) und `{datum}`
(heute). Anlegen in den Einstellungen.

**Senden.** Der Knopf **Senden** fragt beim ersten Klick 3 s lang **„Wirklich
senden?"**. Es muss mindestens ein Empfänger da sein.

**KI-Hilfe beim Schreiben** (wenn KI an): **AI-Entwurf** (bei Antworten),
**Korrigieren**, **Verbessern** und **Ton ändern …** (Förmlich (Sie) / Locker (Du)
/ Kürzer). Jede Änderung lässt sich über den Hinweis rückgängig machen.

---

## 7. Senden mit Netz — Undo, Später, Wiedervorlage

Postfach führt Zeit-Aktionen in einer **lokalen, neustartfesten Warteschlange**
aus. Alle findest du in der Ansicht **Ausgang** (mit Abbrechen) bzw.
**Wiedervorlage**.

- **Rückgängig senden.** Nach dem Senden erscheint „Wird gesendet …" mit der Aktion
  **Rückgängig**. Wie lange, bestimmst du in den Einstellungen (*aus / 10 / 15 / 20
  / 30 Sekunden*).
- **Später senden.** Über das **▾** neben Senden: Vorlagen **Heute 18:00, Morgen
  08:00, Samstag 09:00, Montag 08:00**. Toast „Geplant für …" mit **Stornieren**
  (Stornieren legt den Text zurück in die Entwürfe).
- **Wiedervorlage (Follow-up).** Beim Verfassen: **Keine Erinnerung / Erinnern: 3
  Tage / Erinnern: 1 Woche**. Kommt bis dahin eine Antwort, löst sich die Erinnerung
  von selbst; sonst wirst du benachrichtigt.
- **Snooze.** Taste `z` schiebt eine Mail auf „Morgen 08:00" (bzw. per Menü auf eine
  andere Zeit). Sie verschwindet in einen „Später"-Ordner und kommt zur Zeit
  ungelesen zurück.
- **Wenn ein Versand scheitert.** Postfach probiert es mit wachsendem Abstand
  erneut — 1, 2, 4, 8, 16 und dann höchstens 30 Minuten, zusammen gut anderthalb
  Stunden. Ein zugeklappter Laptop oder ein WLAN-Wechsel begräbt eine Mail damit
  nicht mehr. Erst danach steht der Eintrag im **Ausgang** als *fehlgeschlagen*
  (rot) und du wirst benachrichtigt. Dort hast du dann zwei Knöpfe:
  **Wiederholen** stellt den Versand sofort wieder in die Schlange („Wird erneut
  versucht.") — der geschriebene Text ist noch da —, **Verwerfen** wirft ihn weg.

Sende-Jobs entstehen **ausschließlich** aus einem echten Sende-Klick — die
KI-Schicht kann nie senden.

---

## 8. Ordnung halten — Kategorien, Bulk, Spam

**Kategorien.** Postfach sortiert in die in `config.yaml` festgelegten Kategorien —
in der Standardkonfiguration: **Newsletter, Werbung, Bestellungen, Entwicklung,
Rechnungen, Verein, Termine, Sicherheit, Finanzen** (jede einem Ordner zugeordnet,
manche zum Archivieren). In der Seitenleiste erscheinen sie als farbige Filter.

**Sortieren (KI).** Der Knopf **Sortieren** (Listenkopf oder ⌘K) ordnet
unklassifizierte Inbox-Mail ein — nur, wenn die KI an ist und es überhaupt
Unklassifiziertes gibt. Ergebnisse werden lokal zwischengespeichert; **deine
Korrekturen schlagen immer die KI**.

**Mehrfachauswahl (Bulk-Triage).** Häkchen setzen mit `x` (mit `Shift` als Bereich)
oder per Checkbox. Die Bulk-Leiste zeigt „{n} ausgewählt" mit **Archivieren `e`**,
**Papierkorb `#`**, **Gelesen `u`**, **Spam `!`**.

**Spam.** Taste `!` markiert als Spam bzw. hebt es auf (die Richtung hängt vom
Ordner ab — im Spam-Ordner holt `!` die Mail zurück in die Inbox).

**Dichte.** In den Einstellungen: **Komfortabel** oder **Kompakt** (engere Zeilen).

---

## 9. Suchen

Suchfeld über die Taste `/`, das Feld selbst oder die Befehlspalette. Platzhalter:
`Suchen …  von: betreff: hat:anhang  ·  ? fragt Emilia  ( / )`.

**Operatoren:**

| Operator | Sucht nach |
|---|---|
| `von:` | Absender |
| `an:` | Empfänger |
| `betreff:` | Betreff |
| `vor:` | vor einem Datum |
| `nach:` | ab einem Datum |
| `hat:anhang` | hat einen Anhang |
| `"…"` | exakte Wortgruppe |

Alles andere ist Volltext. Deine Eingabe wird nie als Suchsyntax missverstanden
(jedes Wort wird sicher gequotet). Ist der Volltext-Index vollständig aufgebaut,
sucht Postfach **kontoweit über alle Ordner**; sonst greift ein IMAP-Fallback auf
den aktuellen Ordner. Treffer sind nach Relevanz und Datum sortiert.

**Natürlichsprachige Suche („? fragt Emilia").** Stell der Suche ein `?` voran und
frag auf Deutsch, z. B. `? rechnungen von der telekom aus dem letzten monat`.
Emilia übersetzt das lokal in Operatoren, die dann über die normale Suche laufen.
Die Übersetzung erscheint als Chip „Emilia sucht: …" — anklickbar zum Verfeinern.
(Braucht die KI *an* und einen vollständigen Index.)

---

## 10. Posteingang aufräumen — Abos & Screener

Im Seitenleisten-Bereich **Hygiene**:

**Abos (Abmelde-Manager).** Listet Absender mit `List-Unsubscribe`-Header, nach
Häufigkeit gruppiert („{n}/Monat"). Pro Absender zeigt ein Etikett die Methode:
**1-Klick** (RFC-8058-Abmeldung per HTTPS), **per Mail** (mailto über SMTP),
**Link** (öffnet die Abmeldeseite im Browser) oder **manuell**. Das Abmelden
verlangt eine **Doppelbestätigung** („Abmelden" → „Wirklich abmelden?"). Aufrufe
sind gegen SSRF abgesichert (nur öffentliche Hosts, keine Weiterleitungen).

**Screener (Erstkontakt-Türsteher, HEY-Stil).** Zeigt Absender, die dir zum ersten
Mal schreiben (erste Mail < 30 Tage alt, nie von dir angeschrieben). Zu jedem gibt
es einen begründeten Vorschlag „zulassen"/„ablehnen" (Newsletter, automatisch,
persönlich). Mit **Zulassen** / **Ablehnen** entscheidest du; Ablehnen leitet
künftige Mail in einen „Aussortiert"-Ordner — **nichts wird gelöscht**. Deine
Entscheidungen bleiben gespeichert.

---

## 11. Emilia — der lokale KI-Copilot

Emilia rechnet **vollständig lokal** über Ollama. Der zentrale Schalter ist in den
Einstellungen: **KI aktiviert** — „aus heißt wirklich aus" (dann ruht Sortieren,
Entwürfe, Chat, Umformulieren und KI-Suche; bereits vergebene Kategorien bleiben
sichtbar).

- **Chat (⌘J).** Öffnet Emilias Panel. Sie antwortet im Streaming und zitiert die
  tatsächlich genutzten Quell-Mails als anklickbare Chips. Grundlage ist ein lokales
  **Gedächtnis** (RAG), das du einmal über **Gedächtnis aufbauen** anlegst. Optional
  nimmt sie die gerade geöffnete Mail als Kontext. Die Kopfzeile zeigt „{Modell} ·
  lokal · {N} Mails im Gedächtnis".
- **Text verbessern (im Verfassen).** **Korrigieren**, **Verbessern** und die
  Ton-Modi **Förmlich (Sie) / Locker (Du) / Kürzer**.
- **Faden zusammenfassen.** Nur mit KI und ab 3 Mails, nur auf Klick.
- **Natürlichsprachige Suche.** Siehe [Suchen](#9-suchen).

**Lokal vs. Cloud.** Emilias Chat/Umformulieren/Suche laufen **immer lokal**.
Getrennt davon steuern zwei Schalter in `config.yaml`, ob **Sortieren**
(`sort_local`) und **Entwürfe** (`draft_local`) lokal oder über einen Cloud-Anbieter
laufen. Ein frisch installiertes Binary ist **vollständig lokal**. Schaltest du
einen davon auf Cloud, gehen dafür Mail-Inhalte an den Anbieter — und der Dialog
*Über Postfach* weist das dann **rot** aus.

---

## 12. Kalender-Einladungen & Export

**ICS-Einladungen (inline beantworten).** Enthält eine Mail eine Termin-Einladung,
zeigt die Leseansicht eine **Einladung**-Karte mit Titel, Zeit, Ort und Organisator
sowie den Knöpfen **Zusagen**, **Vielleicht**, **Absagen**. Die Antwort geht als
regulär gesendete ICS-Antwort raus (über den normalen Klick-Sende-Pfad). Danach:
„Zugesagt / Mit Vorbehalt / Abgesagt — Antwort gesendet".

**Als Markdown exportieren (Obsidian & Co.).** Der Knopf **Als Markdown** in der
Leseansicht erzeugt eine `.md`-Datei mit YAML-Frontmatter (Titel/Von/An/Datum,
`tags: [mail]`) plus Textkörper. Sie wird heruntergeladen und, wenn möglich,
zugleich in die Zwischenablage kopiert.

---

## 13. Farbthemen & Erscheinungsbild

In den Einstellungen unter **Erscheinungsbild**:

- **Theme: System / Hell / Dunkel.** *System* folgt macOS. Im Dunkelmodus bleibt die
  Original-Mail bewusst auf hellem Papier.
- **Dichte: Komfortabel / Kompakt.**
- **Farbthema (6 Paletten):**
  - **Schreibtisch** — warmes Papier, Tintenblau (Standard)
  - **Nord** — kühl-arktisches Frostblau
  - **Sepia** — warmes Lese-Creme
  - **Wald** — ruhiges Blattgrün
  - **Rosé** — weiche Malve
  - **Graphit** — minimal, hoher Kontrast

  Jede Palette hat eine eigene helle und dunkle Fassung und lässt sich mit dem
  Modus oben frei kombinieren.
- **Eigener Akzent.** Ein Farbwähler überschreibt den Akzent der Palette durch deine
  Wunschfarbe; **Zurücksetzen** stellt den Palettenakzent wieder her.

Alle Einstellungen wirken sofort, werden lokal gespeichert und schon vor dem ersten
Bildaufbau gesetzt (kein Aufblitzen beim Start). Per ⌘K → „Theme wechseln" springst
du schnell zwischen Hell und Dunkel.

---

## 14. Modell-Assistent (Cookbook)

Der **Modell-Assistent** (⌘K → „Modell-Assistent") findet die lokale KI, die am
besten zu Postfach *und* deinem Mac passt, lädt sie und richtet sie ein — im Geist
des Cookbooks aus PewDiePies Odysseus.

- **Dein System.** Postfach scannt Chip, RAM und Kerne und zeigt sie oben an.
- **Empfehlung.** Aus einem kuratierten Katalog empfiehlt es das Modell mit der
  höchsten **Passung** für Postfachs Aufgabe (deutsche Mail: JSON-Sortieren,
  Entwürfe, Chat), **das auf deinem RAM läuft** — nicht einfach das größte.
  Standard-Empfehlung ist **Qwen 2.5 · 7B**, der Sweetspot aus Qualität und Tempo.
- **Katalog.** Alle Modelle mit Größe, RAM-Bedarf, Stärken und Notiz. Badges:
  **Aktiv**, **Empfohlen**, **Installiert**, **Zu wenig RAM** (solche Zeilen sind
  ausgegraut).
- **Laden & Aktivieren.** Bei der Empfehlung genügt **Laden & aktivieren** (lädt per
  Ollama mit Fortschrittsbalken und macht es danach zu Emilias Modell). Andere
  Modelle bieten **Laden** bzw. **Aktivieren**. Aktivieren schreibt das Modell in
  `config.yaml` **und** schaltet die laufende App sofort um (kein Neustart) — es gilt
  dann zugleich fürs Sortieren/Entwerfen, wenn die lokal laufen.

**Ollama fehlt noch? Postfach richtet es selbst ein.** Ist keine KI-Laufzeit
erreichbar, steht oben die Karte *„KI-Laufzeit fehlt noch"* mit dem Knopf
**Ollama einrichten**. Ein Klick genügt — du musst nirgends etwas herunterladen:

- Postfach holt die **offizielle, aktuelle Ollama-Ausgabe** (rund 145 MB) von
  GitHub und zeigt dabei einen Fortschrittsbalken.
- Es prüft sie gegen die **von GitHub veröffentlichte SHA-256-Prüfsumme**. Stimmt
  sie nicht, wird nichts installiert.
- Entpackt wird in **Postfachs eigenen Datenordner** — kein Administratorrecht,
  nichts in `/Applications`, kein Eingriff ins System.
- Danach startet Postfach den Server gleich mit und tut das ab jetzt bei jedem
  App-Start automatisch.
- **Läuft schon ein Ollama-Server** (deiner oder ein selbst installierter), wird
  **nichts geladen** und kein zweiter gestartet — der Knopf erscheint dann gar
  nicht erst.

Im Demo-Modus sind Einrichten, Laden und Aktivieren deaktiviert (die Empfehlung
ist trotzdem echt).

---

## 15. Benachrichtigungen & Live-Push

- **Live-Push.** Solange die App läuft, hält sie pro Konto eine Push-Verbindung
  (IMAP IDLE) und zeigt neue Mail sofort („Neue Mail eingetroffen."). Verbindungsdots
  pro Konto in der Seitenleiste melden „wieder verbunden" / „Verbindung getrennt".
- **Desktop-Benachrichtigungen.** Native macOS-Hinweise mit Absender und Betreff, pro
  Konto in den Einstellungen an-/abschaltbar (Standard: an). Auch Zeit-Aktionen melden
  sich, wenn nötig („Senden fehlgeschlagen", „Keine Antwort erhalten" …).

---

## 16. Privatsphäre — nachprüfbar

Postfach baut **keine Verbindung auf, die du nicht angestoßen hast** — keine
Telemetrie, kein Analytics, kein Phone-Home. Der Dialog **Über Postfach** (⌘K →
„Über Postfach") listet **jedes** ausgehende Ziel zur Laufzeit:

- deine Konten: **IMAP** (empfangen/Push) und **SMTP** (senden auf Klick),
- **Ollama** `localhost:11434` (lokale KI),
- **api.github.com** (Update-Prüfung — **nur** auf Klick; von dort kommt auch die
  Ollama-Ausgabe, wenn du **Ollama einrichten** anklickst),
- und **nur falls** du Sortieren/Entwerfen auf Cloud gestellt hast, den **Cloud-KI-Host**
  (z. B. `api.anthropic.com`) — **rot** markiert mit dem Hinweis, dass dafür
  Mail-Inhalte den Anbieter erreichen.

Gibt es noch kein Konto, steht dort: „Noch kein Konto — bis dahin geht nichts nach
außen." Der **Update-Check** fragt GitHub ausschließlich auf deinen Klick; automatisch
passiert nie etwas.

---

## 17. Einstellungen (Referenz)

Zahnrad in der Seitenleiste oder ⌘K → „Einstellungen". Gespeichert wird beim
Schließen („Einstellungen gespeichert").

| Bereich | Was du einstellst |
|---|---|
| **Erscheinungsbild** | Theme (System/Hell/Dunkel), Dichte (Komfortabel/Kompakt), Farbthema (6 Paletten) + eigener Akzent → [Kap. 13](#13-farbthemen--erscheinungsbild) |
| **Signaturen** | Eine Signatur je Konto (mit `-- `-Trenner, in Antworten vor dem Zitat) |
| **Benachrichtigungen** | Desktop-Hinweise für neue Mail, pro Konto |
| **Senden** | Rückgängig-Fenster: aus / 10 / 15 / 20 / 30 Sekunden |
| **Emilia & KI** | Der globale Schalter **KI aktiviert** |
| **Konten** | Über die App hinzugefügte Konten entfernen (config.yaml-Konten sind schreibgeschützt) |
| **Ordner-Zuordnung** | Jede KI-Kategorie einem vorhandenen Ordner zuweisen (wichtig bei Providern mit Ordner-Limit wie GMX) |
| **Snippets** | Textbausteine: Kürzel / Titel / Text; Auslösung `;kürzel`+Tab oder ⌘K; Platzhalter `{vorname}`, `{datum}` |

---

## 18. Tastaturkürzel (Referenz)

Einzeltasten wirken **nicht**, während du in einem Eingabefeld tippst.

**Global**

| Taste | Aktion |
|---|---|
| `⌘K` | Befehlspalette öffnen/schließen |
| `⌘J` | Emilia öffnen/schließen (wenn KI an) |
| `Esc` | Schließen/Abbrechen (Palette → Composer → Auswahl aufheben → Emilia → Suche) |
| `/` | Suchfeld fokussieren |
| `g` dann `i` | Zur Inbox |

**In der Liste**

| Taste | Aktion |
|---|---|
| `j` / `k` | Auswahl runter / hoch |
| `Enter` / `o` | Mail öffnen |
| `x` | Häkchen setzen (`Shift` = Bereich) |
| `e` | Archivieren (Bulk oder ausgewählt) |
| `#` | In den Papierkorb |
| `z` | Snooze (auf „Morgen 08:00") |
| `!` | Spam / kein Spam |
| `u` | Gelesen / ungelesen |

**Bei geöffneter Mail**

| Taste | Aktion |
|---|---|
| `r` | Antworten |
| `f` | Weiterleiten |
| `v` | Lesen-Ansicht umschalten |

**In der Anhang-Vorschau** (andere Tasten sind hier bewusst wirkungslos)

| Taste | Aktion |
|---|---|
| `←` / `→` | Vorheriger / nächster Anhang |
| `Esc` | Vorschau schließen |

**Verfassen**

| Taste | Aktion |
|---|---|
| `;kürzel` + `Tab` | Snippet einsetzen |
| `Esc` | Schließen (zweimal innerhalb 3 s = verwerfen, wenn ungespeichert) |

> **Tipp:** Wenn du eine Aktion dreimal mit der Maus machst, blendet Postfach einmalig
> das passende Kürzel ein — so lernst du die Tastatur nebenbei.

---

## 19. Diagnose & Fehlerberichte

Postfach schreibt ein **Protokoll**. Die gebündelte App hat kein Konsolenfenster —
ohne Protokoll verschwände ein Startfehler oder ein abgerissener IMAP-Lauf spurlos,
und „die App tut nichts" wäre nicht nachvollziehbar.

- **Wo:** `~/Library/Application Support/Postfach/logs/postfach.log`. Die Datei
  wird bei etwa 1 MB rotiert, drei ältere Stände bleiben liegen (zusammen ~4 MB).
- **Was drinsteht:** Zeitpunkt, Modul, Fehlertext und Kennungen (Ordner, Job-Id).
  **Keine Mail-Inhalte, keine Passwörter.** Und keine Telemetrie: die Datei bleibt
  auf deinem Rechner, verschickt wird sie nie von allein.

**Angaben zum Mitschicken.** Der Dialog **Über Postfach** (⌘K → „Über Postfach")
hat den Block **Für Fehlerberichte** mit Betriebssystem, Architektur, Anzahl
Konten, Mails im Gedächtnis und dem Pfad zum Protokoll (mit dem Zusatz *(noch
leer)*, solange nichts geschrieben wurde). Der Knopf **kopieren** legt genau die
Zeilen in die Zwischenablage, die ein Bericht braucht:

```
Postfach 0.10.0 · macOS 15.5 · arm64
Konten: 2 · Modell: qwen2.5:7b · Embedding: jina/jina-embeddings-v2-base-de
Gedächtnis: 4213 Mails
Protokoll: /Users/…/Library/Application Support/Postfach/logs/postfach.log
```

**Ein gutes Issue** ([GitHub](https://github.com/tristanrathgeber/postfach/issues))
enthält diesen Block, dazu: was du getan hast, was passiert ist, was du erwartet
hättest. Passende Zeilen aus dem Protokoll helfen sehr — aber **lies sie vorher
durch** und füge **niemals Passwörter oder private Mail-Inhalte** ein. Ein Issue
ist öffentlich.

---

## 20. Häufige Fragen & Problemlösung

**Emilia/KI reagiert nicht.** Läuft Ollama? Öffne den **Modell-Assistenten**: fehlt
die Laufzeit, steht dort **Ollama einrichten** — ein Klick, und Postfach lädt und
startet sie selbst (→ [Kap. 14](#14-modell-assistent-cookbook)). Ist ein Modell
aktiv? Und ist **KI aktiviert** in den Einstellungen an?

**Die KI-Suche sagt „409" / verlangt einen Index.** Baue in Emilias Panel einmal das
**Gedächtnis** auf bzw. lass den Volltext-Index vollständig durchlaufen.

**Suche findet nur den aktuellen Ordner.** Der kontoweite Index ist noch nicht fertig
— bis dahin greift der IMAP-Fallback auf den offenen Ordner.

**GMX/web.de verbindet nicht.** Aktiviere IMAP im Webmail (Einstellungen →
POP3/IMAP). Prüfe, dass SMTP `mail.gmx.net` und IMAP `imap.gmx.net` heißt.

**Gmail/iCloud lehnt das Passwort ab.** Du brauchst ein **App-spezifisches Passwort**,
nicht dein normales.

**Eine gesendete Mail soll zurück.** Innerhalb des Rückgängig-Fensters „Rückgängig"
klicken. Länger vorplanen? Nutze **Später senden** und **Stornieren**.

**Ein Versand ist fehlgeschlagen.** Im **Ausgang** steht der Eintrag rot als
*fehlgeschlagen*. **Wiederholen** stellt ihn erneut in die Schlange — der Text ist
noch da (→ [Kap. 7](#7-senden-mit-netz--undo-später-wiedervorlage)).

**Anhang zu groß.** Grenze ist 25 MB gesamt (inkl. mitgesendeter Originale).

**Ein Anhang zeigt „Keine Vorschau möglich".** Der Typ (HTML, SVG, XML …) lässt
sich nicht sicher anzeigen. **Herunterladen** legt ihn in `~/Downloads` — von dort
öffnest du ihn mit dem Programm deiner Wahl.

**macOS sagt, die App sei „nicht überprüft".** Normal bei unsignierten Apps:
Systemeinstellungen → Datenschutz & Sicherheit → **„Trotzdem öffnen"**. Einmalig
(→ [Kap. 2](#2-erste-schritte)).

**Wo liegen meine Daten?** In `~/Library/Application Support/Postfach` —
Konfiguration, lokaler Index, Warteschlange und Protokoll. Passwörter stehen
ausschließlich im macOS-Schlüsselbund.

**Wo finde ich das Protokoll?**
`~/Library/Application Support/Postfach/logs/postfach.log`. Der Pfad steht auch im
Dialog **Über Postfach** unter „Für Fehlerberichte", mitsamt einem
Kopieren-Knopf für die Systemangaben (→ [Kap. 19](#19-diagnose--fehlerberichte)).

**Wo geht die App online?** Dialog **Über Postfach** — er zeigt jede Verbindung
ehrlich, inklusive Cloud-KI, falls aktiv.

---

*Postfach ist quelloffen (MIT-Lizenz): [github.com/tristanrathgeber/postfach](https://github.com/tristanrathgeber/postfach).
Fehler gefunden oder Wunsch offen? Ein Issue im Repository hilft weiter.*
