import { describe, expect, it } from 'vitest'
import { formatInviteWhen } from './invite'
import type { Invite } from './types'

function inv(over: Partial<Invite>): Invite {
  return {
    summary: 'Test',
    start: '',
    end: '',
    all_day: false,
    location: '',
    organizer_name: '',
    organizer_email: '',
    method: 'REQUEST',
    uid: 'x',
    ...over,
  }
}

const MONTHS = /Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember/

describe('formatInviteWhen', () => {
  it('all-day: kein Datumssprung, keine Uhrzeit (lokale Interpretation)', () => {
    const out = formatInviteWhen(inv({ all_day: true, start: '2026-07-24', end: '2026-07-25' }))
    expect(out).toContain('24')
    expect(out).toContain('Juli')
    expect(out).toContain('2026')
    expect(out).not.toContain(':') // keine Uhrzeit bei all_day
  })

  it('terminiert, gleicher Tag: nur die Endzeit anhängen', () => {
    const out = formatInviteWhen(inv({ start: '2026-07-24T13:00:00+02:00', end: '2026-07-24T14:00:00+02:00' }))
    // genau ein Datum (ein Monatsname), Zeitspanne mit Bindestrich
    expect(out).toContain('–')
    expect(out.match(new RegExp(MONTHS, 'g'))).toHaveLength(1)
  })

  it('terminiert, mehrtägig: End-Datum bleibt erhalten (nicht nur die Uhrzeit)', () => {
    const out = formatInviteWhen(inv({ start: '2026-07-24T10:00:00+02:00', end: '2026-07-26T12:00:00+02:00' }))
    // nach dem Bindestrich MUSS ein Monatsname stehen (volles End-Datum)
    const afterDash = out.split('–')[1] ?? ''
    expect(afterDash).toMatch(MONTHS)
  })

  it('kaputte/leere Werte → nie „Invalid Date"', () => {
    expect(formatInviteWhen(inv({ start: 'kein datum' }))).toBe('kein datum')
    expect(formatInviteWhen(inv({ start: '2026-07-24T13:00:00+02:00', end: 'kaputt' }))).not.toContain('Invalid')
  })
})
