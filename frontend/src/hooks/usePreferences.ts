import { useCallback, useEffect, useState } from 'react'

export type Theme = 'system' | 'light' | 'dark'
export type Density = 'comfortable' | 'compact'

const THEME_KEY = 'postfach.theme'
const DENSITY_KEY = 'postfach.density'

function read<T extends string>(key: string, fallback: T, valid: readonly T[]): T {
  try {
    const v = localStorage.getItem(key)
    if (v && (valid as readonly string[]).includes(v)) return v as T
  } catch {
    // localStorage nicht verfügbar → Default
  }
  return fallback
}

/** Theme anwenden: light/dark setzen data-theme (überstimmt die Media-Query),
 * system entfernt es (dann greift prefers-color-scheme automatisch). */
function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'system') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', theme)
}

export function usePreferences() {
  const [theme, setThemeState] = useState<Theme>(() => read(THEME_KEY, 'system', ['system', 'light', 'dark']))
  const [density, setDensityState] = useState<Density>(() =>
    read(DENSITY_KEY, 'comfortable', ['comfortable', 'compact']),
  )

  useEffect(() => applyTheme(theme), [theme])

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

  return { theme, setTheme, density, setDensity }
}
