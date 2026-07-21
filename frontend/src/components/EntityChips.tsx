import { useEffect, useRef, useState } from 'react'
import type { Entity } from '../lib/types'

const KIND_LABEL: Record<Entity['kind'], string> = {
  date: 'Termin',
  amount: 'Betrag',
  tracking: 'Sendung',
}

/** Lokal erkannte Struktur (Termine, Beträge, Sendungen) als klickbare Chips:
 * Sendung → Anbieter-Tracking im Browser; sonst → in die Zwischenablage. */
export function EntityChips({ entities }: { entities: Entity[] }) {
  const [copied, setCopied] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current) }, [])
  if (entities.length === 0) return null

  const copy = (value: string) => {
    const done = navigator.clipboard?.writeText(value)
    if (!done) return // keine Zwischenablage → kein falsches „kopiert ✓"
    done.then(() => {
      setCopied(value)
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setCopied((c) => (c === value ? null : c)), 1200)
    }, () => {})
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-1.5" aria-label="Erkannte Angaben">
      {entities.map((e, i) =>
        e.url ? (
          <a
            key={`${e.kind}:${e.value}:${i}`}
            href={e.url}
            target="_blank"
            rel="noreferrer"
            title="Sendung verfolgen (Anbieter-Seite)"
            className="inline-flex items-center gap-1 rounded-full border border-hairline bg-surface px-2 py-0.5 text-[11.5px] text-tinte transition hover:border-tinte"
          >
            <span className="font-mono text-[9px] uppercase tracking-wide text-muted">{KIND_LABEL[e.kind]}</span>
            {e.text}
          </a>
        ) : (
          <button
            key={`${e.kind}:${e.value}:${i}`}
            type="button"
            onClick={() => copy(e.value)}
            title="In die Zwischenablage kopieren"
            className="inline-flex items-center gap-1 rounded-full border border-hairline bg-surface px-2 py-0.5 text-[11.5px] text-ink transition hover:border-tinte hover:text-tinte"
          >
            <span className="font-mono text-[9px] uppercase tracking-wide text-muted">{KIND_LABEL[e.kind]}</span>
            {copied === e.value ? 'kopiert ✓' : e.text}
          </button>
        ),
      )}
    </div>
  )
}
