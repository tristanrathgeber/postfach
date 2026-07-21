import { beforeEach, describe, expect, it } from 'vitest'
import { recordMouseAction } from './shortcutTeach'

// Leichtgewichtiges localStorage-Polyfill (kein jsdom nötig).
class MemoryStorage {
  private store = new Map<string, string>()
  getItem(k: string) {
    return this.store.has(k) ? this.store.get(k)! : null
  }
  setItem(k: string, v: string) {
    this.store.set(k, String(v))
  }
  clear() {
    this.store.clear()
  }
}

describe('recordMouseAction', () => {
  beforeEach(() => {
    ;(globalThis as unknown as { localStorage: MemoryStorage }).localStorage = new MemoryStorage()
  })

  it('lehrt genau einmal ab der dritten Wiederholung', () => {
    expect(recordMouseAction('archive')).toBeNull() // 1
    expect(recordMouseAction('archive')).toBeNull() // 2
    const hint = recordMouseAction('archive') // 3 → Hinweis
    expect(hint).toContain('e')
    expect(hint).toContain('archiviert')
    expect(recordMouseAction('archive')).toBeNull() // gelernt → nie wieder
    expect(recordMouseAction('archive')).toBeNull()
  })

  it('zählt Aktionen unabhängig', () => {
    recordMouseAction('archive')
    recordMouseAction('archive')
    expect(recordMouseAction('reply')).toBeNull() // reply erst bei 1
  })

  it('ignoriert unbekannte Aktionen', () => {
    expect(recordMouseAction('unbekannt')).toBeNull()
    expect(recordMouseAction('unbekannt')).toBeNull()
    expect(recordMouseAction('unbekannt')).toBeNull()
  })
})
