import { useCallback, useEffect, useState } from 'react'
import { PALETTE_IDS, darken, type PaletteId } from '../lib/themes'

export type Theme = 'system' | 'light' | 'dark'
export type Density = 'comfortable' | 'compact'

const THEME_KEY = 'postfach.theme'
const DENSITY_KEY = 'postfach.density'
const PALETTE_KEY = 'postfach.palette'
const ACCENT_KEY = 'postfach.accent'

function read<T extends string>(key: string, fallback: T, valid: readonly T[]): T {
  try {
    const v = localStorage.getItem(key)
    if (v && (valid as readonly string[]).includes(v)) return v as T
  } catch {
    // localStorage nicht verfügbar → Default
  }
  return fallback
}

function readAccent(): string | null {
  try {
    const v = localStorage.getItem(ACCENT_KEY)
    return v && /^#[0-9a-fA-F]{6}$/.test(v) ? v : null
  } catch {
    return null
  }
}

/** Theme anwenden: light/dark setzen data-theme (überstimmt die Media-Query),
 * system entfernt es (dann greift prefers-color-scheme automatisch). */
function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'system') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', theme)
}

/** Palette anwenden: Default „schreibtisch" ohne Attribut (nutzt :root direkt). */
function applyPalette(palette: PaletteId) {
  const root = document.documentElement
  if (palette === 'schreibtisch') root.removeAttribute('data-palette')
  else root.setAttribute('data-palette', palette)
}

/** Custom-Akzent per Inline-Style setzen (überstimmt jede Palette); null = zurück. */
function applyAccent(accent: string | null) {
  const s = document.documentElement.style
  if (!accent) {
    for (const p of ['--tinte', '--tinte-strong', '--btn', '--btn-strong']) s.removeProperty(p)
    return
  }
  const strong = darken(accent, 0.16)
  s.setProperty('--tinte', accent)
  s.setProperty('--tinte-strong', strong)
  s.setProperty('--btn', accent)
  s.setProperty('--btn-strong', strong)
}

export function usePreferences() {
  const [theme, setThemeState] = useState<Theme>(() => read(THEME_KEY, 'system', ['system', 'light', 'dark']))
  const [density, setDensityState] = useState<Density>(() =>
    read(DENSITY_KEY, 'comfortable', ['comfortable', 'compact']),
  )
  const [palette, setPaletteState] = useState<PaletteId>(() => read(PALETTE_KEY, 'schreibtisch', PALETTE_IDS))
  const [accent, setAccentState] = useState<string | null>(() => readAccent())

  useEffect(() => applyTheme(theme), [theme])
  useEffect(() => applyPalette(palette), [palette])
  useEffect(() => applyAccent(accent), [accent])

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t)
    try {
      localStorage.setItem(THEME_KEY, t)
    } catch {
      /* ignore */
    }
  }, [])

  const setDensity = useCallback((d: Density) => {
    setDensityState(d)
    try {
      localStorage.setItem(DENSITY_KEY, d)
    } catch {
      /* ignore */
    }
  }, [])

  const setPalette = useCallback((p: PaletteId) => {
    setPaletteState(p)
    try {
      localStorage.setItem(PALETTE_KEY, p)
    } catch {
      /* ignore */
    }
  }, [])

  const setAccent = useCallback((a: string | null) => {
    setAccentState(a)
    try {
      if (a) localStorage.setItem(ACCENT_KEY, a)
      else localStorage.removeItem(ACCENT_KEY)
    } catch {
      /* ignore */
    }
  }, [])

  return { theme, setTheme, density, setDensity, palette, setPalette, accent, setAccent }
}
