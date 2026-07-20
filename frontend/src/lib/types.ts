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
}

export type Classification = {
  category: string
  is_newsletter: boolean
  interesting: boolean
  needs_reply: boolean
  reason: string
}

export type MessageAction = {
  action: 'archive' | 'trash' | 'read' | 'unread' | 'label'
  label?: string
  folder: string
}

export type SendRequest = {
  account: string
  to: string[]
  cc: string[]
  subject: string
  body: string
  reply_to_uid?: number
  folder?: string
}

/** Referenz auf eine konkrete Nachricht (Konto + Ordner + UID). */
export type MsgRef = { account: string; folder: string; uid: number }

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

export type EmiliaImproveMode = 'korrigieren' | 'verbessern'
