import { useEffect } from 'react'

/**
 * „Liegt gerade ein Dialog über der App?" — eine Stelle, die alle fragen können.
 *
 * Ohne das musste jede Tastatur-Stelle einzeln wissen, welche Dialoge es gibt
 * (`if (paletteOpen || composer || settingsOpen) return`). Neue Dialoge wurden
 * dabei vergessen: Bei offenem „Über Postfach" oder „Modell-Assistent" hat
 * `e` weiterhin die Mail DAHINTER archiviert und `#` sie in den Papierkorb
 * geschoben — sichtbar war davon nichts.
 *
 * Bewusst ein Zähler (kein Boolean): Dialoge können sich überlagern (Vorschau
 * über Reader über Palette). Erst wenn der letzte zu ist, greifen die Kürzel
 * wieder. Bewusst Modul-Zustand statt Context: die Tastatur-Handler fragen zum
 * EREIGNIS-Zeitpunkt, nicht beim Rendern — ein Context-Wert wäre dort veraltet.
 */
let openCount = 0

/** Dialog anmelden. Gibt die Abmeldung zurück (mehrfach aufrufbar, zählt einmal). */
export function pushOverlay(): () => void {
  openCount += 1
  let released = false
  return () => {
    if (released) return
    released = true
    openCount = Math.max(0, openCount - 1)
  }
}

/** Ist mindestens ein Dialog offen? */
export function overlayOpen(): boolean {
  return openCount > 0
}

/** Nur für Tests — setzt den Zähler zurück. */
export function resetOverlays(): void {
  openCount = 0
}

/** React-Fassung: meldet an, solange die Komponente steht. */
export function useOverlay(active = true): void {
  useEffect(() => {
    if (!active) return
    return pushOverlay()
  }, [active])
}
