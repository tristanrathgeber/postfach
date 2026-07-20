// Typisierter API-Client — exakt gegen docs/api-contract.md (v0.1: 10 Endpunkte,
// Nachtrag v0.2: 4 Emilia-Endpunkte). Fehlerform: {"detail": "<Meldung>"} mit
// Status 4xx/5xx; Konto nicht erreichbar → 502.

import type {
  Account,
  Classification,
  Detail,
  EmiliaChatRequest,
  EmiliaChatResponse,
  EmiliaImproveMode,
  EmiliaStatus,
  MessageAction,
  SendRequest,
  Summary,
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

  /** POST /api/send */
  send: (body: SendRequest): Promise<{ ok: true }> => post('/send', body),

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
}
