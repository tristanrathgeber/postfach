import type { Invite } from './types'

const DAY_OPTS: Intl.DateTimeFormatOptions = {
  weekday: 'short',
  day: '2-digit',
  month: 'long',
  year: 'numeric',
}
const DATETIME_OPTS: Intl.DateTimeFormatOptions = {
  weekday: 'short',
  day: '2-digit',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
}
const TIME_OPTS: Intl.DateTimeFormatOptions = { hour: '2-digit', minute: '2-digit' }

/** Reines Datum (all_day, `JJJJ-MM-TT`) als LOKALE Mitternacht — `new Date("2026-07-24")`
 * läse es als UTC und verschöbe westlich von UTC um einen Tag. */
function parseLocalDate(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!m) return null
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return Number.isNaN(d.getTime()) ? null : d
}

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

/** Zeitraum einer Einladung menschenlesbar. all_day ohne Uhrzeit; mehrtägige
 * terminierte Events zeigen das volle End-Datum (nicht nur die Endzeit). */
export function formatInviteWhen(inv: Invite): string {
  if (inv.all_day) {
    const start = parseLocalDate(inv.start)
    return start ? start.toLocaleDateString('de-DE', DAY_OPTS) : inv.start
  }
  const start = new Date(inv.start)
  if (Number.isNaN(start.getTime())) return inv.start
  const startStr = start.toLocaleString('de-DE', DATETIME_OPTS)
  const end = inv.end ? new Date(inv.end) : null
  if (!end || Number.isNaN(end.getTime())) return startStr
  // Gleicher Tag → nur Endzeit; sonst volles End-Datum (sonst wirkt ein
  // mehrtägiger Termin wie am selben Tag).
  const endStr = sameDay(start, end)
    ? end.toLocaleTimeString('de-DE', TIME_OPTS)
    : end.toLocaleString('de-DE', DATETIME_OPTS)
  return `${startStr} – ${endStr}`
}
