import { useEffect, useRef } from 'react'

/** True, wenn das Event-Ziel ein Eingabefeld ist (dann keine globalen Single-Key-Shortcuts). */
export function isEditableTarget(e: KeyboardEvent): boolean {
  const el = e.target
  if (!(el instanceof HTMLElement)) return false
  if (el.isContentEditable) return true
  const tag = el.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
}

/** Globaler keydown-Listener; Handler bleibt über einen Ref immer aktuell. */
export function useGlobalKeydown(handler: (e: KeyboardEvent) => void): void {
  const ref = useRef(handler)
  ref.current = handler
  useEffect(() => {
    const listen = (e: KeyboardEvent) => ref.current(e)
    window.addEventListener('keydown', listen)
    return () => window.removeEventListener('keydown', listen)
  }, [])
}

/**
 * Merkt sich eine Präfix-Taste (z. B. "g") für Sequenzen wie "g dann i".
 * Gibt true zurück, wenn die aktuelle Taste eine Sequenz vervollständigt hat.
 */
export function createSequenceTracker(timeoutMs = 600) {
  let prefix: string | null = null
  let timer: ReturnType<typeof setTimeout> | null = null

  return {
    setPrefix(key: string) {
      prefix = key
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        prefix = null
      }, timeoutMs)
    },
    consume(expectedPrefix: string): boolean {
      const hit = prefix === expectedPrefix
      prefix = null
      if (timer) clearTimeout(timer)
      return hit
    },
  }
}
