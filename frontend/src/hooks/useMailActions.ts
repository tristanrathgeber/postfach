import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import { msgKey, sameMsg } from '../lib/format'
import { useToast } from '../components/Toast'
import type { BatchAction, Classification, Detail, MsgRef, Summary } from '../lib/types'

const MOVE_VERB: Record<string, string> = {
  archive: 'Archivieren',
  trash: 'Löschen',
  spam: 'Spam-Markieren',
  unspam: 'Zurückholen',
}

/** Nach Konto+Ordner gruppieren — die Batch-/Classify-Endpunkte arbeiten pro Konto. */
function groupByFolder(targets: readonly MsgRef[]): { account: string; folder: string; uids: number[] }[] {
  const groups = new Map<string, { account: string; folder: string; uids: number[] }>()
  for (const m of targets) {
    const key = `${m.account}\0${m.folder}`
    const g = groups.get(key) ?? { account: m.account, folder: m.folder, uids: [] }
    g.uids.push(m.uid)
    groups.set(key, g)
  }
  return [...groups.values()]
}

/**
 * Fehlerfall einer optimistischen Mutation: KEIN Snapshot-Rollback — der würde
 * auch die Effekte parallel erfolgreicher Mutationen zurückdrehen (z. B. eine
 * bereits archivierte Zeile dauerhaft wiederbeleben). Stattdessen die
 * Server-Wahrheit aktiv nachladen (aktive Queries refetchen sofort).
 */
function resyncAfterError(qc: QueryClient, ref: MsgRef) {
  void qc.invalidateQueries({ queryKey: ['messages', ref.account, ref.folder] })
  void qc.invalidateQueries({ queryKey: ['search', ref.account] })
  void qc.invalidateQueries({ queryKey: ['message', ref.account, ref.folder, ref.uid] })
}

/** Patch auf eine Nachricht in allen Listen-Caches (messages + search) und im Detail-Cache. */
function patchMessage(qc: QueryClient, ref: MsgRef, patch: Partial<Summary>) {
  const patchList = (old: Summary[] | undefined) => old?.map((m) => (sameMsg(m, ref) ? { ...m, ...patch } : m))
  qc.setQueriesData<Summary[]>({ queryKey: ['messages'] }, patchList)
  qc.setQueriesData<Summary[]>({ queryKey: ['search'] }, patchList)
  qc.setQueryData<Detail>(['message', ref.account, ref.folder, ref.uid], (old) => (old ? { ...old, ...patch } : old))
}

/**
 * Mail-Aktionen mit optimistischen Updates:
 * - setSeen: gelesen/ungelesen sofort im Cache, Toast + Server-Resync bei Fehler
 * - bulk: archive/trash/spam/unspam/read/unread für 1..n Mails über
 *   POST /api/batch-action (Einzelaktionen sind der 1-Element-Spezialfall)
 * - overrideCategory: Nutzer-Korrektur, Caches werden gepatcht (kein Refetch)
 * - classify: POST /api/classify je Konto/Ordner-Gruppe, Ergebnis in Caches gemergt
 */
