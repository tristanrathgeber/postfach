/** Farbthemen (Paletten). Die echten Token-Werte liegen in index.css;
 * hier nur Id, Name und ein paar Vorschau-Farben für die Auswahl-UI. */

export type PaletteId = 'schreibtisch' | 'nord' | 'sepia' | 'wald' | 'rose' | 'graphit'

export interface Palette {
  id: PaletteId
  label: string
  hint: string
  /** Vorschau-Swatches (light): [Papier, Akzent/Tinte, Tinte-2] */
  swatch: [string, string, string]
}

export const PALETTES: Palette[] = [
  { id: 'schreibtisch', label: 'Schreibtisch', hint: 'Warmes Papier, Tintenblau', swatch: ['#faf9f6', '#2440b3', '#8c5a2f'] },
  { id: 'nord', label: 'Nord', hint: 'Kühl-arktisches Frostblau', swatch: ['#f2f4f8', '#4c6f98', '#5c7a4a'] },
  { id: 'sepia', label: 'Sepia', hint: 'Warmes Lese-Creme', swatch: ['#f3ecda', '#9a5b28', '#5f7040'] },
  { id: 'wald', label: 'Wald', hint: 'Ruhiges Blattgrün', swatch: ['#f2f5ee', '#35704a', '#7d6a2f'] },
  { id: 'rose', label: 'Rosé', hint: 'Weiche Malve', swatch: ['#f9f3f4', '#a2496b', '#5c7a54'] },
  { id: 'graphit', label: 'Graphit', hint: 'Minimal, hoher Kontrast', swatch: ['#f5f5f3', '#33322f', '#a5423a'] },
]

export const PALETTE_IDS: PaletteId[] = PALETTES.map((p) => p.id)

/** Dunkelt einen Hex-Akzent für die „strong"-Variante ab (Button-Hover). */
export function darken(hex: string, amount = 0.16): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return hex
  const n = parseInt(m[1], 16)
  const r = Math.round(((n >> 16) & 255) * (1 - amount))
  const g = Math.round(((n >> 8) & 255) * (1 - amount))
  const b = Math.round((n & 255) * (1 - amount))
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`
}
