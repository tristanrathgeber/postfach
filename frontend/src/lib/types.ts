// Typen exakt nach docs/api-contract.md (v0.1, eingefroren).

export type Account = { name: string; address: string; provider: 'imap' | 'gmail' }

export type Summary = {
  account: string
  folder: string
  uid: number
  subject: string
  from_name: string
  from_addr: string
  date: string // ISO 8601, z. B. "2026-07-19T10:23:00+02:00"
  snippet: string // erste ~120 Zeichen Klartext
  seen: boolean
  has_attachments: boolean
  category: string | null // z. B. "Newsletter", "Rechnungen" … oder null = unklassifiziert
  /** Mails im Gesprächsfaden (1 = Einzelmail; ohne vollen Index immer 1). */
  thread_count: number
}

export type Attachment = {
  index: number
  filename: string
  content_type: string
  size: number
}

export type Detail = Summary & {
  to: string[]
  cc: string[]
  reply_to: string | null
  message_id: string
  body_text: string
  body_html: string | null // sanitisiert, Remote-Bilder BLOCKIERT (src entfernt, data-blocked-src gesetzt)
  body_html_images: string | null // sanitisiert, Remote-Bilder erlaubt (für "Bilder laden")
  attachments: Attachment[]
  invite: Invite | null // ICS-Einladung (nur METHOD:REQUEST)
  entities: Entity[] // lokal extrahierte Chips (Termine, Beträge, Sendungen)
}

// --- Batch 8: Kalender & Struktur (Nachtrag v0.10) ---

/** ICS-Einladung (Kalender-RSVP). start/end ISO-8601 oder JJJJ-MM-TT (all_day). */
export type Invite = {
  summary: string
  start: string
  end: string
  all_day: boolean
  location: string
  organizer_name: string
  organizer_email: string
  method: string
  uid: string
}

export type InviteResponse = 'accepted' | 'tentative' | 'declined'

/** Lokal extrahierter Chip. url nur bei Sendungsnummern (Anbieter-Tracking). */
export type Entity = {
  kind: 'date' | 'amount' | 'tracking'
  text: string
  value: string
  url?: string
}

export type Classification = {
  category: string
  is_newsletter: boolean
  interesting: boolean
  needs_reply: boolean
  reason: string
}

export type MessageAction = {
  action: 'archive' | 'trash' | 'read' | 'unread' | 'label' | 'spam' | 'unspam'
  label?: string
  folder: string
}

/** Weiterleitung: Server hängt die Original-Anhänge serverseitig an (kein Re-Upload). */
export type ForwardOf = { folder: string; uid: number; include_attachments: boolean }

export type SendRequest = {
  account: string
  to: string[]
  cc: string[]
  bcc: string[]
  subject: string
  body: string
  reply_to_uid?: number
  folder?: string
  forward_of?: ForwardOf
  /** Serverseitig nach erfolgreichem Versand löschen (atomar gegen späte Auto-Saves). */
  draft_id?: string
  /** Später senden (ISO) — überstimmt das Undo-Fenster. */
  send_at?: string
  /** Erinnern, falls bis dahin keine fremde Antwort im Faden auftaucht. */
  followup_days?: number
}

/** POST /api/send — warning: SMTP ok, aber Gesendet-Ablage fehlgeschlagen (NICHT erneut senden).
    scheduled: Versand wartet in der lokalen Warteschlange (Undo-Fenster oder Später senden). */
export type SendResponse = {
  ok: true
  warning?: string
  scheduled?: { id: string; due: string; kind: 'undo' | 'later' }
}

/** GET /api/outbox — geplante Sends. */
export type OutboxEntry = { id: string; account: string; to: string[]; subject: string; due: string; kind: 'undo' | 'later' | 'failed' }

/** GET /api/reminders — Wiedervorlagen (Snooze + Follow-up). */
export type Reminder = { id: string; kind: 'snooze' | 'followup' | 'followup_due' | 'snooze_failed'; subject: string; due: string; info: string }

/** Referenz auf eine konkrete Nachricht (Konto + Ordner + UID). */
export type MsgRef = { account: string; folder: string; uid: number }

// --- Posteingangs-Hygiene (Nachtrag v0.8) ---

/** GET /api/subscriptions — ein Abo-Absender, nach Frequenz sortiert. */
export type Subscription = {
  addr: string
  name: string
  count: number
  first_date: string
  last_date: string
  per_month: number
  method: 'oneclick' | 'mailto' | 'link' | 'none'
  unsubscribed_at: string | null
}

