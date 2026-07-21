import type { Reminder } from '../lib/types'
import { formatDue } from '../lib/times'
import { EmptyState } from './EmptyState'

const KIND_LABEL: Record<Reminder['kind'], string> = {
  snooze: 'schläft',
  followup: 'wartet auf Antwort',
  followup_due: 'keine Antwort!',
  snooze_failed: 'Aufwecken fehlgeschlagen',
}

/** Wiedervorlage: schlafende Mails + Follow-ups (fällige zuerst hervorgehoben). */
export function RemindersList({
  entries,
  onDone,
}: {
  entries: Reminder[]
  onDone: (reminder: Reminder) => void
}) {
  const urgent = (e: Reminder) => e.kind === 'followup_due' || e.kind === 'snooze_failed'
  const sorted = [...entries.filter(urgent), ...entries.filter((e) => !urgent(e))]
  return (
    <section className="flex h-full w-[380px] shrink-0 flex-col border-r border-hairline bg-surface">
      <div className="border-b border-hairline px-4 pb-2.5 pt-3.5">
        <div className="flex items-center gap-2">
          <h2 className="text-[15px] font-semibold">Wiedervorlage</h2>
          <span className="font-mono text-[10.5px] text-muted">{entries.length}</span>
        </div>
        <p className="mt-1 font-mono text-[10px] text-muted">Schlafende Mails und Antwort-Erinnerungen</p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {sorted.length === 0 ? (
          <EmptyState title="Alles im Fluss." subline="z schläfert Mails ein · Erinnerungen setzt du beim Senden" />
        ) : (
          sorted.map((e) => (
            <div key={e.id} className={`border-b border-hairline px-4 py-2.5 ${urgent(e) ? 'bg-[#FBF3EC]' : ''}`}>
              <div className="flex items-center gap-2">
                <span className="min-w-0 flex-1 truncate text-[13px]">{e.subject || '(Kein Betreff)'}</span>
                <time className="shrink-0 font-mono text-[10.5px] text-muted">{formatDue(e.due)}</time>
              </div>
              <div className="mt-0.5 flex items-center gap-2">
                <p className="min-w-0 flex-1 truncate text-[12px] text-muted">
                  {e.info ? `${e.info} · ` : ''}
                  <span className={urgent(e) ? 'font-medium text-[#8C5A2F]' : ''}>{KIND_LABEL[e.kind]}</span>
                </p>
                <button
                  type="button"
                  onClick={() => onDone(e)}
                  className="shrink-0 rounded border border-hairline px-1.5 py-0.5 text-[11px] text-muted transition hover:border-tinte hover:text-tinte"
                >
                  {e.kind === 'snooze' ? 'Aufwecken abbrechen' : 'Erledigt'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
