# Batch 6 — Posteingangs-Hygiene: Abo-Manager + Screener (Design)

Stand: 2026-07-21 · Contract-Addendum: v0.8 (in docs/api-contract.md)

## 1. Abo-Manager

**Datenquelle:** Der Such-Index bekommt zwei Spalten (`list_unsubscribe`,
`list_unsubscribe_post` — aus `ParsedMail.headers`, die der Parser schon
vollständig führt). Die Abo-Liste ist ein GROUP BY über Absender mit
Unsubscribe-Header: Name, Adresse, Mail-Anzahl, letzte Mail, Frequenz
(Mails/30 Tage aus Erst-/Letztdatum + Anzahl).

**1-Klick-Abmelden — Strategie in fester Reihenfolge (`unsubscribe.py`):**
1. **RFC-8058 One-Click**: `List-Unsubscribe-Post: List-Unsubscribe=One-Click`
   vorhanden → Server macht den HTTPS-POST selbst (httpx, `follow_redirects=False`,
   Timeout 15 s, nur https-URLs). Kein Browser, keine Tracker.
2. **mailto:** → die App sendet die Abmelde-Mail (Empfänger/Subject aus der
   mailto-URL; Betreff-Fallback "unsubscribe") über den normalen SMTP-Pfad.
   Das ist eine explizite UI-Aktion des Nutzers — kein Automatik-Send.
3. **Nur HTTPS-Link ohne One-Click** → die API liefert die URL zurück, die UI
   zeigt „Im Browser öffnen" (target=_blank). Wir POSTen nie blind auf
   unbekannte Abmeldeseiten.

Erfolgte Abmeldungen landen in `data/subscriptions.json`
({addr: {unsubscribed_at, method}}) und werden in der Liste als „abgemeldet"
ausgegraut — inklusive Schutz vor Doppel-Abmeldung.

**UI:** Sidebar-Ansicht **„Abos"**: sortiert nach Frequenz, Knopf „Abmelden"
mit Zweitklick-Bestätigung (die Aktion geht nach außen!).

## 2. Screener (HEY-Learning)

**Konzept:** Erstkontakt-Absender (erste Mail jünger als 30 Tage, nie von mir
angeschrieben, keine Entscheidung) erscheinen in der Ansicht **„Screener"**
mit lokalem Vorschlag. Entscheidungen (`data/screener.json`):

- **Zulassen** → Absender ist bekannt, taucht nie wieder auf.
- **Ablehnen** → künftige Mails dieses Absenders verschiebt der Live-Watcher
  automatisch in den Ordner **„Aussortiert"** (niemals Papierkorb, nichts
  wird gelöscht; der Ordner ist normal einsehbar). Das ist eine explizit vom
  Nutzer erlassene REGEL — keine KI-Entscheidung (Sicherheitsmodell intakt).
  Benachrichtigungen für Aussortiertes werden unterdrückt.

**„Nie von mir angeschrieben":** Der Index bekommt ein `is_sent`-Flag pro
Zeile (aus `is_sent_folder`, beim Indexieren); „bekannt" = die Adresse taucht
in den Empfängern irgendeiner Gesendet-Mail auf (Token-Match).

**Lokaler Vorschlag (Heuristik, kein LLM-Call):** „eher ablehnen" bei
Unsubscribe-Header oder noreply-artiger Adresse (geteilte Regex-Basis),
sonst „eher zulassen" — mit Ein-Satz-Begründung. Ehrlich regelbasiert.

## API (v0.8) — Kurzform

| Route | Zweck |
|---|---|
| `GET /api/subscriptions?account=` | Abo-Liste (inkl. Abmelde-Methode) |
| `POST /api/subscriptions/unsubscribe` | `{account, addr}` → führt One-Click/mailto aus, sonst `{link}` |
| `GET /api/screener?account=` | Pending-Erstkontakte mit Vorschlag |
| `POST /api/screener/decide` | `{account, addr, decision: "allow"\|"block"}` |

## Nicht in diesem Batch

Bestehende Mails beim Ablehnen rückwirkend wegräumen (die Suche `von:addr`
+ Bulk kann das schon), Screener-Zustellung in eine eigene Prüf-Inbox
(HEY-Vollmodell), Abmelde-Erfolgskontrolle (kommt keine Mail mehr = Erfolg).
