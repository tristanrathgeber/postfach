import type { OutboxEntry } from '../lib/types'
import { formatDue } from '../lib/times'
import { EmptyState } from './EmptyState'

/** Ausgang: geplante Sends (Undo-Fenster + Später senden) — stornierbar. */
export function OutboxList({
  entries,
  onCancel,
}: {
  entries: OutboxEntry[]
  onCancel: (entry: OutboxEntry) => void
}) {
  return (
    <section className="flex h-full w-[380px] shrink-0 flex-col border-r border-hairline bg-surface">
      <div className="border-b border-hairline px-4 pb-2.5 pt-3.5">
        <div className="flex items-center gap-2">
          <h2 className="text-[15px] font-semibold">Ausgang</h2>
          <span className="font-mono text-[10.5px] text-muted">{entries.length}</span>
        </div>
        <p className="mt-1 font-mono text-[10px] text-muted">Geplante Sends — nichts geht still raus</p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {entries.length === 0 ? (
          <EmptyState title="Nichts geplant." subline={'„Später senden" im Composer legt hier ab'} />
        ) : (
          entries.map((e) => (
            <div key={e.id} className="border-b border-hairline px-4 py-2.5">
              <div className="flex items-center gap-2">
                <span className={`min-w-0 flex-1 truncate text-[13px] ${e.kind === 'failed' ? 'text-red-700' : ''}`}>
                  {e.subject || '(Kein Betreff)'}
                </span>
                <time className="shrink-0 font-mono text-[10.5px] text-muted">{formatDue(e.due)}</time>
              </div>
              <div className="mt-0.5 flex items-center gap-2">
                <p className="min-w-0 flex-1 truncate text-[12px] text-muted">An: {e.to.join(', ')}</p>
                <span className="shrink-0 rounded bg-[#F1EFEA] px-1 font-mono text-[9.5px] text-muted">
                  {e.kind === 'undo' ? 'gleich' : e.kind === 'failed' ? 'fehlgeschlagen' : 'geplant'}
                </span>
                <button
                  type="button"
                  onClick={() => onCancel(e)}
                  className="shrink-0 rounded border border-hairline px-1.5 py-0.5 text-[11px] text-muted transition hover:border-tinte hover:text-tinte"
                >
                  {e.kind === 'failed' ? 'Verwerfen' : 'Stornieren'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
