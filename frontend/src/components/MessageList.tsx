import { useEffect, useState, type RefObject } from 'react'
import type { Summary } from '../lib/types'
import { msgKey } from '../lib/format'
import { MessageRow } from './MessageRow'
import { EmptyState } from './EmptyState'
import { SearchIcon, SpinnerIcon, XIcon } from './Icons'

type MessageListProps = {
  title: string
  messages: Summary[]
  failures: string[]
  isLoading: boolean
  listKey: string
  selectedKey: string | null
  searchActive: boolean
  activeQuery: string
  searchInputRef: RefObject<HTMLInputElement>
  onSearchSubmit: (q: string) => void
  onClearSearch: () => void
  onOpen: (msg: Summary) => void
  onArchive: (msg: Summary) => void
  onTrash: (msg: Summary) => void
  onToggleSeen: (msg: Summary) => void
  onSortieren: () => void
  sortierenPending: boolean
  hasUnclassified: boolean
  emptyOverride?: { title: string; subline: string } | null
}

function SkeletonRows() {
  return (
    <div aria-hidden="true">
      {Array.from({ length: 7 }, (_, i) => (
        <div key={i} className="animate-pulse border-b border-hairline px-4 py-3" style={{ animationDelay: `${i * 80}ms` }}>
          <div className="h-2.5 w-2/5 rounded bg-hairline" />
          <div className="mt-2 h-2.5 w-4/5 rounded bg-hairline" />
        </div>
      ))}
    </div>
  )
}

export function MessageList({
  title,
  messages,
  failures,
  isLoading,
  listKey,
  selectedKey,
  searchActive,
  activeQuery,
  searchInputRef,
  onSearchSubmit,
  onClearSearch,
  onOpen,
  onArchive,
  onTrash,
  onToggleSeen,
  onSortieren,
  sortierenPending,
  hasUnclassified,
  emptyOverride,
}: MessageListProps) {
  const [draft, setDraft] = useState('')

  // Aktive Suche in das Eingabefeld spiegeln (z. B. aus der Befehls-Palette gestartet).
  useEffect(() => {
    setDraft(searchActive ? activeQuery : '')
  }, [searchActive, activeQuery])

  return (
    <section className="flex h-full w-[380px] shrink-0 flex-col border-r border-hairline bg-surface">
      {/* Kopfzeile */}
      <div className="border-b border-hairline px-4 pb-2.5 pt-3.5">
        <div className="flex items-center gap-2">
          <h2 className="min-w-0 truncate text-[15px] font-semibold">{title}</h2>
          <span className="font-mono text-[10.5px] text-muted">{messages.length}</span>
          <span className="flex-1" />
          <button
            type="button"
            onClick={onSortieren}
            disabled={sortierenPending || !hasUnclassified}
            title="Unklassifizierte Nachrichten per KI einsortieren"
            className="flex items-center gap-1.5 rounded border border-hairline bg-surface px-2 py-1 text-[12px] text-ink transition enabled:hover:border-tinte enabled:hover:text-tinte disabled:opacity-40"
          >
            {sortierenPending ? <SpinnerIcon size={11} /> : null}
            Sortieren
          </button>
        </div>

        <div className="relative mt-2.5">
          <SearchIcon size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
          <input
            ref={searchInputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && draft.trim()) {
                onSearchSubmit(draft.trim())
              } else if (e.key === 'Escape') {
                e.currentTarget.blur()
                if (searchActive) onClearSearch()
                else setDraft('')
              }
            }}
            placeholder="Suchen …  ( / )"
            aria-label="Suchen"
            className="w-full rounded border border-hairline bg-paper py-1.5 pl-8 pr-3 text-[13px] placeholder:font-mono placeholder:text-[11px] placeholder:text-muted focus:border-tinte focus:outline-none"
          />
        </div>
      </div>

      {/* Aktive Suche */}
      {searchActive ? (
        <div className="flex items-center gap-2 border-b border-hairline bg-paper px-4 py-1.5">
          <span className="min-w-0 truncate font-mono text-[11px] text-muted">
            Suche: „{activeQuery}“
          </span>
          <span className="flex-1" />
          <button
            type="button"
            onClick={onClearSearch}
            title="Suche verlassen (Esc)"
            aria-label="Suche verlassen"
            className="rounded p-0.5 text-muted transition hover:text-ink"
          >
            <XIcon size={13} />
          </button>
        </div>
      ) : null}

      {/* Konto-Fehler (z. B. 502 — Konto nicht erreichbar); übrige Konten laufen weiter */}
      {failures.map((account) => (
        <div key={account} className="border-b border-red-300 bg-red-50 px-4 py-1.5 text-[12px] text-red-700">
          Konto {account} nicht erreichbar
        </div>
      ))}

      {/* Zeilen */}
      <div className="min-h-0 flex-1 overflow-y-auto" key={listKey}>
        {isLoading && messages.length === 0 ? (
          <SkeletonRows />
        ) : messages.length === 0 ? (
          emptyOverride ? (
            <EmptyState title={emptyOverride.title} subline={emptyOverride.subline} />
          ) : searchActive ? (
            <EmptyState title="Nichts gefunden." subline={`Keine Treffer für „${activeQuery}“`} />
          ) : (
            <EmptyState title="Nichts zu tun. Schön." subline="Keine Nachrichten in dieser Ansicht" />
          )
        ) : (
          messages.map((m, i) => (
            <MessageRow
              key={msgKey(m)}
              msg={m}
              index={i}
              selected={selectedKey === msgKey(m)}
              onOpen={onOpen}
              onArchive={onArchive}
              onTrash={onTrash}
              onToggleSeen={onToggleSeen}
            />
          ))
        )}
      </div>
    </section>
  )
}