/** POST /api/subscriptions/unsubscribe — ok:false + link ⇒ UI öffnet im Browser. */
export type UnsubscribeResult =
  | { ok: true; method: 'oneclick' | 'mailto' }
  | { ok: false; method: 'link'; link: string }

/** GET /api/screener — Erstkontakt ohne Entscheidung, mit regelbasiertem Vorschlag. */
export type ScreenerEntry = {
  addr: string
  name: string
  count: number
  first_date: string
  last_date: string
  has_unsubscribe: boolean
  subject: string
  snippet: string
  folder: string
  uid: number
  suggestion: 'allow' | 'block'
  reason: string
}

// --- Emilia (Nachtrag v0.2, eingefroren 2026-07-20) ---

/** GET /api/emilia/status */
export type EmiliaStatus = {
  model: string
  embed_model: string
  indexed_mails: number
  sort_local: boolean
}

/** Gedächtnis-Treffer, den Emilia für eine Antwort tatsächlich verwendet hat. */
export type EmiliaSource = {
  account: string
  folder: string
  uid: number
  subject: string
  from_name: string
  date: string // ISO 8601
}

/** POST /api/emilia/chat — folder/uid geben der Frage den Kontext der geöffneten Mail. */
export type EmiliaChatRequest = {
  account: string
  message: string
  folder?: string
  uid?: number
}

export type EmiliaChatResponse = { reply: string; sources: EmiliaSource[] }

export type EmiliaImproveMode = 'korrigieren' | 'verbessern' | 'sie' | 'du' | 'kuerzer'

// --- Batch 1 „Schreiben komplett" (Nachtrag v0.3, eingefroren 2026-07-21) ---

/** GET/PUT /api/settings — Signaturen pro Konto (Plain-Text). */
export type Settings = {
  signatures: Record<string, string>
  /** Benachrichtigungen pro Konto; fehlender Eintrag = an. */
  notifications: Record<string, boolean>
  /** Undo-Fenster in Sekunden (0 = sofort senden). */
  undo_seconds: number
  /** Globaler KI-Schalter — aus heißt aus (Classify/Draft/Emilia/NL-Suche). */
  ai_enabled: boolean
}

// --- Emilia II (Nachtrag v0.9) ---

/** NDJSON-Ereignis aus POST /api/emilia/chat/stream. */
export type EmiliaStreamEvent = {
  sources?: EmiliaSource[]
  delta?: string
  done?: true
  error?: string
}

/** GET /api/search/nl — übersetzte Query + normale Suchtreffer. */
export type NlSearchResult = { query: string; hits: Summary[] }

/** POST /api/emilia/thread_summary */
export type ThreadSummary = { summary: string; mails: number }

/** GET .../thread — Faden-Mail: Summary + Server-Wissen über Gesendet-Kopien. */
export type ThreadMail = Summary & { is_sent: boolean }

/** POST /api/batch-action — Bulk-Triage über EINE Verbindung, kein send. */
export type BatchAction = 'read' | 'unread' | 'archive' | 'trash' | 'spam' | 'unspam'

/** GET /api/status — Verbindungszustand der IMAP-IDLE-Watcher. */
export type AccountStatus = { connected: boolean; since: string | null; last_error: string | null }

/** GET /api/contacts?q=&limit=8 — Ranking: Häufigkeit×Aktualität, Sent-Empfänger doppelt. */
export type Contact = { name: string; addr: string }

export type DraftMode = 'new' | 'reply' | 'forward'

/** Lokaler Entwurf (data/drafts.json) — Auto-Save-Upsert über stabile id. */
export type Draft = {
  id: string
  account: string
  to: string[]
  cc: string[]
  bcc: string[]
  subject: string
  body: string
  mode: DraftMode
  ref_folder?: string
  ref_uid?: number
  /** Weiterleitung: Original-Anhänge mitsenden (Checkbox-Zustand überlebt Resume). */
  include_attachments?: boolean
  updated: string // ISO 8601, server-seitig gesetzt
}

/** POST /api/drafts — id optional; mit id = Upsert (Auto-Save), updated setzt der Server. */
export type DraftUpsert = Omit<Draft, 'id' | 'updated'> & { id?: string }

/** GET/PUT /api/snippets — Textbausteine, Auslösung ;kürzel+Tab bzw. ⌘K. */
export type Snippet = { abbrev: string; title: string; text: string }
