import { useEffect, useRef, useState } from 'react'
import { formatDue, timePresets } from '../lib/times'

/**
 * Geteiltes Zeit-Menü (Später senden im Composer, Snooze im Reader).
 * Die freie Zeit wird GEPUFFERT und erst per „Übernehmen" wirksam —
 * datetime-local feuert change schon bei halbfertigen Eingaben.
 */
export function TimePresetMenu({
  heading,
  placementClass,
  onPick,
  onClose,
}: {
  heading: string
  placementClass: string
  onPick: (iso: string) => void
  onClose: () => void
}) {
  const [custom, setCustom] = useState('')
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) onClose()
    }
    window.addEventListener('keydown', onKey, true)
    window.addEventListener('mousedown', onDown)
    return () => {
      window.removeEventListener('keydown', onKey, true)
      window.removeEventListener('mousedown', onDown)
    }
  }, [onClose])

  return (
    <div ref={rootRef} className={`absolute z-30 w-[225px] rounded border border-hairline bg-surface py-1 shadow-lg ${placementClass}`}>
      <p className="px-3 py-1 font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">{heading}</p>
      {timePresets().map((p) => (
        <button
          key={p.id}
          type="button"
          onClick={() => onPick(p.iso)}
          className="flex w-full items-baseline justify-between px-3 py-1.5 text-left text-[12.5px] hover:bg-[#F1EFEA]"
        >
          {p.label}
          <span className="font-mono text-[10px] text-muted">{formatDue(p.iso)}</span>
        </button>
      ))}
      <div className="border-t border-hairline px-3 pb-1.5 pt-2">
        <span className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Eigene Zeit</span>
        <div className="mt-1 flex gap-1">
          <input
            type="datetime-local"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            aria-label="Eigene Zeit"
            className="min-w-0 flex-1 rounded border border-hairline bg-paper px-2 py-1 text-[12px] focus:border-tinte focus:outline-none"
          />
          <button
            type="button"
            disabled={!custom}
            onClick={() => onPick(`${custom}:00`)}
            className="shrink-0 rounded bg-tinte px-2 py-1 text-[11px] font-medium text-white transition hover:bg-[#1D3494] disabled:opacity-40"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  )
}
