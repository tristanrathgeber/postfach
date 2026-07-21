# Postfach API-Vertrag v0.1 (EINGEFROREN — beide Seiten bauen exakt dagegen)

Base-URL: gleiche Origin (`/api/...`). Alle Antworten JSON (außer Attachment-Download).
Fehler: `{"detail": "<menschenlesbare Meldung>"}` mit Status 4xx/5xx; Konto nicht erreichbar → **502**.

## Typen

```ts
type Account = { name: string; address: string; provider: "imap" | "gmail" };

type Summary = {
  account: string; folder: string; uid: number;
  subject: string; from_name: string; from_addr: string;
  date: string;              // ISO 8601, z. B. "2026-07-19T10:23:00+02:00"
  snippet: string;           // erste ~120 Zeichen Klartext
  seen: boolean; has_attachments: boolean;
  category: string | null;   // z. B. "Newsletter", "Rechnungen" … oder null = unklassifiziert
};

type Attachment = { index: number; filename: string; content_type: string; size: number };

type Detail = Summary & {
  to: string[]; cc: string[]; reply_to: string | null; message_id: string;
  body_text: string;
  body_html: string | null;         // sanitisiert, Remote-Bilder BLOCKIERT (src/srcset komplett entfernt)
  body_html_images: string | null;  // sanitisiert, Remote-Bilder erlaubt (für "Bilder laden")
  attachments: Attachment[];
};

type Classification = {
  category: string; is_newsletter: boolean; interesting: boolean;
  needs_reply: boolean; reason: string;
};
```

## Endpunkte

| Methode & Pfad | Request | Response |
|---|---|---|
| `GET /api/accounts` | — | `Account[]` |
| `GET /api/folders?account=` | — | `string[]` |
| `GET /api/messages?account=&folder=INBOX&limit=50` | — | `Summary[]` (neueste zuerst) |
| `GET /api/messages/{account}/{uid}?folder=INBOX` | — | `Detail` |
| `GET /api/messages/{account}/{uid}/attachments/{index}?folder=INBOX` | — | Binärstream mit Content-Disposition |
| `POST /api/messages/{account}/{uid}/action` | `{"action":"archive"\|"trash"\|"read"\|"unread"\|"label","label"?:string,"folder":"INBOX"}` | `{"ok":true}` |
| `POST /api/classify` | `{"account":string,"folder":string,"uids":number[]}` | `{"<uid>": Classification, …}` |
| `POST /api/draft` | `{"account":string,"folder":string,"uid":number}` | `{"text":string}` |
| `POST /api/send` | `{"account":string,"to":string[],"cc":string[],"subject":string,"body":string,"reply_to_uid"?:number,"folder"?:string}` | `{"ok":true, "warning"?:string}` — warning: SMTP ok, aber Gesendet-Ablage fehlgeschlagen (Mail NICHT erneut senden) |
| `GET /api/search?account=&q=&folder=INBOX` | — | `Summary[]` |

## Verhaltensregeln

- Kategorien-Vokabular = email-agent-Taxonomie: `Newsletter, Newsletter-Interessant, Aktion-nötig, Rechnungen, Bestellungen, Entwicklung, Verein, Termine, Werbung, Sonstiges` (+ evtl. eigene aus config). Frontend behandelt die Liste dynamisch (aus tatsächlich gelieferten Kategorien), hardcodet aber die Chip-Farben für die bekannten zehn.
- `classify` ist idempotent & gecacht: bereits klassifizierte uids kommen aus dem Cache, kosten nichts.
- `archive` verschiebt in `AI/<category>`-Ordner falls klassifiziert, sonst in „Archive"-Ordner des Servers.
- `send` mit `reply_to_uid` setzt automatisch `Re:`-Betreff-Fallback und Threading-Header serverseitig; `to` ist im Reply vorbefüllt vom Frontend (Reply-To bzw. From der Originalmail).
- Demo-Modus (`POSTFACH_DEMO=1`): identischer Vertrag, In-Memory-Daten, `send` legt in „Gesendet" ab.
- Öffnen einer Mail markiert sie NICHT automatisch als gelesen — das Frontend sendet explizit `action:"read"` beim Öffnen (damit ist das Verhalten testbar und später abschaltbar).

