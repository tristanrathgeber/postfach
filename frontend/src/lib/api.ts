// Typisierter API-Client — exakt gegen docs/api-contract.md (v0.1: 10 Endpunkte,
// Nachtrag v0.2: 4 Emilia-Endpunkte, Nachtrag v0.3: Settings/Kontakte/Entwürfe/
// Snippets + multipart-Send). Fehlerform: {"detail": "<Meldung>"} mit Status
// 4xx/5xx; Konto nicht erreichbar → 502.

import type {
  OutboxEntry,
  Reminder,
  MsgRef,
  ScreenerEntry,
  Subscription,
  UnsubscribeResult,
  ThreadMail,
  Account,
  Classification,
  Contact,
  Detail,
  Draft,
  DraftUpsert,
  EmiliaChatRequest,
  EmiliaChatResponse,
  EmiliaImproveMode,
  EmiliaStatus,
  MessageAction,
  SendRequest,
  SendResponse,
  Settings,
  Snippet,
  Summary,
  BatchAction,
  AccountStatus,
} from './types'

const BASE = '/api'

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

/** Fehlertext für die UI: ApiError → detail, alles andere → generische Meldung. */
export function errText(e: unknown): string {
  return e instanceof ApiError ? e.detail : 'Unbekannter Fehler'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, init)
  } catch {
    throw new ApiError(0, 'Backend nicht erreichbar')
  }
  if (!res.ok) {
    let detail = `Fehler ${res.status}`
    try {
      const data: unknown = await res.json()
      if (
        typeof data === 'object' &&
        data !== null &&
        'detail' in data &&
        typeof (data as { detail: unknown }).detail === 'string'
      ) {
        detail = (data as { detail: string }).detail
      }
    } catch {
      // Body war kein JSON — generische Meldung behalten.
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

const enc = encodeURIComponent

export const api = {
  /** GET /api/accounts */
  accounts: (): Promise<Account[]> => request('/accounts'),

  /** GET /api/folders?account= */
  folders: (account: string): Promise<string[]> => request(`/folders?account=${enc(account)}`),

  /** GET /api/messages?account=&folder=INBOX&limit=50 — neueste zuerst */
  messages: (account: string, folder = 'INBOX', limit = 50): Promise<Summary[]> =>
    request(`/messages?account=${enc(account)}&folder=${enc(folder)}&limit=${limit}`),

  /** GET /api/messages/{account}/{uid}?folder=INBOX */
  message: (account: string, uid: number, folder = 'INBOX'): Promise<Detail> =>
    request(`/messages/${enc(account)}/${uid}?folder=${enc(folder)}`),

  /** GET /api/messages/{account}/{uid}/attachments/{index}?folder=INBOX — Binärstream (nur URL, kein fetch) */
  attachmentUrl: (account: string, uid: number, index: number, folder = 'INBOX'): string =>
    `${BASE}/messages/${enc(account)}/${uid}/attachments/${index}?folder=${enc(folder)}`,

  /** POST /api/messages/{account}/{uid}/action */
  action: (account: string, uid: number, body: MessageAction): Promise<{ ok: true }> =>
    post(`/messages/${enc(account)}/${uid}/action`, body),

  /** POST /api/classify — Antwort: {"<uid>": Classification, …} */
  classify: (body: { account: string; folder: string; uids: number[] }): Promise<Record<string, Classification>> =>
    post('/classify', body),

  /** POST /api/draft */
  draft: (body: { account: string; folder: string; uid: number }): Promise<{ text: string }> => post('/draft', body),

  /** POST /api/send — JSON-Variante (ohne hochgeladene Anhänge) */
  send: (body: SendRequest): Promise<SendResponse> => post('/send', body),

  /**
   * POST /api/send — multipart/form-data: Feld "payload" (JSON als String) +
   * "files"-Einträge (gesamt ≤ 25 MB → 413). Kein Content-Type-Header setzen,
   * der Browser ergänzt die multipart-Boundary selbst.
   */
  sendWithAttachments: (payload: SendRequest, files: File[]): Promise<SendResponse> => {
    const form = new FormData()
    form.append('payload', JSON.stringify(payload))
    for (const file of files) form.append('files', file, file.name)
    return request('/send', { method: 'POST', body: form })
  },

  /** GET /api/search?account=&q=&folder=INBOX */
  search: (account: string, q: string, folder = 'INBOX'): Promise<Summary[]> =>
    request(`/search?account=${enc(account)}&q=${enc(q)}&folder=${enc(folder)}`),

  // --- Emilia (Nachtrag v0.2) ---

  /** POST /api/emilia/chat — Antwort deutsch, sources = tatsächlich verwendete Gedächtnis-Treffer */
  emiliaChat: (body: EmiliaChatRequest): Promise<EmiliaChatResponse> => post('/emilia/chat', body),

  /** POST /api/emilia/improve — gibt NUR den überarbeiteten Text zurück */
  emiliaImprove: (body: { text: string; mode: EmiliaImproveMode }): Promise<{ text: string }> =>
    post('/emilia/improve', body),

  /** POST /api/emilia/index — idempotent, aktualisiert den Bestand */
  emiliaIndex: (body: { account: string }): Promise<{ indexed: number }> => post('/emilia/index', body),

  /** GET /api/emilia/status */
  emiliaStatus: (): Promise<EmiliaStatus> => request('/emilia/status'),

  // --- Batch 1 „Schreiben komplett" (Nachtrag v0.3) ---

  /** GET /api/settings */
  settings: (): Promise<Settings> => request('/settings'),

  /** POST /api/batch-action — {ok, done}; Teilfehler kommen als 502 mit Klartext. */
  batchAction: (body: { account: string; folder: string; uids: number[]; action: BatchAction }): Promise<{ ok: true; done: number }> =>
    post('/batch-action', body),

  /** POST /api/classify/override — Nutzer-Korrektur, schlägt die KI dauerhaft. */
  classifyOverride: (body: { account: string; folder: string; uid: number; category: string }): Promise<{ ok: true }> =>
    post('/classify/override', body),

  /** GET /api/status — Watcher-Verbindungsstatus je Konto. */
  status: (): Promise<{ accounts: Record<string, AccountStatus> }> => request('/status'),

  /** GET /api/messages/{account}/{uid}/thread — Gesprächsfaden, kontoweit, chronologisch. */
  thread: (account: string, uid: number, folder: string): Promise<ThreadMail[]> =>
    request(`/messages/${enc(account)}/${uid}/thread?folder=${enc(folder)}`),

  /** GET /api/outbox — geplante Sends (Undo-Fenster + Später senden). */
  outbox: (account: string): Promise<OutboxEntry[]> => request(`/outbox?account=${enc(account)}`),

  /** DELETE /api/outbox/{id} — Storno; der Auto-Save-Entwurf bleibt erhalten. */
  cancelOutbox: (id: string): Promise<{ ok: true }> => request(`/outbox/${enc(id)}`, { method: 'DELETE' }),

  /** POST .../snooze — Mail bis <until> in den Ordner „Später". */
  snooze: (ref: MsgRef, until: string): Promise<{ ok: true; id: string }> =>
    post(`/messages/${enc(ref.account)}/${ref.uid}/snooze`, { folder: ref.folder, until }),

  /** GET /api/reminders — Wiedervorlagen (Snooze + Follow-ups). */
  reminders: (account: string): Promise<Reminder[]> => request(`/reminders?account=${enc(account)}`),

  /** POST /api/reminders/{id}/done */
  reminderDone: (id: string): Promise<{ ok: true }> => post(`/reminders/${enc(id)}/done`, {}),

  /** GET /api/search/status — 0 = schnelle Suche noch nicht aufgebaut. */
  searchStatus: (account: string): Promise<{ indexed: number; ready: boolean }> =>
    request(`/search/status?account=${enc(account)}`),

  /** GET /api/categories — alle konfigurierten Kategorien. */
  categories: (): Promise<string[]> => request('/categories'),

  /** PUT /api/settings */
  putSettings: (body: Settings): Promise<{ ok: true }> => put('/settings', body),

  /** GET /api/contacts?q=&limit=8 — Ranking: Häufigkeit×Aktualität, Sent-Empfänger doppelt */
  contacts: (q: string, limit = 8): Promise<Contact[]> => request(`/contacts?q=${enc(q)}&limit=${limit}`),

  /** GET /api/drafts?account= */
  drafts: (account: string): Promise<Draft[]> => request(`/drafts?account=${enc(account)}`),

  /** POST /api/drafts — mit id = Upsert (Auto-Save) */
  saveDraft: (body: DraftUpsert): Promise<{ id: string }> => post('/drafts', body),

  /** DELETE /api/drafts/{id} — betrifft nur das lokale Artefakt */
  deleteDraft: (id: string): Promise<{ ok: true }> => request(`/drafts/${enc(id)}`, { method: 'DELETE' }),

  /** GET /api/snippets */
  snippets: (): Promise<Snippet[]> => request('/snippets'),

  /** PUT /api/snippets */
  putSnippets: (items: Snippet[]): Promise<{ ok: true }> => put('/snippets', items),

  // --- Posteingangs-Hygiene (Nachtrag v0.8) ---

  /** GET /api/subscriptions?account= — Abo-Liste, nach Frequenz sortiert. */
  subscriptions: (account: string): Promise<Subscription[]> =>
    request(`/subscriptions?account=${enc(account)}`),

  /** POST /api/subscriptions/unsubscribe — One-Click/mailto serverseitig, sonst Link. */
  unsubscribe: (body: { account: string; addr: string }): Promise<UnsubscribeResult> =>
    post('/subscriptions/unsubscribe', body),

  /** GET /api/screener?account= — Erstkontakte ohne Entscheidung. */
  screener: (account: string): Promise<ScreenerEntry[]> => request(`/screener?account=${enc(account)}`),

  /** POST /api/screener/decide — allow/block; block = Nutzer-Regel für den Watcher. */
  screenerDecide: (body: { account: string; addr: string; decision: 'allow' | 'block' }): Promise<{ ok: true }> =>
    post('/screener/decide', body),
}
