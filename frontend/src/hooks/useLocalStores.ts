import { useQuery } from '@tanstack/react-query'
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
