import type { ScreenerEntry } from '../lib/types'
import { EmptyState } from './EmptyState'

export type ScreenerRow = ScreenerEntry & { account: string }

/** Screener: Erstkontakt-Absender zulassen oder ablehnen. Der Vorschlag ist
 * ehrlich regelbasiert (Abmelde-Header / Automaten-Adresse) — die Entscheidung
 * trifft der Nutzer. „Ablehnen" sortiert künftige Mails nach „Aussortiert". */
export function ScreenerList({
  entries,
  busyKey,
  onDecide,
}: {
  entries: ScreenerRow[]
  /** `konto:adresse` der laufenden Entscheidung — sperrt beide Knöpfe der Zeile. */
  busyKey: string | null
  onDecide: (entry: ScreenerRow, decision: 'allow' | 'block') => void
}) {
  return (
    <section className="flex h-full w-[380px] shrink-0 flex-col border-r border-hairline bg-surface">
      <div className="border-b border-hairline px-4 pb-2.5 pt-3.5">
        <div className="flex items-center gap-2">
          <h2 className="text-[15px] font-semibold">Screener</h2>
          <span className="font-mono text-[10.5px] text-muted">{entries.length}</span>
        </div>
        <p className="mt-1 font-mono text-[10px] text-muted">Neue Absender — einmal entscheiden, die App merkt es sich</p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {entries.length === 0 ? (
          <EmptyState title="Alles entschieden." subline="Neue Erstkontakte erscheinen hier" />
        ) : (
          entries.map((e) => {
            const busy = busyKey === `${e.account}:${e.addr}`
            return (
            <div key={`${e.account}:${e.addr}`} className="border-b border-hairline px-4 py-2.5">
              <div className="flex items-center gap-2">
                <span className="min-w-0 flex-1 truncate text-[13px] font-medium">{e.name}</span>
                <span
                  className={`shrink-0 rounded px-1 font-mono text-[9.5px] ${
                    e.suggestion === 'block' ? 'bg-danger-bg text-danger' : 'bg-success-bg text-success'
                  }`}
                  title={e.reason}
                >
                  Vorschlag: {e.suggestion === 'block' ? 'ablehnen' : 'zulassen'}
                </span>
              </div>
              <p className="mt-0.5 truncate font-mono text-[10.5px] text-muted">{e.addr}</p>
              {e.subject ? <p className="mt-1 truncate text-[12px]">{e.subject}</p> : null}
              {e.snippet ? <p className="truncate text-[11.5px] text-muted">{e.snippet}</p> : null}
              <div className="mt-1.5 flex items-center gap-2">
                <span className="min-w-0 flex-1 truncate text-[10.5px] text-muted">{e.reason}</span>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onDecide(e, 'allow')}
                  className={`shrink-0 rounded border border-hairline px-2 py-0.5 text-[11px] text-muted transition hover:border-success hover:text-success ${busy ? 'opacity-50' : ''}`}
                >
                  Zulassen
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onDecide(e, 'block')}
                  className={`shrink-0 rounded border border-hairline px-2 py-0.5 text-[11px] text-muted transition hover:border-danger hover:text-danger ${busy ? 'opacity-50' : ''}`}
                  title={'Künftige Mails landen im Ordner „Aussortiert“ — nichts wird gelöscht'}
                >
                  Ablehnen
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
