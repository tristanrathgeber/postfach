// Chip-Akzent je Kategorie (email-agent-Taxonomie) als CSS-Variable — der Chip
// tönt Hintergrund UND Text daraus (color-mix), sodass die Farbe in BEIDEN
// Themes stimmt. Unbekannte Kategorien fallen auf Grau zurück.

const CHIP_ACCENT: Record<string, string> = {
  Newsletter: 'gray',
  'Newsletter-Interessant': 'sky',
  'Aktion-nötig': 'red',
  Rechnungen: 'amber',
  Bestellungen: 'orange',
  Entwicklung: 'violet',
  Verein: 'green',
  Termine: 'teal',
  Werbung: 'pink',
  Sonstiges: 'gray',
}

/** CSS-Variable des Kategorie-Akzents, z. B. `var(--chip-red)`. */
export function chipColor(category: string): string {
  return `var(--chip-${CHIP_ACCENT[category] ?? 'gray'})`
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
