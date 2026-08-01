import { beforeEach, describe, expect, it } from 'vitest'
import { overlayOpen, pushOverlay, resetOverlays } from './overlay'

describe('overlay-Registrierung', () => {
  beforeEach(resetOverlays)

  it('meldet ohne offenen Dialog nichts', () => {
    expect(overlayOpen()).toBe(false)
  })

  it('erkennt einen offenen Dialog und dessen Schließen', () => {
    const close = pushOverlay()
    expect(overlayOpen()).toBe(true)
    close()
    expect(overlayOpen()).toBe(false)
  })

  it('bleibt aktiv, solange noch ein Dialog offen ist (Überlagerung)', () => {
    // Anhang-Vorschau über Reader über Palette: erst der LETZTE gibt die
    // Tastenkürzel wieder frei.
    const first = pushOverlay()
    const second = pushOverlay()
    first()
    expect(overlayOpen()).toBe(true)
    second()
    expect(overlayOpen()).toBe(false)
  })

  it('zählt doppeltes Schließen nicht doppelt', () => {
    // React kann Effekt-Aufräumer in StrictMode mehrfach auslösen — das darf
    // den Zähler nicht unter null drücken und fremde Dialoge freigeben.
    const closeA = pushOverlay()
    const closeB = pushOverlay()
    closeA()
    closeA()
    closeA()
    expect(overlayOpen()).toBe(true) // B ist noch offen
    closeB()
    expect(overlayOpen()).toBe(false)
  })

  it('geht nie unter null', () => {
    const close = pushOverlay()
    close()
    close()
    expect(overlayOpen()).toBe(false)
    const next = pushOverlay()
    expect(overlayOpen()).toBe(true)
    next()
    expect(overlayOpen()).toBe(false)
  })
})
