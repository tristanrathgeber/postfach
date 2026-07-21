import { useCallback, useState } from 'react'
import type { Draft } from '../lib/types'
import { formatListDate } from '../lib/format'
import { isEditableTarget, useGlobalKeydown } from '../lib/keyboard'
import { EmptyState } from './EmptyState'
import { SpinnerIcon, TrashIcon } from './Icons'

type DraftsListProps = {
  drafts: Draft[]
  isLoading: boolean
  /** false, solange Palette/Composer/Einstellungen offen sind — dann keine Listen-Tasten. */
  keysEnabled: boolean
  onOpen: (draft: Draft) => void
  onDelete: (draft: Draft) => void
}

const MODE_LABEL: Record<Draft['mode'], string | null> = {
  new: null,
  reply: 'Antwort',
  forward: 'Weiterleitung',
}

/** Entwürfe-Ansicht (ersetzt die MessageList): lokale Artefakte, Öffnen/Fortsetzen/Löschen. */
export function DraftsList({ drafts, isLoading, keysEnabled, onOpen, onDelete }: DraftsListProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selectedIndex = selectedId ? drafts.findIndex((d) => d.id === selectedId) : -1
  const selected = selectedIndex >= 0 ? drafts[selectedIndex] : undefined

  const moveSelection = useCallback(
    (delta: number) => {
      if (drafts.length === 0) return
      const entry = delta > 0 ? 0 : drafts.length - 1
      const next = selectedIndex === -1 ? entry : Math.min(Math.max(selectedIndex + delta, 0), drafts.length - 1)
      const id = drafts[next].id
      setSelectedId(id)
      requestAnimationFrame(() => {
        document.querySelector(`[data-draft="${CSS.escape(id)}"]`)?.scrollIntoView({ block: 'nearest' })
      })
    },
    [drafts, selectedIndex],
  )

  useGlobalKeydown((e) => {
    if (!keysEnabled || isEditableTarget(e) || e.metaKey || e.ctrlKey || e.altKey) return
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
        if (selected) onOpen(selected)
        break
      case '#':
        if (selected) {
          const next = drafts[selectedIndex + 1] ?? drafts[selectedIndex - 1]
          onDelete(selected)
          setSelectedId(next ? next.id : null)
        }
        break
    }
  })

  return (
    <section className="flex h-full w-[380px] shrink-0 flex-col border-r border-hairline bg-surface">
      <div className="border-b border-hairline px-4 pb-2.5 pt-3.5">
        <div className="flex items-center gap-2">
          <h2 className="min-w-0 truncate text-[15px] font-semibold">Entwürfe</h2>
          <span className="font-mono text-[10.5px] text-muted">{drafts.length}</span>
          <span className="flex-1" />
          {isLoading ? <SpinnerIcon size={12} className="text-muted" /> : null}
        </div>
        <p className="mt-1 font-mono text-[10px] text-muted">Lokal gespeichert · Enter öffnen · # löschen</p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {drafts.length === 0 ? (
          isLoading ? null : (
            <EmptyState title="Keine Entwürfe." subline="Der Composer speichert automatisch beim Tippen" />
          )
        ) : (
          drafts.map((d, i) => {
            const active = d.id === selectedId
            const modeLabel = MODE_LABEL[d.mode]
            return (
              <div
                key={d.id}
                data-draft={d.id}
                role="button"
                tabIndex={-1}
                onClick={() => {
                  setSelectedId(d.id)
                  onOpen(d)
                }}
                className={`row-enter group relative cursor-pointer border-b border-hairline px-4 py-2.5 transition ${
                  active ? 'bg-[#EFF2FB]' : 'hover:bg-[#F8F7F4]'
                }`}
                style={{ animationDelay: `${Math.min(i, 15) * 22}ms` }}
              >
                {active ? <span className="absolute inset-y-0 left-0 w-[2px] bg-tinte" aria-hidden="true" /> : null}

                <div className="flex items-center gap-1.5">
                  <span className="min-w-0 flex-1 truncate text-[13px] font-medium">
                    {d.subject || '(Kein Betreff)'}
                  </span>
                  {modeLabel ? (
                    <span className="shrink-0 rounded border border-hairline bg-paper px-1 py-px font-mono text-[9px] uppercase tracking-wide text-muted">
                      {modeLabel}
                    </span>
                  ) : null}
                  <time className="shrink-0 font-mono text-[10.5px] text-muted group-hover:invisible">
                    {formatListDate(d.updated)}
                  </time>
                </div>
                <p className="mt-0.5 min-w-0 truncate text-[12.5px] text-muted">
                  {d.to.length > 0 ? `An: ${d.to.join(', ')}` : 'Ohne Empfänger'}
                </p>

                {/* Löschen bei Hover */}
                <div className="absolute right-2 top-1.5 hidden items-center rounded border border-hairline bg-surface px-0.5 py-px shadow-sm group-hover:flex">
                  <button
                    type="button"
                    title="Entwurf löschen (#)"
                    aria-label="Entwurf löschen"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete(d)
                    }}
                    className="rounded p-1 text-muted transition hover:bg-[#F1EFEA] hover:text-ink"
                  >
                    <TrashIcon size={13} />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </section>
  )
}
