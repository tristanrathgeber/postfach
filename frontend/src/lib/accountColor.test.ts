import { describe, expect, it } from 'vitest'
import { accountColor } from './accountColor'

const HEX = /^#[0-9a-fA-F]{6}$/

describe('accountColor', () => {
  it('deterministisch: gleicher Name → gleiche Farbe', () => {
    expect(accountColor('gmx')).toBe(accountColor('gmx'))
    expect(accountColor('privat')).toBe(accountColor('privat'))
  })

  it('leerer Name fällt sauber auf die erste Palettenfarbe', () => {
    expect(accountColor('')).toMatch(HEX)
  })

  it('liefert für beliebige Namen immer eine gültige Palettenfarbe (kein Overflow/negativ)', () => {
    for (const n of ['a', 'ZZZZZZZZ', 'gmx-privat-2', 'Über-Konto', '12345678901234567890']) {
      expect(accountColor(n)).toMatch(HEX)
    }
  })
})
