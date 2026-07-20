import type { ReactNode } from 'react'

/** 3-Spalten-Layout: Sidebar (220px) · Liste (380px) · Reader (flexibel, min-w-0)
    + optionale rechte Seitenleiste (Emilia). Unter ~900px scrollt der Shell
    horizontal statt Spalten zu quetschen. */
export function AppShell({
  sidebar,
  list,
  reader,
  aside,
}: {
  sidebar: ReactNode
  list: ReactNode
  reader: ReactNode
  aside?: ReactNode
}) {
  return (
    <div className="h-full overflow-x-auto">
      <div className="flex h-full min-w-[900px]">
        {sidebar}
        {list}
        {reader}
        {aside}
      </div>
    </div>
  )
}
