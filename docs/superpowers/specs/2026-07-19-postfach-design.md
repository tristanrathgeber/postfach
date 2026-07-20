# Postfach — Design (v0.1)

**Datum:** 2026-07-19 · **Status:** Beschlossen (autonome Session; Phasen-Zerlegung dokumentiert)

## Was das ist

Eine **lokale Mail-Anwendung im Stil von Notion Mail** für Tristans IMAP-Konten (selbst gehostet, GMX, Gmail …): aufgeräumtes 3-Spalten-UI, AI-sortierte Views, Tastatur-Triage, Command-Palette, AI-Antwortentwürfe im eigenen Schreibstil — und echtes Senden. Läuft komplett auf dem eigenen Rechner (Backend bindet nur 127.0.0.1); keine Cloud, keine Fremdserver außer den eigenen Mailservern (und der Anthropic-API für die AI-Features, wie beim email-agent konfigurierbar auf Ollama).

**Verhältnis zum email-agent:** `~/Projects/email-agent` bleibt eigenständig (mit seiner Niemals-Senden-Invariante) und wird als Bibliothek eingebunden — Classifier, Drafter, Stilprofil, Modelle, LLM-Backends kommen von dort. Postfach hat eine eigene, reichere Mail-Schicht (inkl. SMTP-Versand und Papierkorb), denn ein Mail-Client braucht beides.

## „Alles können" — Phasen-Zerlegung

„Wie Notion Mail und alles kann" ist ein Produkt, kein Sprint. Zerlegung:

