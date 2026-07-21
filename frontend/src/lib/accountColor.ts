// Stabile Akzentfarbe je Konto — deterministisch aus dem Namen, aus einer
// harmonischen Palette, die auf hellem UND dunklem Grund lesbar bleibt.
// Hilft, in der Unified Inbox die Herkunft auf einen Blick zu sehen.

// Mittlere Helligkeit gewählt, damit jeder Ton als kleiner Punkt auf hellem
// UND dunklem Papier (≥3:1) liest — die kühlen Töne sind bewusst aufgehellt.
const PALETTE = [
  '#4C93A6', // Petrol
  '#C08A3A', // Bernstein
  '#BC647E', // Altrosa
  '#8E7DC8', // Violett
  '#5CA166', // Grün
  '#6C89DC', // Blau
  '#C4744A', // Terrakotta
  '#6C93B6', // Stahlblau
]

export function accountColor(name: string): string {
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return PALETTE[h % PALETTE.length]
}
