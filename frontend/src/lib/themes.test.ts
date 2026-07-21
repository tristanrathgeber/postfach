import { describe, expect, it } from 'vitest'
import { PALETTES, PALETTE_IDS, darken } from './themes'

describe('darken', () => {
  it('darkens each channel by the given fraction', () => {
    // #6496c8 → 100,150,200; 16% darker → 84,126,168 = #547ea8
    expect(darken('#6496c8', 0.16)).toBe('#547ea8')
  })

  it('accepts a hex without the leading hash', () => {
    expect(darken('ffffff', 0.5)).toBe('#808080')
  })

  it('clamps black to black and pads short channels', () => {
    expect(darken('#000000', 0.16)).toBe('#000000')
    expect(darken('#0a0a0a', 0.5)).toBe('#050505')
  })

  it('returns the input unchanged when it is not a 6-digit hex', () => {
    expect(darken('rebeccapurple')).toBe('rebeccapurple')
    expect(darken('#abc')).toBe('#abc')
  })
})

describe('PALETTES', () => {
  it('exposes Schreibtisch first as the default palette', () => {
    expect(PALETTES[0].id).toBe('schreibtisch')
  })

  it('lists exactly the six known palette ids', () => {
    expect(PALETTE_IDS).toEqual(['schreibtisch', 'nord', 'sepia', 'wald', 'rose', 'graphit'])
  })

  it('gives every palette three preview swatches', () => {
    for (const p of PALETTES) {
      expect(p.swatch).toHaveLength(3)
      for (const c of p.swatch) expect(c).toMatch(/^#[0-9a-f]{6}$/i)
    }
  })
})
