import { describe, expect, it } from 'vitest'
import { simplifyBody, wasTruncated } from './readerText'

describe('simplifyBody', () => {
  it('kappt am ersten Zitat-Marker und behält den Kopf', () => {
    const text = 'Danke, passt!\nVG Alex\n\n> Am 1.1. schrieb Martin:\n> Kommst du?'
    expect(simplifyBody(text)).toBe('Danke, passt!\nVG Alex')
  })

  it('Mail, die MIT einem Zitat beginnt → Volltext (nichts sinnvoll zu kürzen)', () => {
    const text = '> Am 1.1. schrieb X:\n> Hallo\nDanke, gut!'
    expect(simplifyBody(text)).toBe(text.trim())
  })

  it('leerer / marker-loser / newline-loser Text → getrimmter Volltext', () => {
    expect(simplifyBody('')).toBe('')
    expect(simplifyBody('Nur ein Satz, kein Zitat.')).toBe('Nur ein Satz, kein Zitat.')
    expect(simplifyBody('Eine Zeile ohne Umbruch')).toBe('Eine Zeile ohne Umbruch')
  })

  it('deutsche Attributionszeile „Am … schrieb Max Mustermann:" wird erkannt', () => {
    const text = 'Kurze Antwort.\n\nAm 01.01.2026 um 12:00 schrieb Max Mustermann:\n> Frage'
    expect(simplifyBody(text)).toBe('Kurze Antwort.')
  })

  it('„Von:" MITTEN im Fließtext ist KEIN Zitat-Marker (nur echte Header-Blöcke)', () => {
    const text = 'Rückmeldung zur Anfrage.\n\nVon: unserem Lieferanten kam nichts.\nBitte meldet euch.'
    // Kein An:/Gesendet: dahinter → legitimer Text bleibt erhalten
    expect(simplifyBody(text)).toBe(text.trim())
  })

  it('echter weitergeleiteter Header-Block (Von:/An:/Betreff:) wird gekappt', () => {
    const text = 'Zur Info weitergeleitet.\n\nVon: chef@x.de\nAn: team@x.de\nBetreff: Q3\n\nText der alten Mail'
    expect(simplifyBody(text)).toBe('Zur Info weitergeleitet.')
  })
})

describe('wasTruncated (Konsistenz-Wächter für den Hinweis)', () => {
  it('true nur, wenn simplifyBody wirklich kürzt', () => {
    expect(wasTruncated('Danke!\n> zitat\n> mehr')).toBe(true)
    // Fällt auf Volltext zurück → Hinweis darf NICHT „ausgeblendet" sagen
    expect(wasTruncated('> zitat\nmehr')).toBe(false)
    expect(wasTruncated('kein zitat')).toBe(false)
  })
})
