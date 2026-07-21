# Batch 11 — Design (Design)

Stand: 2026-07-21 · Letzter Batch · rein Frontend (kein Contract-Nachtrag)

Der Feinschliff, bewusst zum Schluss: Dark Mode richtig gemacht, ein Reader-View,
Per-Konto-Farben, ein Dichte-Umschalter, und ein Polish-Pass. Die „Schreibtisch"-
Identität (warmes Papier, Tintenblau, Haarlinien, Newsreader-Kursiv) trägt in die
Nacht: ein *Nachttisch* — warme dunkle Töne, kein kaltes Schwarz, Tinte aufgehellt.

## 1. Token-System erweitern (Fundament für Dark Mode)

Heute streuen ~60 hartkodierte Farben durch die Komponenten (`bg-[#F1EFEA]` u. Ä.).
Die werden zu **semantischen CSS-Variablen** verdichtet und in `tailwind.config`
gemappt:
- Bestand: `--paper --surface --ink --muted --hairline --tinte --unread`
- Neu: `--hover` (Zeilen-Hover), `--tint` (tinte-getönte Fläche: Auswahl/Badges),
  `--tinte-strong` (Button-Hover), `--danger --danger-bg`, `--success --success-bg`,
  `--accent-warm` (Warn/Betrag-Badge).

Alle `#hex`- und `red-/green-`-Literale in den Komponenten werden durch diese
Tokens ersetzt (systematisch, ein Durchgang).

## 2. Dark Mode

**Theme-Umschalter:** `system | hell | dunkel`, in localStorage gemerkt,
`data-theme`-Attribut am `<html>` (überstimmt die `prefers-color-scheme`-Media-Query).
Umschalten im Über-/Einstellungs-Bereich UND per ⌘K.

**Dark-Palette** (Nachttisch): `--paper #1B1A17`, `--surface #232220`,
`--ink #E8E5DC`, `--muted #979283`, `--hairline #37352F`, `--tinte #9BAAEC`
(aufgehellt für Kontrast auf dunkel), plus die neuen Tokens dunkel abgestimmt.

**Original-Mail bleibt im HELLEN Papier-Container** (Roadmap-Kern): der Mail-Body
(HTML-iframe UND Klartext-`<pre>`) rendert IMMER auf hellem Papier — E-Mails sind
für Weiß gestaltet, Invertieren zerstört Layout/Kontrast, und **Bilder werden nie
invertiert**. Der App-Rahmen (Sidebar, Liste, Reader-Kopf) wird dunkel, der
Mail-Inhalt sitzt als heller „Papierbogen" darin. „Smart-Darkening pro Mail" wäre
Over-Engineering — nicht in diesem Batch (YAGNI); der helle Bogen ist die richtige,
robuste Antwort.

## 3. Reader-View

Eine Taste (`v`) / ein Knopf im Reader schaltet zwischen **Normal** und
**Lesen**: Klartext-Extraktion des Mail-Texts (bereits vorhanden als `body_text`),
zitierte Vor-Mails (`> …` / „Am … schrieb") ausgeblendet bzw. eingeklappt, in
ruhiger Newsreader-Typografie mit angenehmem Zeilenmaß (~68 ch), größerer
Zeilenhöhe. Kein HTML, keine Remote-Bilder, keine Ablenkung. Zustand pro geöffneter
Mail zurückgesetzt.

## 4. Per-Konto-Farbcodierung

Jedes Konto bekommt eine stabile Akzentfarbe (deterministisch aus dem Kontonamen,
aus einer harmonischen Palette). Anzeige: ein schmaler Farbstreifen/Punkt links an
den Listenzeilen (nur in „Alle Konten") und am Konto-Eintrag der Sidebar — hilft,
in der Unified Inbox Herkunft auf einen Blick zu sehen.

## 5. Dichte-Umschalter + Polish

- **Dichte** `komfortabel | kompakt` (localStorage): steuert die vertikale Polsterung
  der Listenzeilen (kompakt = mehr Mails auf den Schirm).
- **Leerzustände** vereinheitlichen (schon `EmptyState` — Ton/Abstände prüfen).
- **Motion/Toast**: `prefers-reduced-motion` respektieren (Animationen aus), Toast-
  Ein/Ausblenden ruhiger.
- **Polish-Pass**: Fokus-Ringe, Kontraste (WCAG AA in beiden Themes), Icon-Größen
  konsistent.

## Umsetzung & Prüfung

- Tokens + tailwind.config + index.css (Light/Dark/`data-theme`), dann komponenten-
  weiter Ersetz-Durchgang.
- `useTheme`/`useDensity`-Hooks (localStorage, System-Media-Query-Listener).
- E2E in der Demo: Screenshots in HELL und DUNKEL; Mail-Reader zeigt den hellen
  Papierbogen auch im Dark Mode; Reader-View-Umschaltung; Dichte; Per-Konto-Farbe.
- Kontrast stichprobenhaft prüfen; `prefers-reduced-motion` testen.
- Kein neuer Backend-Code → Backend-Tests unverändert grün; Frontend build/lint/test.

## Nicht in diesem Batch

Smart-Darkening einzelner Mails (heller Bogen ist die Antwort), Theme-Editor/eigene
Farben, Auto-Theme nach Tageszeit, Windows/Linux-spezifisches Design.
