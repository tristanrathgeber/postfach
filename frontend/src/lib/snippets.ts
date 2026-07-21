/**
 * Snippet-Variablen: {vorname} = Vorname des ersten Empfängers, {datum} = heute (de-DE).
 * Der Vorname kommt bevorzugt aus `names` (Adresse → Anzeigename, z. B. aus dem
 * Reply-Kontext oder einem Kontakte-Pick), sonst aus dem Local-Part der Adresse.
 * Adress-Lookups sind case-insensitiv — Header liefern Original-Case, Kontakte lowercase.
 */
export function expandSnippet(text: string, firstTo: string | undefined, names?: ReadonlyMap<string, string>): string {
  let vorname = ''
  const known = firstTo ? names?.get(firstTo.toLowerCase()) : undefined
  if (known) {
    vorname = known.split(/\s+/)[0] ?? ''
  } else if (firstTo) {
    const local = firstTo.split('@')[0] ?? ''
    const first = local.split(/[._-]/)[0] ?? ''
    vorname = first ? first.charAt(0).toUpperCase() + first.slice(1) : ''
  }
  return text.replace(/\{vorname\}/g, vorname).replace(/\{datum\}/g, new Date().toLocaleDateString('de-DE'))
}

/** `;kürzel` unmittelbar vor dem Caret — Unicode-Buchstaben inklusive (;gruß). */
export function matchAbbrev(beforeCaret: string): { abbrev: string; start: number } | null {
  const m = beforeCaret.match(/;([\p{L}\p{N}_]+)$/u)
  if (!m || m.index === undefined) return null
  return { abbrev: m[1], start: m.index }
}
