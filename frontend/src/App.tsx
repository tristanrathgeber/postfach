import { useCallback, useMemo, useRef, useState } from 'react'
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { BatchAction, Detail, Draft, MsgRef, Snippet, Summary } from './lib/types'
import { api, errText } from './lib/api'
import { msgKey, refOf } from './lib/format'
import { sortCategories } from './lib/categories'
import { viewFolder, viewKey, viewTitle, type View } from './lib/view'
import { isSpamFolder } from './lib/folders'
import { createSequenceTracker, isEditableTarget, useGlobalKeydown } from './lib/keyboard'
import {
  ALL_ACCOUNTS,
  useAccounts,
  useDraftsAggregate,
  useFolders,
  useMessagesAggregate,
  useSearchAggregate,
} from './hooks/useMailData'
import { useLiveEvents } from './hooks/useLiveEvents'
import { useMailActions } from './hooks/useMailActions'
import { AppShell } from './components/AppShell'
import { Sidebar } from './components/Sidebar'
import { MessageList } from './components/MessageList'
import { DraftsList } from './components/DraftsList'
import { Reader } from './components/Reader'
import { Composer, type ComposerState } from './components/Composer'
import { useOutboxAggregate, useRemindersAggregate, useSearchReady, useSettings, useSnippets } from './hooks/useLocalStores'
import { OutboxList } from './components/OutboxList'
import { RemindersList } from './components/RemindersList'
import { timePresets } from './lib/times'
import { CommandPalette, type PaletteAction } from './components/CommandPalette'
import { EmiliaPanel } from './components/EmiliaPanel'
import { SettingsModal } from './components/SettingsModal'
import { SparklesIcon } from './components/Icons'
import { ToastProvider, useToast } from './components/Toast'

const queryClient = new QueryClient({
  defaultOptions: {
    // Fallback-Netz unter dem SSE-Push: beim Fokuswechsel und alle 3 Minuten
    // leise nachladen, falls ein Live-Event verloren ging.
    queries: { retry: 1, refetchOnWindowFocus: true, refetchInterval: 180_000, staleTime: 30_000 },
  },
})

/**
 * key für <Composer>: Ersetzen des ComposerState (z. B. via ⌘K-Palette) muss
 * die Komponente remounten, sonst bleiben An/Betreff/Konto des vorherigen
 * Zustands stehen. Die laufende Nummer remountet auch bei zweimal "Verfassen".
 */
function composerKey({ id, state }: { id: number; state: ComposerState }): string {
  if (state.draft) return `draft:${state.draft.id}:${id}`
  switch (state.mode) {
    case 'reply':
      return `reply:${state.detail.account}:${state.detail.folder}:${state.detail.uid}`
    case 'forward':
      return `forward:${state.detail.account}:${state.detail.folder}:${state.detail.uid}`
    default:
      return `new:${state.account}:${id}`
  }
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <Postfach />
      </ToastProvider>
    </QueryClientProvider>
  )
}