## Nachtrag v0.2 — Emilia (eingefroren 2026-07-20)

| Methode & Pfad | Request | Response |
|---|---|---|
| `POST /api/emilia/chat` | `{"account":string,"message":string,"folder"?:string,"uid"?:number}` | `{"reply":string,"sources":[{account,folder,uid,subject,from_name,date}]}` |
| `POST /api/emilia/improve` | `{"text":string,"mode":"korrigieren"\|"verbessern"}` | `{"text":string}` |
| `POST /api/emilia/index` | `{"account":string}` | `{"indexed":number}` |
| `GET /api/emilia/status` | — | `{"model":string,"embed_model":string,"indexed_mails":number,"sort_local":boolean}` |

Verhalten: `chat` antwortet deutsch, `sources` = die tatsächlich verwendeten Gedächtnis-Treffer
(kann leer sein); `uid`/`folder` geben der Frage den Kontext der geöffneten Mail. `improve`
gibt NUR den überarbeiteten Text zurück. `index` ist idempotent (aktualisiert Bestand).

## Nachtrag v0.3 — Batch 1 „Schreiben komplett" (eingefroren 2026-07-21)

| Methode & Pfad | Request | Response |
|---|---|---|
| `GET /api/settings` | — | `{"signatures":{"<konto>":string}}` |
| `PUT /api/settings` | `{"signatures":{...}}` | `{"ok":true}` |
| `GET /api/contacts?q=&limit=8` | — | `[{"name":string,"addr":string}]` (Ranking: Häufigkeit×Aktualität, Sent-Empfänger doppelt) |
| `GET /api/drafts?account=` | — | `[Draft]` |
| `POST /api/drafts` | Draft, `id` optional (mit id = **Upsert** fürs Auto-Save) | `{"id":string}` |
| `DELETE /api/drafts/{id}` | — | `{"ok":true}` |
| `GET /api/snippets` | — | `[{"abbrev","title","text"}]` |
| `PUT /api/snippets` | `[items]` | `{"ok":true}` |

`Draft = {id, account, to: string[], cc: string[], bcc: string[], subject, body,
mode: "new"|"reply"|"forward", ref_folder?: string, ref_uid?: number, updated: iso}`

**`POST /api/send` erweitert (JSON-Variante bleibt gültig):**
- JSON-Body zusätzlich: `"bcc": string[]`, `"forward_of": {"folder","uid","include_attachments": bool}` (Server hängt Original-Anhänge an)
- NEU multipart/form-data: Feld `payload` (obiges JSON als String) + `files` (0..n Anhänge, gesamt ≤ 25 MB → 413 bei Überschreitung)
- Gesendet-Kopie behält Bcc-Header; SMTP-Versand entfernt ihn (Envelope korrekt)

## Nachtrag v0.3.1 — Review-Härtung Batch 1 (2026-07-21)

- `POST /api/send`: neu `"draft_id"?: string` — Server löscht den Entwurf nach
  erfolgreichem Versand (atomar gegenüber spät ankommenden Auto-Save-Upserts).
  Das 25-MB-Limit zählt auch serverseitig eingesammelte Weiterleitungs-Anhänge.
  Header-Werte (to/cc/bcc/subject, Anhang-Namen) werden CRLF-bereinigt.
- `Draft` zusätzlich: `"include_attachments"?: bool` (Weiterleitung: Checkbox-Zustand).

## Nachtrag v0.4 — Batch 2 „Empfangen & Ordnung" (eingefroren 2026-07-21)

