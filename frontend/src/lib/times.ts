// Zeitvorschläge für „Später senden" und Snooze — lokale Zeit, ISO ohne Zone
// (der Server vergleicht lexikografisch gegen datetime.now().isoformat()).

export type TimePreset = { id: string; label: string; iso: string }

function at(base: Date, hour: number): Date {
  const d = new Date(base)
  d.setHours(hour, 0, 0, 0)
  return d
}

function iso(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:00`
}

export function timePresets(now = new Date()): TimePreset[] {
  const presets: TimePreset[] = []
  const evening = at(now, 18)
  if (evening > now) presets.push({ id: 'evening', label: 'Heute 18:00', iso: iso(evening) })
  const tomorrow = at(new Date(now.getTime() + 86_400_000), 8)
  presets.push({ id: 'tomorrow', label: 'Morgen 08:00', iso: iso(tomorrow) })
  const saturday = new Date(now)
  saturday.setDate(now.getDate() + ((6 - now.getDay() + 7) % 7 || 7))
  presets.push({ id: 'saturday', label: 'Samstag 09:00', iso: iso(at(saturday, 9)) })
  const monday = new Date(now)
  monday.setDate(now.getDate() + ((1 - now.getDay() + 7) % 7 || 7))
  presets.push({ id: 'monday', label: 'Montag 08:00', iso: iso(at(monday, 8)) })
  return presets
}

export function formatDue(isoStr: string): string {
  const d = new Date(isoStr)
  if (Number.isNaN(d.getTime())) return isoStr
  return d.toLocaleString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