| Phase | Inhalt |
|---|---|
| **v0.1 (diese Session)** | Multi-Account-Inbox, AI-Kategorien als Views (Split-Inbox), Mail lesen (sicheres HTML, Bilder blockiert), Anhänge herunterladen, Antworten/Verfassen mit AI-Entwurf im eigenen Stil, Senden (SMTP) + Sent-Ablage, Triage (Archiv, Papierkorb, gelesen/ungelesen, Label), IMAP-Suche, Cmd+K-Palette, Tastatur-Navigation (j/k/e/#/r/u), **Demo-Modus** mit Beispiel-Postfach |
| v0.2 | Konversations-Threads, Snooze, Später-senden + Undo-Send, eigener View-Builder (Filterregeln), Anhänge senden, Bulk-Triage, Auto-Refresh/IDLE-Push |
| v0.3 | Lokaler SQLite-Cache + Volltextsuche, Regel-Engine („wenn Absender X → Ordner Y"), Integrationen (Kalender, Notion), Mobile-Layout |

## Betrachtete Ansätze

| Ansatz | Bewertung |
|---|---|
| **A: FastAPI-Backend (email-agent als Lib) + React/Vite-Frontend (gewählt)** | Nutzt die getestete IMAP/LLM-Schicht wieder; sauberer API-Vertrag zwischen zwei unabhängig baubaren Hälften; Frontend-Freiheit für Notion-artiges UI. |
| B: Alles in Next.js (imapflow) | Müsste die komplette, bereits getestete Python-Mail-Intelligenz in TS neu bauen. Kein Gewinn. |
| C: Bestehenden Client (Thunderbird) + Add-on | UI-Decke zu niedrig für „wie Notion Mail"; kein eigenes Produkt. |

## Architektur

```
Browser (React/Vite/Tailwind, Port 8722 via FastAPI-Static)
   │  /api (JSON)
FastAPI (127.0.0.1:8722)
   ├── mail/  eigene Schicht: IMAP (imapclient) + SMTP (smtplib) + Sanitizer (nh3)
   ├── email_agent (Path-Dependency): Classifier, Drafter, Style, LLM-Backends
   └── Demo-Modus (POSTFACH_DEMO=1): In-Memory-Postfach mit Beispielmails
```

### API-Vertrag (verbindlich für beide Hälften)

```
GET  /api/accounts                          → [{name, address, provider}]
GET  /api/folders?account                   → [str]
GET  /api/messages?account&folder&limit     → [Summary]  (neueste zuerst)
GET  /api/messages/{account}/{uid}?folder   → Detail
GET  /api/messages/{account}/{uid}/attachments/{index}?folder → Binärdownload
POST /api/messages/{account}/{uid}/action   {action: archive|trash|read|unread|label, label?, folder} → {ok}
POST /api/classify   {account, folder, uids[]} → {uid: {category, is_newsletter, interesting, needs_reply, reason}}
POST /api/draft      {account, folder, uid}    → {text}
POST /api/send       {account, to[], cc[], subject, body, reply_to_uid?, folder?} → {ok}
GET  /api/search?account&q&folder           → [Summary]

Summary: {account, folder, uid, subject, from_name, from_addr, date, snippet,
          seen, has_attachments, category|null}
Detail:  Summary + {to[], cc[], reply_to|null, message_id, body_text,
          body_html|null (sanitisiert, Remote-Bilder blockiert),
          body_html_images|null (sanitisiert, Bilder erlaubt),
          attachments: [{index, filename, content_type, size}]}
```

### Sicherheitsmodell

- **Backend nur auf 127.0.0.1**; Single-User, keine Auth in v0.1 (dokumentiert).
- **HTML-Mails:** serverseitig mit `nh3` sanitisiert (kein Script/Style/Event-Handler); Remote-Bilder standardmäßig blockiert (`src` → `data-blocked-src`, Tracking-Schutz), auf Klick „Bilder laden" liefert die API die Bilder-Variante. Frontend rendert zusätzlich in **sandboxed iframe**.
- **Senden & Löschen nur durch Menschen:** ausschließlich als Reaktion auf UI-Aktionen. Die AI-Schicht (Classifier/Drafter) hat keinerlei Zugriff auf Send-/Trash-Pfade — per Test erzwungen (kein Import der SMTP-/Action-Module aus AI-Modulen; kein „auto send" irgendwo).
- **Papierkorb statt Löschen:** `trash` = MOVE in den Trash-Ordner des Servers (dort gilt die Server-Aufbewahrung). Kein Expunge in v0.1.
- **LLM-Aufrufe** wie im email-agent: tool-los, Injection-Guard, Mailinhalte sind Daten.
- Credentials wie gehabt via `.env` (`MAIL_<NAME>_PASSWORD`), nie in Logs/Responses.

### Konfiguration (`config/config.yaml`)

Wie email-agent-`accounts`, plus SMTP: `smtp_host` (Default = imap_host), `smtp_port` (Default 587 = STARTTLS; 465 = SSL). Gmail-Provider: `smtp.gmail.com`. LLM-Einstellungen identisch zum email-agent (claude Default, ollama Option).

### Frontend (Notion-Mail-Anmutung)

3 Spalten: **Sidebar** (Konten, Views: Inbox, je AI-Kategorie, Ungelesen, Ordner) · **Mail-Liste** (dichte Zeilen: Absender, Betreff+Snippet, Kategorie-Chip, Zeit; Hover-Aktionen) · **Lesebereich** (Header, sandboxed HTML, Anhänge, Antwort-Composer einblendbar). Cmd+K-Palette (Aktionen + Suche), Tasten: j/k (Navigation), e (Archiv), # (Papierkorb), u (ungelesen), r (Antworten), c (Verfassen), / (Suche), Esc. Composer mit „AI-Entwurf"-Button (nutzt Stilprofil). Klassifikation: Button „Sortieren" pro Ansicht + automatisch beim Laden neuer Inbox-Mails; Ergebnis-Cache in `data/classify.json` (keyed account+uid), damit LLM-Kosten einmalig pro Mail anfallen.

Stack: Vite + React + TypeScript + Tailwind, TanStack Query, cmdk. Kein UI-Kit — eigener, ruhiger Look (Systemfont, viel Weißraum, dezente Grautöne, Kategorie-Chips).

### Demo-Modus

`POSTFACH_DEMO=1`: In-Memory-Mailbox (deutsche Beispielmails aller Kategorien, HTML/Plain/Anhang-Fälle) + Fake-LLM. Zweck: UI sofort ausprobierbar ohne Credentials; Ende-zu-Ende-Verifikation im Browser; Screenshots. Demo-„Senden" landet im Demo-Sent-Ordner.

## Fehlerbehandlung

Konto nicht erreichbar → API 502 mit Meldung, UI zeigt Banner je Konto, andere Konten funktionieren. LLM-Fehler → Klassifikation „Sonstiges"/Entwurf-Fehlermeldung im Composer, nie blockierend. SMTP-Fehler → Fehlerdialog, Mail bleibt im Composer erhalten. IMAP-Verbindungen pro Request (v0.1, einfach & robust); Verbindungspooling erst bei Bedarf (YAGNI).

## Tests

Backend TDD (pytest): API-Routen mit Fake-Mail-Schicht + Fake-LLM (Muster aus email-agent), Sanitizer-Fälle (Script/Event-Handler/Remote-Bilder), SMTP-Versand gemockt (Empfänger, Threading-Header, Sent-APPEND), Demo-Modus-Smoke, **Safety-Tests** (AI-Module importieren keine Send-/Action-Pfade; kein Send ohne expliziten API-Call). Frontend: Verifikation über echten Browser-Lauf im Demo-Modus (Screenshots, Klickpfade); Komponententests v0.2.

## Bewusst weggelassen (v0.1)

Threads, Snooze/Send-later, View-Builder, Attachment-Versand, IDLE, Offline-Cache, Auth/Mehrbenutzer, Mobile.
