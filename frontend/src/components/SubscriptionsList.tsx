import { useEffect, useRef, useState } from 'react'
import type { Subscription } from '../lib/types'
import { EmptyState } from './EmptyState'

export type SubscriptionRow = Subscription & { account: string }

/** Zeilen-Identität über Konten hinweg: derselbe Newsletter in zwei Konten
 * darf weder Links noch Armierung noch Busy-Zustand teilen. */
function subscriptionKey(row: { account: string; addr: string }): string {
  return `${row.account}:${row.addr}`
}

const METHOD_LABEL: Record<Subscription['method'], string> = {
  oneclick: '1-Klick',
  mailto: 'per Mail',
  link: 'Link',
  none: 'manuell',
}

// Bestätigender Klick zählt erst nach dieser Karenz — ein versehentlicher
// Doppelklick (arm + fire in ~100 ms) würde die Zweitklick-Bestätigung
// sonst aushebeln, und die Aktion geht nach außen.
const CONFIRM_GRACE_MS = 300

/** Abo-Manager: Newsletter nach Frequenz, Abmelden mit Zweitklick-Bestätigung.
 * `links` = vom Server gelieferte Abmelde-URLs für Absender ohne
 * One-Click/mailto — die UI öffnet sie im Browser. */
export function SubscriptionsList({
  entries,
  links,
  busyKey,
  onUnsubscribe,
}: {
  entries: SubscriptionRow[]
  links: Record<string, string>
  busyKey: string | null
  onUnsubscribe: (entry: SubscriptionRow) => void
}) {
  // Zweitklick-Bestätigung: erster Klick armiert nur diese eine Zeile.
  const [armedKey, setArmedKey] = useState<string | null>(null)
  const armedAtRef = useRef(0)
  useEffect(() => {
    if (armedKey === null) return
    const t = setTimeout(() => setArmedKey(null), 4000)
    return () => clearTimeout(t)
  }, [armedKey])

  const activeCount = entries.filter((s) => s.unsubscribed_at === null).length
  const doneCount = entries.length - activeCount

  return (
    <section className="flex h-full w-[380px] shrink-0 flex-col border-r border-hairline bg-surface">
      <div className="border-b border-hairline px-4 pb-2.5 pt-3.5">
        <div className="flex items-center gap-2">
          <h2 className="text-[15px] font-semibold">Abos</h2>
          <span className="font-mono text-[10.5px] text-muted">
            {activeCount}
            {doneCount > 0 ? ` · ${doneCount} abgemeldet` : ''}
          </span>
        </div>
        <p className="mt-1 font-mono text-[10px] text-muted">Newsletter & Verteiler — abmelden per List-Unsubscribe</p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {entries.length === 0 ? (
          <EmptyState title="Keine Abos gefunden." subline="Hier erscheinen Absender mit Abmelde-Header" />
        ) : (
          entries.map((s) => {
            const rowKey = subscriptionKey(s)
            const done = s.unsubscribed_at !== null
            const link = links[rowKey]
            const busy = busyKey === rowKey
            const armed = armedKey === rowKey
            return (
              <div key={rowKey} className={`border-b border-hairline px-4 py-2.5 ${done ? 'opacity-50' : ''}`}>
                <div className="flex items-center gap-2">
                  <span className="min-w-0 flex-1 truncate text-[13px] font-medium">{s.name}</span>
                  <span className="shrink-0 font-mono text-[10.5px] text-muted">
                    {s.per_month.toLocaleString('de-DE', { maximumFractionDigits: 1 })}/Monat
                  </span>
                </div>
                <div className="mt-0.5 flex items-center gap-2">
                  <p className="min-w-0 flex-1 truncate font-mono text-[10.5px] text-muted">{s.addr}</p>
                  <span className="shrink-0 rounded bg-hover px-1 font-mono text-[9.5px] text-muted">
                    {s.count} {s.count === 1 ? 'Mail' : 'Mails'} · {METHOD_LABEL[s.method]}
                  </span>
                  {done ? (
                    <span className="shrink-0 font-mono text-[10px] text-muted">abgemeldet</span>
                  ) : link ? (
                    <a
                      href={link}
                      target="_blank"
                      rel="noreferrer"
                      className="shrink-0 rounded border border-tinte px-1.5 py-0.5 text-[11px] text-tinte"
                    >
                      Abmeldeseite öffnen
                    </a>
                  ) : s.method === 'none' ? null : (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={(e) => {
                        if (armed) {
                          // Doppelklick (e.detail > 1) oder Klick innerhalb der
                          // Karenz = noch derselbe Handgriff, keine Bestätigung.
                          if (e.detail > 1 || Date.now() - armedAtRef.current < CONFIRM_GRACE_MS) return
                          setArmedKey(null)
                          onUnsubscribe(s)
                        } else {
                          armedAtRef.current = Date.now()
                          setArmedKey(rowKey)
                        }
                      }}
                      className={`shrink-0 rounded border px-1.5 py-0.5 text-[11px] transition ${
                        armed
                          ? 'border-red-700 bg-red-700 text-white'
                          : 'border-hairline text-muted hover:border-tinte hover:text-tinte'
                      } ${busy ? 'opacity-50' : ''}`}
                    >
                      {busy ? 'Läuft…' : armed ? 'Wirklich abmelden?' : 'Abmelden'}
                    </button>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </section>
  )
}
