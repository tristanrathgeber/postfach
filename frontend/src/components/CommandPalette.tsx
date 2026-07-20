import { useEffect, useState } from 'react'
import { Command } from 'cmdk'

export type PaletteAction = {
  id: string
  label: string
  group: string
  shortcut?: string
  keywords?: string[]
  run: () => void
}

type CommandPaletteProps = {
  open: boolean
  onClose: () => void
  actions: PaletteAction[]
  onSearch: (q: string) => void
}

const GROUP_CLASS =
  '[&_[cmdk-group-heading]]:px-2.5 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:pt-2 ' +
  '[&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[9.5px] [&_[cmdk-group-heading]]:uppercase ' +
  '[&_[cmdk-group-heading]]:tracking-[0.1em] [&_[cmdk-group-heading]]:text-muted'

const ITEM_CLASS =
  'flex cursor-pointer items-center gap-2 rounded px-2.5 py-2 text-[13px] ' +
  'data-[selected=true]:bg-[#EFF2FB] data-[selected=true]:text-tinte'

export function CommandPalette({ open, onClose, actions, onSearch }: CommandPaletteProps) {
  const [value, setValue] = useState('')

  useEffect(() => {
    if (open) setValue('')
  }, [open])

  if (!open) return null

  // Gruppen in Einfüge-Reihenfolge (Aktionen, Ansichten, Konten)
  const groups: { name: string; items: PaletteAction[] }[] = []
  for (const a of actions) {
    const g = groups.find((x) => x.name === a.group)
    if (g) g.items.push(a)
    else groups.push({ name: a.group, items: [a] })
  }

  const query = value.trim()

  return (
    <div
      className="fade-in fixed inset-0 z-50 flex items-start justify-center bg-black/20 pt-[14vh]"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          // Auch native Propagation stoppen: Esc darf nur die Palette schließen,
          // nicht zusätzlich die globalen window-Listener (z. B. Composer) treffen.
          e.stopPropagation()
          onClose()
        }
      }}
    >
      <Command
        label="Befehle"
        className="w-[560px] max-w-[90vw] overflow-hidden rounded-lg border border-hairline bg-surface shadow-xl"
      >
        <Command.Input
          autoFocus
          value={value}
          onValueChange={setValue}
          placeholder="Befehl eingeben oder suchen …"
          className="w-full border-b border-hairline bg-transparent px-4 py-3 text-[14px] outline-none placeholder:text-muted"
        />
        <Command.List className="max-h-[340px] overflow-y-auto p-1.5">
          <Command.Empty className="px-3 py-6 text-center font-serif text-[16px] italic text-muted">
            Nichts gefunden.
          </Command.Empty>
          {groups.map((g) => (
            <Command.Group key={g.name} heading={g.name} className={GROUP_CLASS}>
              {g.items.map((a) => (
                <Command.Item
                  key={a.id}
                  value={`${a.id} ${a.label}`}
                  keywords={a.keywords}
                  onSelect={() => {
                    onClose()
                    a.run()
                  }}
                  className={ITEM_CLASS}
                >
                  <span className="min-w-0 flex-1 truncate">{a.label}</span>
                  {a.shortcut ? (
                    <kbd className="shrink-0 rounded border border-hairline bg-paper px-1.5 py-0.5 font-mono text-[10px] text-muted">
                      {a.shortcut}
                    </kbd>
                  ) : null}
                </Command.Item>
              ))}
            </Command.Group>
          ))}
          {query ? (
            <Command.Group heading="Suche" className={GROUP_CLASS} forceMount>
              <Command.Item
                forceMount
                value={`volltextsuche ${query}`}
                onSelect={() => {
                  onClose()
                  onSearch(query)
                }}
                className={ITEM_CLASS}
              >
                <span className="min-w-0 flex-1 truncate">Suchen nach: „{query}“</span>
                <kbd className="shrink-0 rounded border border-hairline bg-paper px-1.5 py-0.5 font-mono text-[10px] text-muted">
                  /
                </kbd>
              </Command.Item>
            </Command.Group>
          ) : null}
        </Command.List>
      </Command>
    </div>
  )
}
