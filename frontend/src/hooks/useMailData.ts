import { useQueries, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Summary } from '../lib/types'

/** Pseudo-Konto "Alle Konten": aggregiert client-seitig über alle echten Konten. */
export const ALL_ACCOUNTS = '__alle_konten__'

export const MESSAGE_LIMIT = 50

export type AggregateResult = {
  messages: Summary[]
  /** Namen der Konten, deren Abruf fehlgeschlagen ist. */
  failures: string[]
  isLoading: boolean
}

export function useAccounts() {
  return useQuery({ queryKey: ['accounts'], queryFn: api.accounts, staleTime: 5 * 60_000 })
}

export function useFolders(account: string | null) {
  return useQuery({
    queryKey: ['folders', account],
    queryFn: () => api.folders(account ?? ''),
    enabled: account !== null,
    staleTime: 5 * 60_000,
  })
}

function byDateDesc(a: Summary, b: Summary): number {
  return new Date(b.date).getTime() - new Date(a.date).getTime()
}

type QueryResultLike = {
  data: Summary[] | undefined
  isError: boolean
  isLoading: boolean
}

function combineAccounts(accountNames: string[], results: QueryResultLike[]): AggregateResult {
  // Aggregat-Ansicht toleriert Teilausfälle: erreichbare Konten liefern weiter,
  // ausgefallene landen als Banner-Eintrag in `failures` (entspricht Promise.allSettled).
  const messages: Summary[] = []
  const failures: string[] = []
  results.forEach((r, i) => {
    if (r.data) messages.push(...r.data)
    if (r.isError) failures.push(accountNames[i] ?? '?')
  })
  messages.sort(byDateDesc)
  return {
    messages,
    failures,
    isLoading: results.some((r) => r.isLoading),
  }
}

/**
 * Nachrichten für ein oder mehrere Konten ("Alle Konten" → ein Query je Konto,
 * client-seitig gemergt und nach Datum sortiert). Query-Keys bleiben je Konto
 * stabil: ["messages", account, folder].
 */
export function useMessagesAggregate(accountNames: string[], folder: string): AggregateResult {
  return useQueries({
    queries: accountNames.map((name) => ({
      queryKey: ['messages', name, folder],
      queryFn: () => api.messages(name, folder, MESSAGE_LIMIT),
    })),
    combine: (results) => combineAccounts(accountNames, results),
  })
}

/** Suche über ein oder mehrere Konten (GET /api/search je Konto, gemergt); inaktiv bei leerem q. */
export function useSearchAggregate(accountNames: string[], q: string, folder: string): AggregateResult {
  const active = q.trim().length > 0
  return useQueries({
    queries: accountNames.map((name) => ({
      queryKey: ['search', name, q, folder],
      queryFn: () => api.search(name, q, folder),
      enabled: active,
      staleTime: 30_000,
    })),
    combine: (results) => combineAccounts(accountNames, results),
  })
}
