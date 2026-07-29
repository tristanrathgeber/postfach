import { describe, expect, it } from 'vitest'
import { openableHref } from './mailLink'

describe('openableHref', () => {
  it('lässt normale Web- und Mail-Links durch', () => {
    expect(openableHref('https://example.org/x?y=1')).toBe('https://example.org/x?y=1')
    expect(openableHref('http://example.org/')).toBe('http://example.org/')
    expect(openableHref('mailto:a@b.de')).toBe('mailto:a@b.de')
  })

  it('blockt gefährliche Schemata', () => {
    for (const href of [
      'javascript:alert(1)',
      'data:text/html,<script>alert(1)</script>',
      'file:///etc/passwd',
      'vbscript:msgbox(1)',
      // Groß-/Kleinschreibung und Leerzeichen dürfen den Filter nicht umgehen
      '  JavaScript:alert(1)',
    ]) {
      expect(openableHref(href), href).toBeNull()
    }
  })

  it('verwirft relative und leere Links (in einer Mail ohne Bezugspunkt)', () => {
    for (const href of ['/pfad', 'seite.html', '', '   ', null, undefined]) {
      expect(openableHref(href)).toBeNull()
    }
  })
})
