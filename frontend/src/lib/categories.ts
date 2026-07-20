// Chip-Farben für die bekannten zehn Kategorien (email-agent-Taxonomie).
// Unbekannte Kategorien fallen auf Grau zurück — die Liste selbst bleibt dynamisch.

const FALLBACK = 'bg-gray-100 text-gray-700'

export const CHIP_STYLES: Record<string, string> = {
  Newsletter: 'bg-slate-100 text-slate-700',
  'Newsletter-Interessant': 'bg-sky-100 text-sky-700',
  'Aktion-nötig': 'bg-red-100 text-red-700',
  Rechnungen: 'bg-amber-100 text-amber-700',
  Bestellungen: 'bg-orange-100 text-orange-700',
  Entwicklung: 'bg-violet-100 text-violet-700',
  Verein: 'bg-green-100 text-green-700',
  Termine: 'bg-teal-100 text-teal-700',
  Werbung: 'bg-pink-100 text-pink-700',
  Sonstiges: FALLBACK,
}

export function chipStyle(category: string): string {
  return CHIP_STYLES[category] ?? FALLBACK
}

/** Sortierung der Kategorie-Ansichten in der Sidebar: bekannte zuerst in fester Reihenfolge, Rest alphabetisch. */
const KNOWN_ORDER = [
  'Aktion-nötig',
  'Termine',
  'Rechnungen',
  'Bestellungen',
  'Entwicklung',
  'Verein',
  'Newsletter-Interessant',
  'Newsletter',
  'Werbung',
  'Sonstiges',
]

export function sortCategories(categories: string[]): string[] {
  return [...categories].sort((a, b) => {
    const ia = KNOWN_ORDER.indexOf(a)
    const ib = KNOWN_ORDER.indexOf(b)
    if (ia !== -1 && ib !== -1) return ia - ib
    if (ia !== -1) return -1
    if (ib !== -1) return 1
    return a.localeCompare(b, 'de')
  })
}
