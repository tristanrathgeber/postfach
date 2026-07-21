import { chipColor } from '../lib/categories'

/** Kategorie-Chip — kleiner "Tintenstempel": Mono, Uppercase, weich getönt.
 * BG = Akzent bei ~16 % über dem Papier → stimmt in hellem UND dunklem Theme. */
export function Chip({ category, className = '' }: { category: string; className?: string }) {
  const c = chipColor(category)
  return (
    <span
      style={{ color: c, backgroundColor: `color-mix(in srgb, ${c} 16%, transparent)` }}
      className={`inline-block whitespace-nowrap rounded-[3px] px-1.5 py-px font-mono text-[9px] font-medium uppercase tracking-[0.08em] ${className}`}
    >
      {category}
    </span>
  )
}