export function useMailActions() {
  const qc = useQueryClient()
  const { showToast } = useToast()

  const setSeen = useMutation({
    mutationFn: ({ ref, seen }: { ref: MsgRef; seen: boolean }) =>
      api.action(ref.account, ref.uid, { action: seen ? 'read' : 'unread', folder: ref.folder }),
    onMutate: async ({ ref, seen }) => {
      await qc.cancelQueries({ queryKey: ['messages', ref.account, ref.folder] })
      await qc.cancelQueries({ queryKey: ['search', ref.account] })
      patchMessage(qc, ref, { seen })
    },
    onError: (e, { ref }) => {
      showToast(`Aktion fehlgeschlagen: ${errText(e)}`, 'error')
      resyncAfterError(qc, ref)
    },
    onSuccess: (_data, { ref, seen }) => {
      // Erneut patchen: der parallele Detail-GET kann nach dem optimistischen
      // Patch mit altem seen-Wert aufgelöst worden sein (Race beim Öffnen).
      patchMessage(qc, ref, { seen })
    },
  })

  const bulk = useMutation({
    mutationFn: async ({ targets, action }: { targets: MsgRef[]; action: BatchAction }) => {
      const settled = await Promise.allSettled(
        groupByFolder(targets).map((g) => api.batchAction({ ...g, action })),
      )
      return { failed: settled.filter((s) => s.status === 'rejected').length }
    },
    onMutate: async ({ targets, action }) => {
      // Laufende Refetches abbrechen — eine in-flight Antwort mit altem Stand
      // würde die optimistisch entfernten Zeilen wiederbeleben.
      for (const g of groupByFolder(targets)) {
        await qc.cancelQueries({ queryKey: ['messages', g.account, g.folder] })
        await qc.cancelQueries({ queryKey: ['search', g.account] })
      }
      const keys = new Set(targets.map(msgKey))
      const hit = (m: Summary) => keys.has(msgKey(m))
      if (action === 'read' || action === 'unread') {
        const patchRows = (old: Summary[] | undefined) =>
          old?.map((m) => (hit(m) ? { ...m, seen: action === 'read' } : m))
        qc.setQueriesData<Summary[]>({ queryKey: ['messages'] }, patchRows)
        qc.setQueriesData<Summary[]>({ queryKey: ['search'] }, patchRows)
      } else {
        const removeRows = (old: Summary[] | undefined) => old?.filter((m) => !hit(m))
        qc.setQueriesData<Summary[]>({ queryKey: ['messages'] }, removeRows)
        qc.setQueriesData<Summary[]>({ queryKey: ['search'] }, removeRows)
      }
    },
    onSuccess: ({ failed }, { targets, action }) => {
      for (const g of groupByFolder(targets)) {
        void qc.invalidateQueries({ queryKey: ['messages', g.account, g.folder], refetchType: 'none' })
        void qc.invalidateQueries({ queryKey: ['search', g.account], refetchType: 'none' })
        // „Kein Spam" verschiebt IN die Inbox — deren Cache aktiv nachladen,
        // sonst fehlt die Mail dort bis zum nächsten Poll.
        if (action === 'unspam') void qc.invalidateQueries({ queryKey: ['messages', g.account, 'INBOX'] })
      }
      if (failed > 0) {
        showToast('Aktion für einige Konten fehlgeschlagen.', 'error')
        for (const m of targets) resyncAfterError(qc, m)
      } else if (targets.length > 1 && action !== 'read' && action !== 'unread') {
        showToast(`${targets.length} Nachrichten · ${MOVE_VERB[action]}`)
      }
    },
    onError: (e, { targets, action }) => {
      showToast(`${MOVE_VERB[action] ?? 'Aktion'} fehlgeschlagen: ${errText(e)}`, 'error')
      for (const m of targets) resyncAfterError(qc, m)
    },
  })

  const overrideCategory = useMutation({
    mutationFn: ({ ref, category }: { ref: MsgRef; category: string }) =>
      api.classifyOverride({ account: ref.account, folder: ref.folder, uid: ref.uid, category }),
    onMutate: ({ ref, category }) => {
      // Der neue Wert ist clientseitig bekannt — patchen statt IMAP-Refetch.
      patchMessage(qc, ref, { category })
    },
    onSuccess: (_d, { category }) => showToast(`Kategorie geändert: ${category}`),
    onError: (e, { ref }) => {
      showToast(`Kategorie nicht änderbar: ${errText(e)}`, 'error')
      resyncAfterError(qc, ref)
    },
  })

  const classify = useMutation({
    mutationFn: async (targets: Summary[]) => {
      // Teilausfälle tolerieren: erfolgreiche Konten werden trotzdem gemergt.
      return Promise.allSettled(
        groupByFolder(targets).map(async (g) => ({
          group: g,
          result: await api.classify({ account: g.account, folder: g.folder, uids: g.uids }),
        })),
      )
    },
    onSuccess: (settled) => {
      let failures = 0
      for (const s of settled) {
        if (s.status === 'rejected') {
          failures++
          continue
        }
        const { group, result } = s.value
        mergeClassifications(qc, group.account, group.folder, result)
      }
      // Auch der Komplettausfall läuft hier durch: allSettled lehnt nie ab,
      // alle Gruppen landen dann als rejected im failures-Zähler.
      if (failures > 0) showToast('Sortieren für einige Konten fehlgeschlagen.', 'error')
    },
  })

  return { setSeen, bulk, overrideCategory, classify }
}

function mergeClassifications(qc: QueryClient, account: string, folder: string, result: Record<string, Classification>) {
  for (const [uidStr, c] of Object.entries(result)) {
    patchMessage(qc, { account, folder, uid: Number(uidStr) }, { category: c.category })
  }
}
