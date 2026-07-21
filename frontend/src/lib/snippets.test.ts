import { describe, expect, test } from 'vitest'
import { expandSnippet, matchAbbrev } from './snippets'

describe('expandSnippet', () => {
  test('nutzt den bekannten Anzeigenamen für {vorname}', () => {
    const names = new Map([['m.becker@web.example', 'Martin Becker']])
    expect(expandSnippet('Hallo {vorname}!', 'm.becker@web.example', names)).toBe('Hallo Martin!')
  })

  test('fällt ohne bekannten Namen auf den Local-Part zurück', () => {
    expect(expandSnippet('Hallo {vorname}!', 'sabine@web.example')).toBe('Hallo Sabine!')
  })

  test('Local-Part-Heuristik nimmt das erste Segment vor Punkt/Unterstrich/Bindestrich', () => {
    expect(expandSnippet('Hallo {vorname}!', 'lisa.mueller@web.example')).toBe('Hallo Lisa!')
  })

  test('leerer Vorname ohne Empfänger', () => {
    expect(expandSnippet('Hallo {vorname}!', undefined)).toBe('Hallo !')
  })

  test('Name aus der Map schlägt die Local-Part-Heuristik', () => {
    const names = new Map([['info@firma.example', 'Petra Sommer']])
    expect(expandSnippet('{vorname}', 'info@firma.example', names)).toBe('Petra')
  })

  test('{datum} wird als deutsches Datum ersetzt', () => {
    expect(expandSnippet('am {datum}', 'a@b.c')).toMatch(/^am \d{1,2}\.\d{1,2}\.\d{4}$/)
  })

  test('ersetzt mehrfach vorkommende Variablen', () => {
    const names = new Map([['a@b.c', 'Anna Anders']])
    expect(expandSnippet('{vorname} und {vorname}', 'a@b.c', names)).toBe('Anna und Anna')
  })

  test('Namens-Lookup ignoriert Groß/Kleinschreibung der Adresse', () => {
    // Reply-Header liefern Original-Case, Kontakte sind lowercase gespeichert.
    const names = new Map([['m.becker@web.example', 'Martin Becker']])
    expect(expandSnippet('Hallo {vorname}!', 'M.Becker@Web.example', names)).toBe('Hallo Martin!')
  })
})

describe('matchAbbrev', () => {
  test('findet ;kürzel am Textende', () => {
    expect(matchAbbrev('Hallo ;vg')).toEqual({ abbrev: 'vg', start: 6 })
  })

  test('kann Umlaute im Kürzel', () => {
    expect(matchAbbrev(';gruß')).toEqual({ abbrev: 'gruß', start: 0 })
  })

  test('kein Match ohne Semikolon direkt vor dem Wort', () => {
    expect(matchAbbrev('Hallo vg')).toBeNull()
    expect(matchAbbrev('Hallo ;vg ')).toBeNull()
  })
})
