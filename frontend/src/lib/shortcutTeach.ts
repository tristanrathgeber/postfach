// Behutsames Shortcut-Teaching: führt jemand eine Aktion wiederholt PER MAUS aus,
// blendet Postfach EINMAL einen Tastatur-Tipp ein — danach nie wieder für diese
// Aktion. Kein Nagging. Zustand in localStorage (Zähler + gelernte Aktionen).

const STORAGE_KEY = 'postfach.shortcut-teach.v1'
const TEACH_AT = 3 // ab der dritten Maus-Wiederholung

/** Aktion (interner Schlüssel) → (Taste, was sie tut) für den Hinweis-Text. */
export const SHORTCUT_HINTS: Record<string, { key: string; verb: string }> = {
  archive: { key: 'e', verb: 'archiviert' },
  reply: { key: 'r', verb: 'antwortet' },
  forward: { key: 'f', verb: 'leitet weiter' },
  trash: { key: '#', verb: 'in den Papierkorb' },
  later: { key: 'z', verb: 'legt später vor' },
  seen: { key: 'u', verb: 'schaltet gelesen/ungelesen' },
}

type State = { counts: Record<string, number>; learned: string[] }

function read(): State {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<State>
      return { counts: parsed.counts ?? {}, learned: parsed.learned ?? [] }
    }
  } catch {
    // localStorage nicht verfügbar/kaputt — ohne Teaching weiterlaufen.
  }
  return { counts: {}, learned: [] }
}

function write(state: State): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // ignorieren — Teaching ist reiner Komfort
  }
}

/**
 * Eine per Maus ausgelöste Aktion melden. Gibt den anzuzeigenden Hinweistext
 * zurück, wenn jetzt (genau einmal) getippt werden soll — sonst null.
 */
export function recordMouseAction(action: string): string | null {
  const hint = SHORTCUT_HINTS[action]
  if (!hint) return null
  const state = read()
  if (state.learned.includes(action)) return null
  const count = (state.counts[action] ?? 0) + 1
  state.counts[action] = count
  if (count >= TEACH_AT) {
    state.learned.push(action)
    write(state)
    return `Tipp: Taste „${hint.key}" ${hint.verb} — schneller als klicken.`
  }
  write(state)
  return null
}
