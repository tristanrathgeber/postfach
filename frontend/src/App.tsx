import { useCallback, useMemo, useRef, useState } from 'react'
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query'
import type { Detail, MsgRef, Summary } from './lib/types'
import { msgKey, refOf } from './lib/format'
import { sortCategories } from './lib/categories'
import { viewFolder, viewKey, viewTitle, type View } from './lib/view'
import { createSequenceTracker, isEditableTarget, useGlobalKeydown } from './lib/keyboard'
import { ALL_ACCOUNTS, useAccounts, useFolders, useMessagesAggregate, useSearchAggregate } from './hooks/useMailData'
import { useMailActions } from './hooks/useMailActions'
import { AppShell } from './components/AppShell'
import { Sidebar } from './components/Sidebar'
import { MessageList } from './components/MessageList'
import { Reader } from './components/Reader'
import { Composer, type ComposerState } from './components/Composer'
import { CommandPalette, type PaletteAction } from './components/CommandPalette'
import { EmiliaPanel } from './components/EmiliaPanel'
import { SparklesIcon } from './components/Icons'
import { ToastProvider, useToast } from './components/Toast'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 },
  },
})

/**
 * key für <Composer>: Ersetzen des ComposerState (z. B. via ⌘K-Palette) muss
 * die Komponente remounten, sonst bleiben An/Betreff/Konto des vorherigen
 * Zustands stehen. Die laufende Nummer remountet auch bei zweimal "Verfassen".
 */
function composerKey({ id, state }: { id: number; state: ComposerState }): string {
  return state.mode === 'reply'
    ? `reply:${state.detail.account}:${state.detail.folder}:${state.detail.uid}`
    : `new:${state.account}:${id}`
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
  const [opened, setOpened] = useState<MsgRef | null>(null)
  const [composer, setComposer] = useState<{ id: number; state: ComposerState } | null>(null)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [emiliaOpen, setEmiliaOpen] = useState(false)
  // "Bilder laden" gilt nur für genau eine Nachricht (msgKey)
  const [imagesFor, setImagesFor] = useState<string | null>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const prevViewRef = useRef<View>({ kind: 'inbox' })
  const seqRef = useRef(createSequenceTracker())
  const composerSeq = useRef(0)

  const openComposer = useCallback((state: ComposerState) => {
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
  const searchActive = view.kind === 'search'
  const messagesAgg = useMessagesAggregate(accountNames, folder)
  // Sidebar-Zähler und Kategorien hängen immer an der INBOX, nicht an der
  // aktiven Ansicht (sonst kippen sie z. B. in "Gesendet" um). Ist die Ansicht
  // selbst die Inbox, teilen sich beide Hooks denselben Query-Cache.
  const inboxAgg = useMessagesAggregate(accountNames, 'INBOX')
  const searchAgg = useSearchAggregate(accountNames, searchActive ? view.query : '', folder)
  const foldersQuery = useFolders(accountSel === ALL_ACCOUNTS ? null : accountSel)
  const actions = useMailActions()

  const visible = useMemo((): Summary[] => {
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

  // --- Aktionen ---
  const { mutate: setSeenMutate } = actions.setSeen
  const { mutate: moveMutate } = actions.move
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
    (ref: MsgRef, action: 'archive' | 'trash') => {
      const key = msgKey(ref)
      const idx = visible.findIndex((m) => msgKey(m) === key)
      const next = idx >= 0 ? (visible[idx + 1] ?? visible[idx - 1]) : undefined
      moveMutate({ ref, action })
      setSelectedKey((cur) => (cur === key ? (next ? msgKey(next) : null) : cur))
      setOpened((cur) => (cur && msgKey(cur) === key ? null : cur))
    },
    [visible, moveMutate],
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
    if (paletteOpen || composer) return // Palette/Composer behandeln Esc selbst
    if (e.key === 'Escape') {
      // Esc-Priorität: Palette > Composer > Emilia > Suche
      if (emiliaOpen) setEmiliaOpen(false)
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
      case 'e':
        if (selectedMsg) removeMessage(refOf(selectedMsg), 'archive')
        break
      case '#':
        if (selectedMsg) removeMessage(refOf(selectedMsg), 'trash')
        break
      case 'u':
        if (selectedMsg) toggleSeen(selectedMsg)
        break
      case 'r':
        e.preventDefault()
        replyToOpened()
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

    list.push({ id: 'view-inbox', group: 'Ansichten', label: 'Inbox', shortcut: 'g i', run: () => setView({ kind: 'inbox' }) })
    list.push({ id: 'view-unread', group: 'Ansichten', label: 'Ungelesen', run: () => setView({ kind: 'unread' }) })
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
  }, [accounts, categories, composeNew, opened, removeMessage, replyToOpened, runSortieren, selectedMsg, toggleSeen])

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
            folders={foldersQuery.data ?? []}
          />
        }
        list={
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
            activeQuery={view.kind === 'search' ? view.query : ''}
            searchInputRef={searchInputRef}
            onSearchSubmit={submitSearch}
            onClearSearch={clearSearch}
            onOpen={openMessage}
            onArchive={archiveMessage}
            onTrash={trashMessage}
            onToggleSeen={toggleSeen}
            onSortieren={runSortieren}
            sortierenPending={actions.classify.isPending}
            hasUnclassified={unclassified.length > 0}
            emptyOverride={emptyOverride}
          />
        }
        reader={
          <Reader
            opened={opened}
            imagesEnabled={imagesEnabled}
            onEnableImages={() => setImagesFor(opened ? msgKey(opened) : null)}
            onReply={(detail) => openComposer({ mode: 'reply', detail })}
            onArchive={(detail) => removeMessage(refOf(detail), 'archive')}
            onTrash={(detail) => removeMessage(refOf(detail), 'trash')}
            onToggleSeen={toggleSeen}
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
        <Composer key={composerKey(composer)} state={composer.state} accounts={accounts} onClose={() => setComposer(null)} />
      ) : null}
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} actions={paletteActions} onSearch={submitSearch} />
    </>
  )
}
