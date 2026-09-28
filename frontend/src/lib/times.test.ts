import { describe, expect, it } from 'vitest'
import { timePresets } from './times'

describe('timePresets', () => {
  it('liefert an einem Sonntag keine doppelten Zeitpunkte (Morgen == Montag)', () => {
    const sunday = new Date('2026-10-04T10:00:00')
    const isos = timePresets(sunday).map((p) => p.iso)
    expect(new Set(isos).size).toBe(isos.length)
  })

  it('Montag-Vorschlag bleibt an einem Werktag der nächste Montag', () => {
    const wednesday = new Date('2026-09-30T10:00:00')
    const monday = timePresets(wednesday).find((p) => p.id === 'monday')
    expect(monday?.iso).toBe('2026-10-05T08:00:00')
  })
})