| Methode & Pfad | Request | Response |
|---|---|---|
| `POST /api/batch-action` | `{"account","folder","uids":[number],"action":"read"\|"unread"\|"archive"\|"trash"\|"spam"\|"unspam"}` | `{"ok":true,"done":number}` |
| `POST /api/messages/{account}/{uid}/action` | zusätzlich erlaubt: `"action":"spam"\|"unspam"` | `{"ok":true}` |
| `POST /api/classify/override` | `{"account","folder","uid","category"}` (nur konfigurierte Kategorien, sonst 422) | `{"ok":true}` |
| `GET /api/status` | — | `{"accounts":{"<konto>":{"connected":bool,"since":iso\|null,"last_error":string\|null}}}` |
| `GET /api/settings` | erweitert | `{"signatures":{...},"notifications":{"<konto>":bool}}` (fehlender Eintrag = an) |
| `PUT /api/settings` | akzeptiert zusätzlich `"notifications"` | `{"ok":true}` |

Verhalten:
- `batch-action`: EINE IMAP-Verbindung, Aktionen als Listen-Operation; `archive`
  respektiert das Kategorie-Mapping pro Mail. Teilfehler → 502 mit Klartext.
- `spam` verschiebt in den Junk-Ordner (SPECIAL-USE `\Junk` → Namenssuche
  spam/junk/spamverdacht/werbung → anlegen „Spam"); `unspam` zurück in INBOX.
- Klassifikations-Overrides tragen `"source":"user"` im Cache und werden von
  der KI nie überschrieben.
- SSE `GET /api/live` sendet zusätzlich `{"type":"status","account":string,"connected":bool}`.

## Nachtrag v0.5 — Batch 3 „Lokale Volltextsuche" (eingefroren 2026-07-21)

| Methode & Pfad | Request | Response |
|---|---|---|
| `GET /api/search?account=&q=&folder=` | unverändert | `[Summary]` — NEU: nach einem vollen Index-Lauf aus dem lokalen FTS5-Index, IMMER über ALLE Ordner des Kontos (Treffer tragen ihren echten `folder`; `folder=` wird auf diesem Pfad ignoriert). Ohne vollen Index → IMAP-Fallback im übergebenen Ordner (v0.4-Verhalten) |
| `GET /api/search/status?account=` | — | `{"indexed": number, "ready": boolean}` — ready erst nach einem VOLLEN Index-Lauf (einzelne Live-Push-Zeilen zählen nicht) |

Query-Operatoren in `q`: `von:` `an:` `betreff:` `vor:JJJJ-MM-TT` `nach:JJJJ-MM-TT`
`hat:anhang` sowie `"exakte Phrase"`. Nutzertext wird als FTS-Literal gequotet
(keine FTS-Syntax von außen). Ranking bm25 (Betreff > Absender/Empfänger > Body),
Limit 50. `POST /api/emilia/index` befüllt zusätzlich den Such-Index;
Move-Aktionen ENTFERNEN den Index-Eintrag (IMAP vergibt im Ziel neue UIDs —
ein Umzug wäre ein toter Treffer); der nächste Index-Lauf nimmt die Mail neu
auf und räumt extern Verschwundenes ab (Pruning). read/unread halten `seen`
im Index aktuell.

## Nachtrag v0.6 — Batch 4 „Konversations-Threads" (eingefroren 2026-07-21)

| Methode & Pfad | Request | Response |
|---|---|---|
| `GET /api/messages/{account}/{uid}/thread?folder=` | — | `[Summary & {"is_sent": bool}]` — der Gesprächsfaden, chronologisch aufsteigend, über ALLE Ordner (inkl. Gesendet). Ohne vollen Index/Eintrag: `[]` (UI zeigt die Leiste erst ab 2 Mails) |
| `GET /api/messages` | unverändert | `Summary` zusätzlich `"thread_count": number` (1 = Einzelmail; ohne vollen Index immer 1) |

Threading: `thread_root` = References[0] → In-Reply-To → eigene Message-ID;
Betreff-Fallback nur beim Index-Lauf und nur bei eindeutigem Kandidaten.
Thread-Triage läuft über die bestehende `POST /api/batch-action` mit den
UIDs des Fadens (Client-seitig pro Ordner gruppiert; Gesendet-Kopien werden
von der UI nicht angefasst).

## Nachtrag v0.7 — Batch 5 „Zeit-Features" (eingefroren 2026-07-21)

| Methode & Pfad | Request | Response |
|---|---|---|
| `POST /api/send` | zusätzlich `"send_at"?: iso` (Später senden), `"followup_days"?: number` (Erinnerung falls keine Antwort) | bei Undo-Verzögerung/send_at: `{"ok":true,"scheduled":{"id","due","kind":"undo"\|"later"}}`, sonst wie bisher |
| `GET /api/outbox?account=` | — | `[{"id","account","to":[..],"subject","due","kind"}]` — geplante Sends |
| `DELETE /api/outbox/{id}` | — | `{"ok":true}` — Storno; der Auto-Save-Entwurf bleibt erhalten |
| `POST /api/messages/{account}/{uid}/snooze` | `{"folder","until": iso}` | `{"ok":true,"id"}` — Mail wandert in den Ordner „Später", kehrt zur Zeit ungelesen in die INBOX zurück (Wiederfinden per Message-ID, nicht UID) |
| `GET /api/reminders?account=` | — | `[{"id","kind":"followup"\|"snooze","subject","due","info"}]` — anstehende Wiedervorlagen |
| `POST /api/reminders/{id}/done` | — | `{"ok":true}` |
| `GET/PUT /api/settings` | zusätzlich `"undo_seconds": number` (0 = sofort senden; Default 15) | — |

Scheduler: lokale Warteschlange (data/schedule.json + data/outbox/), Tick 20 s,
Jobs idempotent und neustartfest. Follow-up löscht sich still, wenn der
Thread-Index eine fremde Antwort nach dem Versandzeitpunkt kennt.
Sicherheits-Invariante: Nur explizite Senden-Klicks legen Send-Jobs an.

## Nachtrag v0.8 — Batch 6 „Posteingangs-Hygiene" (eingefroren 2026-07-21)

| Methode & Pfad | Request | Response |
|---|---|---|
| `GET /api/subscriptions?account=` | — | `[{"addr","name","count","first_date","last_date","per_month","method":"oneclick"\|"mailto"\|"link"\|"none","unsubscribed_at":iso\|null}]` |
| `POST /api/subscriptions/unsubscribe` | `{"account","addr"}` | `{"ok":true,"method":"oneclick"\|"mailto"}` oder `{"ok":false,"method":"link","link":url}` (UI öffnet im Browser) |
| `GET /api/screener?account=` | — | `[{"addr","name","count","first_date","last_date","has_unsubscribe","subject","snippet","folder","uid","suggestion":"allow"\|"block","reason"}]` — Erstkontakte ohne Entscheidung; subject/snippet/folder/uid = neueste Mail des Absenders |
| `POST /api/screener/decide` | `{"account","addr","decision":"allow"\|"block"}` | `{"ok":true}` |

Abmelde-Strategie: RFC-8058-One-Click-POST (nur https, keine Redirects) →
mailto-Send über den normalen SMTP-Pfad (explizite UI-Aktion) → sonst Link.
Screener: „block" ist eine NUTZER-Regel — der Live-Watcher verschiebt künftige
Mails des Absenders in den Ordner „Aussortiert" (nie Papierkorb, nie löschen)
und unterdrückt deren Benachrichtigung. Erstkontakt = erste Mail < 30 Tage,
Adresse nie Empfänger einer Gesendet-Mail, keine Entscheidung vorhanden.

## Nachtrag v0.9 — Batch 7 „Emilia II" (eingefroren 2026-07-21)

| Methode & Pfad | Request | Response |
|---|---|---|
| `POST /api/emilia/chat/stream` | wie `/api/emilia/chat` | NDJSON-Stream: `{"sources":[…]}` → `{"delta":"…"}`× → `{"done":true}` bzw. `{"error":"…"}` |
| `GET /api/search/nl?account=&q=` | — | `{"query":"<Operator-Query>","hits":[Summary…]}`; 409 wenn Index nicht ready |
| `POST /api/emilia/improve` | `{"text","mode"}` — mode neu auch `"sie"\|"du"\|"kuerzer"` | `{"text"}` |
| `POST /api/emilia/thread_summary` | `{"account","folder","uid"}` | `{"summary":"…","mails":n}`; 404 ohne Faden |
| `PUT /api/settings` | neu: `"ai_enabled": bool` (Teil-Update) | `{"ok":true}` |

`ai_enabled=false` ⇒ 403 auf `/api/classify`, `/api/draft`, `/api/search/nl`
und alle `/api/emilia/*`-Routen AUSSER `/emilia/index` (läuft weiter, überspringt
nur die Embeddings — FTS-Suche und Kontakt-Ernte sind keine KI) und
`/emilia/status` (Anzeige). Kategorie-Cache bleibt lesbar. Nach Reaktivierung
holt der nächste Voll-Index übersprungene Embeddings nach.
Streaming-Transport: `application/x-ndjson`, eine JSON-Zeile pro Ereignis.

## Nachtrag v0.10 — Batch 8 „Kalender-Minimum & Export" (eingefroren 2026-07-21)

| Methode & Pfad | Request | Response |
|---|---|---|
| `GET /api/messages/{account}/{uid}?folder=` | — | Detail zusätzlich: `"invite": Invite\|null`, `"entities": Entity[]` |
| `POST /api/invite/respond` | `{"account","folder","uid","response":"accepted"\|"tentative"\|"declined"}` | `{"ok":true}` bzw. `{"ok":true,"warning":"…"}`; 404 ohne Einladung |
| `GET /api/messages/{account}/{uid}/export?folder=` | — | `{"filename":"…​.md","markdown":"…"}` |

`Invite` = `{summary, start, end, all_day, location, organizer_name,
organizer_email, method, uid}` (start/end ISO-8601 oder Datum bei all_day).
`Entity` = `{kind:"date"\|"amount"\|"tracking", text, value, url?}` — `url`
nur bei Sendungsnummern (Anbieter-Tracking, Host-Allowlist).
RSVP läuft über den normalen Versandpfad (Nutzer-Klick, Sent-Ablage);
`text/calendar; method=REPLY` mit echtem ATTENDEE-PARTSTAT.

## Nachtrag v0.11 — Batch 9 „Onboarding & deutsche Provider" (eingefroren 2026-07-21)

| Methode & Pfad | Request | Response |
|---|---|---|
| `GET /api/providers` | — | `[{"id","label","imap_host","imap_port","smtp_host","smtp_port","note"}]` (id `custom` = manuell) |
| `POST /api/accounts/test` | `{provider,address,imap_host,imap_port,smtp_host,smtp_port,password}` | `{ok, imap:bool, smtp:bool, error?}` bzw. `{ok:true, demo:true}` |
| `POST /api/accounts` | Test-Body + `{name, sent_folder?}` | `{ok:true, watcher_pending:true}`; 409 bei Namenskonflikt |
| `DELETE /api/accounts/{name}` | — | `{ok:true}`; 409 wenn config.yaml-Konto (schreibgeschützt); 404 unbekannt |
| `GET /api/folder-map?account=` | — | `{categories:[…], folders:[…], mapping:{cat:folder}}` |
| `PUT /api/folder-map` | `{mapping:{cat:folder}}` | `{ok:true}` |

Passwort NUR im macOS-Schlüsselbund (Service `postfach`, Username = Kontoname),
nie in config.yaml/JSON/Index/Log. Auflösung: Env-Variable → Schlüsselbund.
UI-Konten in `data/accounts.json` (verwaltet); `config.yaml` bleibt unberührt.
`GET /api/accounts` liefert zusätzlich `"managed":bool` je Konto.