function Postfach() {
  const qc = useQueryClient()
  const { showToast } = useToast()

  const [accountSel, setAccountSel] = useState<string>(ALL_ACCOUNTS)
  const [view, setView] = useState<View>({ kind: 'inbox' })
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  // Mehrfachauswahl für die Bulk-Triage (msgKeys); Anker für Shift-Bereiche.
  // Die Summary-Objekte werden mitgemerkt: fällt eine markierte Mail aus der
  // sichtbaren Liste (Refetch, Ungelesen-Filter), wirkt die Aktion trotzdem.
  const [checked, setChecked] = useState<ReadonlySet<string>>(new Set())
  const checkedMsgsRef = useRef(new Map<string, Summary>())
  const checkAnchorRef = useRef<string | null>(null)
  const [opened, setOpened] = useState<MsgRef | null>(null)
  const [composer, setComposer] = useState<{ id: number; state: ComposerState } | null>(null)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [emiliaOpen, setEmiliaOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  // "Bilder laden" gilt nur für genau eine Nachricht (msgKey)
  const [imagesFor, setImagesFor] = useState<string | null>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const prevViewRef = useRef<View>({ kind: 'inbox' })
  const seqRef = useRef(createSequenceTracker())
  const composerSeq = useRef(0)
  // Der offene Composer registriert hier seine "Snippet an Cursor einfügen"-Funktion (⌘K-Palette).
  const snippetInsertRef = useRef<((snip: Snippet) => void) | null>(null)
  // … und seine Persist-Funktion: Ersetzen (z. B. ⌘K → "Weiterleiten" bei
  // offenem Composer) darf getippten Text nie stillschweigend wegwerfen.
  const composerPersistRef = useRef<(() => void) | null>(null)

  const openComposer = useCallback((state: ComposerState) => {
    composerPersistRef.current?.()
    composerSeq.current += 1
    setComposer({ id: composerSeq.current, state })
  }, [])

  // --- Daten ---
  const accountsQuery = useAccounts()
  const accounts = useMemo(() => accountsQuery.data ?? [], [accountsQuery.data])
  const accountNames = useMemo(
    () => (accountSel === ALL_ACCOUNTS ? accounts.map((a) => a.name) : [accountSel]),
    [accountSel, accounts],
  )

  const folder = viewFolder(view)
  // Ordner-Rolle (deckungsgleich mit dem Backend) — steuert die !-Richtung.
  const inSpamView = isSpamFolder(folder)
  const searchActive = view.kind === 'search'
  const messagesAgg = useMessagesAggregate(accountNames, folder)
  // Sidebar-Zähler und Kategorien hängen immer an der INBOX, nicht an der
  // aktiven Ansicht (sonst kippen sie z. B. in "Gesendet" um). Ist die Ansicht
  // selbst die Inbox, teilen sich beide Hooks denselben Query-Cache.
  const inboxAgg = useMessagesAggregate(accountNames, 'INBOX')
  const searchAgg = useSearchAggregate(accountNames, searchActive ? view.query : '', folder)
  const foldersQuery = useFolders(accountSel === ALL_ACCOUNTS ? null : accountSel)
  const draftsAgg = useDraftsAggregate(accountNames)
  const searchIndexReady = useSearchReady(accountNames, searchActive)
  const outboxAgg = useOutboxAggregate(accountNames)
  const remindersAgg = useRemindersAggregate(accountNames)
  const snippetsQuery = useSnippets()
  const settingsQuery = useSettings()
  const actions = useMailActions()
  // Verbindungsstatus (Watcher) + alle konfigurierten Kategorien (Korrektur-Menü)
  const statusQuery = useQuery({ queryKey: ['status'], queryFn: api.status, refetchInterval: 60_000 })
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: api.categories, staleTime: Infinity })

  const visible = useMemo((): Summary[] => {
    if (view.kind === 'drafts' || view.kind === 'outbox' || view.kind === 'reminders') return [] // eigene Listen — keine Mail-Tastatur
    if (view.kind === 'search') return searchAgg.messages
    if (view.kind === 'unread') return messagesAgg.messages.filter((m) => !m.seen)
    if (view.kind === 'category') return messagesAgg.messages.filter((m) => m.category === view.category)
    return messagesAgg.messages
  }, [view, messagesAgg.messages, searchAgg.messages])

  const categories = useMemo(() => {
    const counts = new Map<string, number>()
    for (const m of inboxAgg.messages) {
      if (m.category) counts.set(m.category, (counts.get(m.category) ?? 0) + 1)
    }
    return sortCategories([...counts.keys()]).map((name) => ({ name, count: counts.get(name) ?? 0 }))
  }, [inboxAgg.messages])

  const unreadCount = useMemo(() => inboxAgg.messages.filter((m) => !m.seen).length, [inboxAgg.messages])
  const unclassified = useMemo(() => visible.filter((m) => m.category === null), [visible])

  // --- Auswahl ---
  const selectedIndex = useMemo(
    () => (selectedKey ? visible.findIndex((m) => msgKey(m) === selectedKey) : -1),
    [visible, selectedKey],
  )
  const selectedMsg = selectedIndex >= 0 ? visible[selectedIndex] : undefined

  const scrollRowIntoView = useCallback((key: string) => {
    requestAnimationFrame(() => {
      document.querySelector(`[data-msg="${CSS.escape(key)}"]`)?.scrollIntoView({ block: 'nearest' })
    })
  }, [])

  const moveSelection = useCallback(
    (delta: number) => {
      if (visible.length === 0) return
      const next =
        selectedIndex === -1
          ? delta > 0
            ? 0
            : visible.length - 1
          : Math.min(Math.max(selectedIndex + delta, 0), visible.length - 1)
      const key = msgKey(visible[next])
      setSelectedKey(key)
      scrollRowIntoView(key)
    },
    [visible, selectedIndex, scrollRowIntoView],
  )

  // View-/Kontowechsel: Auswahl gehört zur sichtbaren Liste — leeren.
  const viewIdent = `${viewKey(view)}|${accountSel}`
  const prevViewIdentRef = useRef(viewIdent)
  if (prevViewIdentRef.current !== viewIdent) {
    prevViewIdentRef.current = viewIdent
    if (checked.size > 0) setChecked(new Set())
    checkedMsgsRef.current.clear()
    checkAnchorRef.current = null
  }

  // --- Mehrfachauswahl (Bulk-Triage) ---
  const toggleCheck = useCallback(
    (msg: Summary, range: boolean) => {
      const key = msgKey(msg)
      setChecked((prev) => {
        const next = new Set(prev)
        if (range && checkAnchorRef.current) {
          const a = visible.findIndex((m) => msgKey(m) === checkAnchorRef.current)
          const b = visible.findIndex((m) => msgKey(m) === key)
          if (a >= 0 && b >= 0) {
            for (let i = Math.min(a, b); i <= Math.max(a, b); i++) {
              next.add(msgKey(visible[i]))
              checkedMsgsRef.current.set(msgKey(visible[i]), visible[i])
            }
            return next
          }
        }
        if (next.has(key)) {
          next.delete(key)
          checkedMsgsRef.current.delete(key)
        } else {
          next.add(key)
          checkedMsgsRef.current.set(key, msg)
        }
        return next
      })
      checkAnchorRef.current = key
      setSelectedKey(key)
    },
    [visible],
  )

  const clearChecked = useCallback(() => {
    setChecked(new Set())
    checkedMsgsRef.current.clear()
    checkAnchorRef.current = null
  }, [])

  const { mutate: bulkMutate } = actions.bulk
  const runBulk = useCallback(
    (action: BatchAction) => {
      const targets = [...checkedMsgsRef.current.values()]
      if (targets.length === 0) return
      if (action === 'spam') {
        // Richtung PRO Treffer: die Suche mischt Ordner (Spam + Inbox).
        const spamHits = targets.filter((m) => isSpamFolder(m.folder))
        const rest = targets.filter((m) => !isSpamFolder(m.folder))
        if (spamHits.length > 0) bulkMutate({ targets: spamHits, action: 'unspam' })
        if (rest.length > 0) bulkMutate({ targets: rest, action: 'spam' })
      } else {
        bulkMutate({ targets, action })
      }
      if (action !== 'read' && action !== 'unread') {
        const keys = new Set(targets.map(msgKey))
        setOpened((cur) => (cur && keys.has(msgKey(cur)) ? null : cur))
        setSelectedKey((cur) => (cur && keys.has(cur) ? null : cur))
      }
      clearChecked()
    },
    [bulkMutate, clearChecked],
  )

  // --- Aktionen ---
  const { mutate: setSeenMutate } = actions.setSeen
  const { mutate: classifyMutate } = actions.classify

  const openMessage = useCallback(
    (msg: Summary) => {
      setSelectedKey(msgKey(msg))
      setOpened(refOf(msg))
      // Vertrag: Öffnen markiert NICHT automatisch als gelesen — wir senden
      // beim Öffnen genau einmal explizit {"action":"read"} (nur falls ungelesen).
      if (!msg.seen) setSeenMutate({ ref: refOf(msg), seen: true })
    },
    [setSeenMutate],
  )

  const toggleSeen = useCallback(
    (msg: Summary) => {
      setSeenMutate({ ref: refOf(msg), seen: !msg.seen })
    },
    [setSeenMutate],
  )

  const removeMessage = useCallback(
    (ref: MsgRef, action: 'archive' | 'trash' | 'spam' | 'unspam') => {
      const key = msgKey(ref)
      const idx = visible.findIndex((m) => msgKey(m) === key)
      const next = idx >= 0 ? (visible[idx + 1] ?? visible[idx - 1]) : undefined
      bulkMutate({ targets: [ref], action })
      setSelectedKey((cur) => (cur === key ? (next ? msgKey(next) : null) : cur))
      setOpened((cur) => (cur && msgKey(cur) === key ? null : cur))
    },
    [visible, bulkMutate],
  )

  const runSortieren = useCallback(() => {
    if (unclassified.length > 0) classifyMutate(unclassified)
  }, [unclassified, classifyMutate])

  // Stabile Referenzen, damit memo(MessageRow) bei Auswahlwechseln nicht neu rendert.
  const archiveMessage = useCallback((m: Summary) => removeMessage(refOf(m), 'archive'), [removeMessage])
  const trashMessage = useCallback((m: Summary) => removeMessage(refOf(m), 'trash'), [removeMessage])

  const composeNew = useCallback(() => {
    const account = accountSel !== ALL_ACCOUNTS ? accountSel : accounts[0]?.name
    if (!account) {
      showToast('Kein Konto verfügbar.', 'error')
      return
    }
    openComposer({ mode: 'new', account })
  }, [accountSel, accounts, openComposer, showToast])

  const replyToOpened = useCallback(() => {
    if (!opened) return
    const detail = qc.getQueryData<Detail>(['message', opened.account, opened.folder, opened.uid])
    if (detail) openComposer({ mode: 'reply', detail })
  }, [opened, openComposer, qc])

  const forwardOpened = useCallback(() => {
    if (!opened) return
    const detail = qc.getQueryData<Detail>(['message', opened.account, opened.folder, opened.uid])
    if (detail) openComposer({ mode: 'forward', detail })
  }, [opened, openComposer, qc])

  // --- Entwürfe: Fortsetzen & Löschen ---
  const openDraft = useCallback(
    async (draft: Draft) => {
      // Antwort-/Weiterleitungs-Entwürfe brauchen das Original als Kontext
      // (Threading bzw. forward_of) — Detail nachladen, sonst als "neu" fortsetzen.
      if (draft.mode !== 'new' && draft.ref_folder && draft.ref_uid !== undefined) {
        try {
          const detail = await qc.fetchQuery({
            queryKey: ['message', draft.account, draft.ref_folder, draft.ref_uid],
            queryFn: () => api.message(draft.account, draft.ref_uid!, draft.ref_folder),
          })
          if (draft.mode === 'reply') openComposer({ mode: 'reply', detail, draft })
          else openComposer({ mode: 'forward', detail, draft })
          return
        } catch {
          // Original nicht mehr ladbar → Text nicht verlieren, als neue Mail fortsetzen.
          showToast('Original nicht mehr auffindbar — Entwurf ohne Threading/Anhänge fortgesetzt.', 'error')
        }
      }
      openComposer({ mode: 'new', account: draft.account, draft })
    },
    [openComposer, qc, showToast],
  )

  const deleteDraftMutation = useMutation({
    mutationFn: (draft: Draft) => api.deleteDraft(draft.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['drafts'] })
      showToast('Entwurf gelöscht.')
    },
    onError: (e) => showToast(`Entwurf nicht löschbar: ${errText(e)}`, 'error'),
  })
  const deleteDraft = deleteDraftMutation.mutate

  // --- Zeit-Features ---
  const snoozeMutation = useMutation({
    mutationFn: ({ ref, until }: { ref: MsgRef; until: string }) => api.snooze(ref, until),
    onMutate: ({ ref }) => {
      // Optimistisch aus den Listen — die Mail wandert in den Ordner „Später".
      const removeRow = (old: Summary[] | undefined) => old?.filter((m) => !(m.account === ref.account && m.folder === ref.folder && m.uid === ref.uid))
      qc.setQueriesData<Summary[]>({ queryKey: ['messages'] }, removeRow)
      qc.setQueriesData<Summary[]>({ queryKey: ['search'] }, removeRow)
    },
    onSuccess: (_d, { ref, until }) => {
      qc.invalidateQueries({ queryKey: ['reminders'] })
      qc.invalidateQueries({ queryKey: ['messages', ref.account, ref.folder], refetchType: 'none' })
      showToast(`Wiedervorlage: ${new Date(until).toLocaleString('de-DE', { weekday: 'short', hour: '2-digit', minute: '2-digit' })}`)
      setOpened((cur) => (cur && msgKey(cur) === msgKey(ref) ? null : cur))
    },
    onError: (e, { ref }) => {
      showToast(`Wiedervorlage fehlgeschlagen: ${errText(e)}`, 'error')
      qc.invalidateQueries({ queryKey: ['messages', ref.account, ref.folder] })
    },
  })
  const { mutate: snoozeMutate } = snoozeMutation
  const snoozeMail = (ref: MsgRef, until: string) => snoozeMutate({ ref, until })

  const cancelOutboxMutation = useMutation({
    mutationFn: (id: string) => api.cancelOutbox(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outbox'] })
      qc.invalidateQueries({ queryKey: ['drafts'] })
      showToast('Storniert — der Text liegt in den Entwürfen.')
    },
    onError: (e) => showToast(`Stornieren fehlgeschlagen: ${errText(e)}`, 'error'),
  })

  const reminderDoneMutation = useMutation({
    mutationFn: (id: string) => api.reminderDone(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reminders'] }),
    onError: (e) => showToast(`Fehlgeschlagen: ${errText(e)}`, 'error'),
  })

  // --- Suche ---
  const submitSearch = useCallback(
    (q: string) => {
      if (view.kind !== 'search') prevViewRef.current = view
      // Gesucht wird im Ordner der Ansicht, aus der die Suche gestartet wurde.
      setView({ kind: 'search', query: q, folder: viewFolder(view) })
    },
    [view],
  )

  const clearSearch = useCallback(() => {
    setView(prevViewRef.current)
  }, [])

  // --- Tastatur ---
  useGlobalKeydown((e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault()
      setPaletteOpen((v) => !v)
      return
    }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'j') {
      e.preventDefault()
      setEmiliaOpen((v) => !v)
      return
    }
    if (paletteOpen || composer || settingsOpen) return // Palette/Composer/Einstellungen behandeln Esc selbst
    if (e.key === 'Escape') {
      // Esc-Priorität: Palette > Composer > Auswahl > Emilia > Suche.
      // In Eingabefeldern gehört Esc dem Feld (Suchfeld leeren, Emilia-Input).
      if (isEditableTarget(e)) return
      if (checked.size > 0) clearChecked()
      else if (emiliaOpen) setEmiliaOpen(false)
      else if (searchActive) clearSearch()
      return
    }
    if (isEditableTarget(e) || e.metaKey || e.ctrlKey || e.altKey) return

    switch (e.key) {
      case 'j':
        e.preventDefault()
        moveSelection(1)
        break
      case 'k':
        e.preventDefault()
        moveSelection(-1)
        break
      case 'Enter':
      case 'o':
        if (selectedMsg) openMessage(selectedMsg)
        break
      case 'x':
      case 'X':
        if (selectedMsg) toggleCheck(selectedMsg, e.shiftKey)
        break
      case 'e':
        if (checked.size > 0) runBulk('archive')
        else if (selectedMsg) removeMessage(refOf(selectedMsg), 'archive')
        break
      case '#':
        if (checked.size > 0) runBulk('trash')
        else if (selectedMsg) removeMessage(refOf(selectedMsg), 'trash')
        break
      case 'z':
        if (selectedMsg) {
          const presets = timePresets()
          const preset = presets.find((p) => p.id === 'tomorrow') ?? presets[0]
          snoozeMail(refOf(selectedMsg), preset.iso)
        }
        break
      case '!':
        if (checked.size > 0) runBulk('spam')
        else if (selectedMsg) removeMessage(refOf(selectedMsg), inSpamView ? 'unspam' : 'spam')
        break
      case 'u':
        if (checked.size > 0) runBulk('read')
        else if (selectedMsg) toggleSeen(selectedMsg)
        break
      case 'r':
        e.preventDefault()
        replyToOpened()
        break
      case 'f':
        // Nur wenn eine Nachricht geöffnet ist (analog zu r).
        e.preventDefault()
        forwardOpened()
        break
      case 'c':
        e.preventDefault()
        composeNew()
        break
      case '/':
        e.preventDefault()
        searchInputRef.current?.focus()
        break
      case 'i':
        if (seqRef.current.consume('g')) setView({ kind: 'inbox' })
        break
      case 'g':
        seqRef.current.setPrefix('g')
        break
    }
  })

  // --- Befehls-Palette ---
  const paletteActions = useMemo<PaletteAction[]>(() => {
    const list: PaletteAction[] = []
    list.push({ id: 'verfassen', group: 'Aktionen', label: 'Verfassen', shortcut: 'c', run: composeNew })
    if (opened) {
      list.push({ id: 'antworten', group: 'Aktionen', label: 'Antworten', shortcut: 'r', run: replyToOpened })
      list.push({ id: 'weiterleiten', group: 'Aktionen', label: 'Weiterleiten', shortcut: 'f', run: forwardOpened })
      const openedRef = opened
      list.push({ id: 'bilder', group: 'Aktionen', label: 'Bilder laden', run: () => setImagesFor(msgKey(openedRef)) })
    }
    if (selectedMsg) {
      const msg = selectedMsg
      list.push({
        id: 'archivieren',
        group: 'Aktionen',
        label: 'Archivieren',
        shortcut: 'e',
        run: () => removeMessage(refOf(msg), 'archive'),
      })
      list.push({
        id: 'papierkorb',
        group: 'Aktionen',
        label: 'Papierkorb',
        shortcut: '#',
        run: () => removeMessage(refOf(msg), 'trash'),
      })
      list.push({
        id: 'ungelesen',
        group: 'Aktionen',
        label: msg.seen ? 'Als ungelesen markieren' : 'Als gelesen markieren',
        shortcut: 'u',
        run: () => toggleSeen(msg),
      })
    }
    list.push({ id: 'sortieren', group: 'Aktionen', label: 'Sortieren', keywords: ['klassifizieren'], run: runSortieren })
    list.push({
      id: 'emilia',
      group: 'Aktionen',
      label: 'Emilia öffnen/schließen',
      shortcut: '⌘J',
      keywords: ['assistent', 'ki', 'chat'],
      run: () => setEmiliaOpen((v) => !v),
    })
    list.push({
      id: 'einstellungen',
      group: 'Aktionen',
      label: 'Einstellungen',
      keywords: ['signatur', 'snippets', 'settings'],
      run: () => setSettingsOpen(true),
    })

    // Snippets an der Cursor-Position einfügen — nur sinnvoll bei offenem Composer.
    if (composer) {
      for (const s of snippetsQuery.data ?? []) {
        list.push({
          id: `snippet-${s.abbrev}`,
          group: 'Snippets',
          label: `Snippet: ${s.title || s.abbrev}`,
          keywords: [s.abbrev, 'snippet', 'baustein'],
          run: () => snippetInsertRef.current?.(s),
        })
      }
    }

    list.push({ id: 'view-inbox', group: 'Ansichten', label: 'Inbox', shortcut: 'g i', run: () => setView({ kind: 'inbox' }) })
    list.push({ id: 'view-unread', group: 'Ansichten', label: 'Ungelesen', run: () => setView({ kind: 'unread' }) })
    list.push({ id: 'view-drafts', group: 'Ansichten', label: 'Entwürfe', run: () => setView({ kind: 'drafts' }) })
    for (const c of categories) {
      list.push({
        id: `view-cat-${c.name}`,
        group: 'Ansichten',
        label: c.name,
        keywords: ['kategorie'],
        run: () => setView({ kind: 'category', category: c.name }),
      })
    }

    list.push({ id: 'acc-alle', group: 'Konten', label: 'Alle Konten', run: () => setAccountSel(ALL_ACCOUNTS) })
    for (const a of accounts) {
      list.push({
        id: `acc-${a.name}`,
        group: 'Konten',
        label: a.name,
        keywords: [a.address, 'konto'],
        run: () => setAccountSel(a.name),
      })
    }
    return list
  }, [
    accounts,
    categories,
    composeNew,
    composer,
    forwardOpened,
    opened,
    removeMessage,
    replyToOpened,
    runSortieren,
    selectedMsg,
    snippetsQuery.data,
    toggleSeen,
  ])

  // --- Onboarding / Leerzustände ---
  const emptyOverride = useMemo(() => {
    if (accountsQuery.isError) {
      return { title: 'Das Backend schläft noch.', subline: 'Backend starten, dann neu laden' }
    }
    if (accountsQuery.isSuccess && accounts.length === 0) {
      return { title: 'Willkommen im Postfach.', subline: 'Konten im Backend konfigurieren, dann neu laden' }
    }
    return null
  }, [accountsQuery.isError, accountsQuery.isSuccess, accounts.length])

  const active = searchActive ? searchAgg : messagesAgg
  const imagesEnabled = opened !== null && imagesFor === msgKey(opened)

  // --- Emilia ---
  const emiliaAccount = accountSel !== ALL_ACCOUNTS ? accountSel : (accounts[0]?.name ?? null)
  const openedDetail = opened
    ? qc.getQueryData<Detail>(['message', opened.account, opened.folder, opened.uid])
    : undefined
  const emiliaContext = opened
    ? { folder: opened.folder, uid: opened.uid, subject: openedDetail?.subject ?? '' }
    : null
  const openSource = useCallback((source: { account: string; folder: string; uid: number }) => {
    const ref: MsgRef = { account: source.account, folder: source.folder, uid: source.uid }
    setSelectedKey(msgKey(ref))
    setOpened(ref)
  }, [])

  // --- Live-Push: neue Mail → Liste sofort aktualisieren ---
  const onNewMail = useCallback(
    (account: string) => {
      qc.invalidateQueries({ queryKey: ['messages', account, 'INBOX'] })
      qc.invalidateQueries({ queryKey: ['emilia-status'] })
      qc.invalidateQueries({ queryKey: ['outbox', account] })
      qc.invalidateQueries({ queryKey: ['reminders', account] })
      showToast('Neue Mail eingetroffen.')
    },
    [qc, showToast],
  )
  const lastConnectedRef = useRef(new Map<string, boolean>())
  const onStatusChange = useCallback(
    (account: string, connected: boolean) => {
      qc.invalidateQueries({ queryKey: ['status'] })
      const prev = lastConnectedRef.current.get(account)
      lastConnectedRef.current.set(account, connected)
      if (prev === undefined && connected) return // App-Start: erster Connect ist kein "wieder verbunden"
      if (prev === connected) return
      showToast(
        connected ? `${account}: wieder verbunden.` : `${account}: Verbindung getrennt — verbinde neu …`,
        connected ? 'info' : 'error',
      )
    },
    [qc, showToast],
  )
  useLiveEvents(onNewMail, onStatusChange)

  // Kategorie-Korrektur: Override speichern, Caches werden gepatcht.
  const { mutate: overrideCategoryMutate } = actions.overrideCategory
  const changeCategory = useCallback(
    (detail: Detail, category: string) => overrideCategoryMutate({ ref: refOf(detail), category }),
    [overrideCategoryMutate],
  )

  return (
    <>
      <AppShell
        sidebar={
          <Sidebar
            accounts={accounts}
            accountSel={accountSel}
            onSelectAccount={setAccountSel}
            view={view}
            onSelectView={setView}
            categories={categories}
            inboxCount={inboxAgg.messages.length}
            unreadCount={unreadCount}
            draftsCount={draftsAgg.drafts.length}
            outboxCount={outboxAgg.entries.length}
            remindersCount={remindersAgg.entries.length}
            remindersDue={remindersAgg.dueCount}
            folders={foldersQuery.data ?? []}
            status={statusQuery.data?.accounts ?? {}}
            onOpenSettings={() => setSettingsOpen(true)}
          />
        }
        list={
          view.kind === 'outbox' ? (
            <OutboxList entries={outboxAgg.entries} onCancel={(e) => cancelOutboxMutation.mutate(e.id)} />
          ) : view.kind === 'reminders' ? (
            <RemindersList entries={remindersAgg.entries} onDone={(r) => reminderDoneMutation.mutate(r.id)} />
          ) : view.kind === 'drafts' ? (
            <DraftsList
              drafts={draftsAgg.drafts}
              isLoading={draftsAgg.isLoading}
              keysEnabled={!paletteOpen && !composer && !settingsOpen}
              onOpen={openDraft}
              onDelete={deleteDraft}
            />
          ) : (
          <MessageList
            title={viewTitle(view)}
            messages={visible}
            failures={active.failures}
            // Kaltstart: solange die Konten laden, ist accountNames leer und das
            // Aggregat meldet fälschlich "fertig" — Skeleton statt Leerzustand.
            isLoading={accountsQuery.isPending || active.isLoading}
            listKey={`${viewKey(view)}|${accountSel}`}
            selectedKey={selectedKey}
            searchActive={searchActive}
            searchIndexReady={searchIndexReady}
            activeQuery={view.kind === 'search' ? view.query : ''}
            searchInputRef={searchInputRef}
            onSearchSubmit={submitSearch}
            onClearSearch={clearSearch}
            onOpen={openMessage}
            onArchive={archiveMessage}
            onTrash={trashMessage}
            onToggleSeen={toggleSeen}
            checked={checked}
            onToggleCheck={toggleCheck}
            onBulk={runBulk}
            spamMode={inSpamView}
            onClearChecked={clearChecked}
            onSortieren={runSortieren}
            sortierenPending={actions.classify.isPending}
            hasUnclassified={unclassified.length > 0}
            emptyOverride={emptyOverride}
          />
          )
        }
        reader={
          <Reader
            opened={opened}
            imagesEnabled={imagesEnabled}
            onEnableImages={() => setImagesFor(opened ? msgKey(opened) : null)}
            onReply={(detail) => openComposer({ mode: 'reply', detail })}
            onForward={(detail) => openComposer({ mode: 'forward', detail })}
            onArchive={(detail) => removeMessage(refOf(detail), 'archive')}
            onTrash={(detail) => removeMessage(refOf(detail), 'trash')}
            onToggleSeen={toggleSeen}
            onToggleSpam={(detail, spam) => removeMessage(refOf(detail), spam ? 'spam' : 'unspam')}
            onSnooze={(detail, until) => snoozeMail(refOf(detail), until)}
            categories={categoriesQuery.data ?? []}
            onChangeCategory={changeCategory}
            onOpenThreadMail={openMessage}
            onThreadAction={(mails, action) => {
              bulkMutate({ targets: mails, action })
              const keys = new Set(mails.map(msgKey))
              setOpened((cur) => (cur && keys.has(msgKey(cur)) ? null : cur))
            }}
          />
        }
        aside={
          emiliaOpen ? (
            <EmiliaPanel
              account={emiliaAccount}
              context={emiliaContext}
              onOpenSource={openSource}
              onClose={() => setEmiliaOpen(false)}
            />
          ) : undefined
        }
      />
      {!emiliaOpen ? (
        <button
          type="button"
          onClick={() => setEmiliaOpen(true)}
          title="Emilia öffnen (⌘J)"
          className="fixed right-4 top-3 z-30 flex items-center gap-1.5 rounded-full border border-hairline bg-paper px-3 py-1.5 font-serif text-[13.5px] italic text-ink shadow-sm transition hover:border-tinte hover:text-tinte"
        >
          <SparklesIcon size={13} />
          Emilia
        </button>
      ) : null}
      {composer ? (
        <Composer
          key={composerKey(composer)}
          state={composer.state}
          accounts={accounts}
          signatures={settingsQuery.data?.signatures ?? {}}
          snippetInsertRef={snippetInsertRef}
          persistRef={composerPersistRef}
          modalAbove={settingsOpen}
          onClose={() => setComposer(null)}
        />
      ) : null}
      {settingsOpen ? <SettingsModal accounts={accounts} onClose={() => setSettingsOpen(false)} /> : null}
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} actions={paletteActions} onSearch={submitSearch} />
    </>
  )
}
