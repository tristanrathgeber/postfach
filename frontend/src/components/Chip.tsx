import { chipStyle } from '../lib/categories'

/** Kategorie-Chip — kleiner "Tintenstempel": Mono, Uppercase, weich getönt. */
export function Chip({ category, className = '' }: { category: string; className?: string }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-[3px] px-1.5 py-px font-mono text-[9px] font-medium uppercase tracking-[0.08em] ${chipStyle(category)} ${className}`}
    >
      {category}
    </span>
  )
}
