import { useQueries, useQuery, type QueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../lib/api'
import type { Draft, Summary } from '../lib/types'

/** Cache-Form der Suche seit v0.9: Treffer + ggf. die von Emilia übersetzte Query. */
export type SearchCacheEntry = { query: string | null; hits: Summary[] }

/**
 * Zeilen-Patches auf den Such-Cache — ALLE optimistischen Updates müssen über
 * diesen Helfer laufen, weil der Cache {query, hits} trägt und nicht Summary[].
 */
export function patchSearchData(
  qc: QueryClient,
  rowFn: (rows: Summary[] | undefined) => Summary[] | undefined,
): void {
  qc.setQueriesData<SearchCacheEntry>({ queryKey: ['search'] }, (old) => {
    if (!old) return old
    const hits = rowFn(old.hits)
    return hits ? { ...old, hits } : old
  })
}

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

/**
 * Entwürfe (Nachtrag v0.3): der Vertrag liefert Entwürfe pro Konto
 * (GET /api/drafts?account=) — "Alle Konten" holt je Konto und merged,
 * neueste Änderung zuerst. Query-Keys je Konto stabil: ["drafts", account].
 */
export function useDraftsAggregate(accountNames: string[]): { drafts: Draft[]; isLoading: boolean } {
  return useQueries({
    queries: accountNames.map((name) => ({
      queryKey: ['drafts', name],
      queryFn: () => api.drafts(name),
      // Lokaler Store: Auto-Save/Löschen invalidieren explizit — kein Polling nötig.
      staleTime: Infinity,
      refetchInterval: false as const,
      refetchOnWindowFocus: false,
    })),
    combine: (results) => ({
      drafts: results
        .flatMap((r) => r.data ?? [])
        .sort((a, b) => new Date(b.updated).getTime() - new Date(a.updated).getTime()),
      isLoading: results.some((r) => r.isLoading),
    }),
  })
}

/**
 * Suche über ein oder mehrere Konten (GET /api/search je Konto, gemergt);
 * inaktiv bei leerem q. Beginnt die Eingabe mit `?`, übersetzt Emilia die
 * natürliche Frage in Operatoren (GET /api/search/nl) — `nlQuery` trägt die
 * übersetzte Query für die transparente Anzeige in der UI.
 */
export function useSearchAggregate(
  accountNames: string[],
  q: string,
  folder: string,
): AggregateResult & { nlQuery: string | null; failureDetail: string | null } {
  const isNl = q.trim().startsWith('?')
  const nlQ = q.trim().slice(1).trim()
  const active = (isNl ? nlQ : q.trim()).length > 0
  return useQueries({
    queries: accountNames.map((name) => ({
      queryKey: ['search', name, q, folder],
      queryFn: async () => {
        if (!isNl) return { query: null as string | null, hits: await api.search(name, q, folder) }
        const result = await api.searchNl(name, nlQ)
        return { query: result.query as string | null, hits: result.hits }
      },
      enabled: active,
      // NL-Suche kostet einen LLM-Aufruf pro Refetch — nicht alle 3 Minuten
      // und nicht bei jedem Fokuswechsel neu übersetzen.
      staleTime: isNl ? 5 * 60_000 : 30_000,
      refetchInterval: isNl ? (false as const) : undefined,
      refetchOnWindowFocus: isNl ? false : undefined,
    })),
    combine: (results) => ({
      ...combineAccounts(
        accountNames,
        results.map((r) => ({ ...r, data: r.data?.hits })),
      ),
      nlQuery: results.map((r) => r.data?.query).find((query) => query != null) ?? null,
      // 403 (KI aus)/409 (Index fehlt) sollen als KLARTEXT im Banner stehen,
      // nicht als irreführendes „Konto nicht erreichbar".
      failureDetail:
        results
          .map((r) => (r.error instanceof ApiError ? r.error.detail : null))
          .find((detail) => detail != null) ?? null,
    }),
  })
}
