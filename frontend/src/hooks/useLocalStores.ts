import { useQueries, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

// Lokale Store-Daten (Signaturen, Snippets): Mutationen invalidieren explizit —
// das globale 3-Minuten-Polling und der Fokus-Refetch wären reine Verschwendung.
const LOCAL_STORE_OPTS = {
  staleTime: Infinity,
  refetchInterval: false as const,
  refetchOnWindowFocus: false,
}

export function useSettings() {
  return useQuery({ queryKey: ['settings'], queryFn: api.settings, ...LOCAL_STORE_OPTS })
}

export function useSnippets() {
  return useQuery({ queryKey: ['snippets'], queryFn: api.snippets, ...LOCAL_STORE_OPTS })
}

/** true, wenn ALLE Konten einen vollen Such-Index haben (Banner „ganzes Konto"). */
export function useSearchReady(accountNames: string[], enabled: boolean): boolean {
  return useQueries({
    queries: accountNames.map((name) => ({
      queryKey: ['search-status', name],
      queryFn: () => api.searchStatus(name),
      enabled,
      staleTime: 60_000,
    })),
    combine: (results) => enabled && results.length > 0 && results.every((r) => r.data?.ready === true),
  })
}

/** Geplante Sends aller Konten — der Scheduler räumt sie selbst ab (60-s-Poll). */
export function useOutboxAggregate(accountNames: string[]) {
  return useQueries({
    queries: accountNames.map((name) => ({
      queryKey: ['outbox', name],
      queryFn: () => api.outbox(name),
      refetchInterval: 60_000,
    })),
    combine: (results) => ({
      entries: results.flatMap((r) => r.data ?? []).sort((a, b) => a.due.localeCompare(b.due)),
    }),
  })
}

/** Wiedervorlagen (Snooze + Follow-ups) aller Konten. */
export function useRemindersAggregate(accountNames: string[]) {
  return useQueries({
    queries: accountNames.map((name) => ({
      queryKey: ['reminders', name],
      queryFn: () => api.reminders(name),
      refetchInterval: 60_000,
    })),
    combine: (results) => {
      const entries = results.flatMap((r) => r.data ?? []).sort((a, b) => a.due.localeCompare(b.due))
      return { entries, dueCount: entries.filter((e) => e.kind === 'followup_due').length }
    },
  })
}
