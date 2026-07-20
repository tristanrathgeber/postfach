/** Leere Zustände: große Newsreader-Kursive + kurze Mono-Subline. */
export function EmptyState({ title, subline }: { title: string; subline?: string }) {
  return (
    <div className="fade-in flex h-full flex-col items-center justify-center gap-3 px-8 text-center">
      <p className="font-serif text-[26px] italic leading-snug text-ink">{title}</p>
      {subline ? <p className="font-mono text-[11px] text-muted">{subline}</p> : null}
    </div>
  )
}
