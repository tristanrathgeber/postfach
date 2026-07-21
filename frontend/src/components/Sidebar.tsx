import { useState } from 'react'
import type { Account, AccountStatus } from '../lib/types'
import { sameView, type View } from '../lib/view'
import { ALL_ACCOUNTS } from '../hooks/useMailData'
import { ChevronDownIcon, ChevronRightIcon, GearIcon } from './Icons'
import { formatListDate } from '../lib/format'

export type CategoryEntry = { name: string; count: number }

type SidebarProps = {
  accounts: Account[]
  accountSel: string
  onSelectAccount: (name: string) => void
  view: View
  onSelectView: (view: View) => void
  categories: CategoryEntry[]
  inboxCount: number
  unreadCount: number
  draftsCount: number
  outboxCount: number
  remindersCount: number
  remindersDue: number
  subscriptionsCount: number
  screenerCount: number
  folders: string[]
  /** Watcher-Verbindungsstatus je Konto (leer, solange kein Watcher läuft — z. B. Demo). */
  status: Record<string, AccountStatus>
  onOpenSettings: () => void
}

function NavRow({
  label,
  count,
  active,
  onClick,
  indent = false,
}: {
  label: string
  count?: number
  active: boolean
  onClick: () => void
  indent?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-2 rounded px-2 py-[5px] text-left text-[13px] transition ${
        indent ? 'pl-6' : ''
      } ${active ? 'bg-[#EBEEF9] font-medium text-tinte' : 'text-ink hover:bg-[#F1EFEA]'}`}
    >
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {count !== undefined && count > 0 ? (
        <span className={`shrink-0 font-mono text-[10px] ${active ? 'text-tinte' : 'text-muted'}`}>{count}</span>
      ) : null}
    </button>
  )
}

type FolderNode = { name: string; full: string; children: FolderNode[] }

function buildFolderTree(folders: string[]): FolderNode[] {
  const roots: FolderNode[] = []
  const byPath = new Map<string, FolderNode>()
  for (const full of [...folders].sort((a, b) => a.localeCompare(b, 'de'))) {
    if (full === 'INBOX') continue // die Inbox-Ansicht oben deckt das ab
    const parts = full.split('/')
    const display = parts[0] === 'INBOX' ? parts.slice(1) : parts
    if (display.length === 0) continue
    let list = roots
    let path = parts[0] === 'INBOX' ? 'INBOX' : ''
    for (const part of display) {
      path = path ? `${path}/${part}` : part
      let node = byPath.get(path)
      if (!node) {
        node = { name: part, full: path, children: [] }
        byPath.set(path, node)
        list.push(node)
      }
      list = node.children
    }
  }
  // Hauptablage (INBOX/…) zuerst, dann übrige Wurzeln (Archiv, Gelöscht, …)
  return [
    ...roots.filter((n) => n.full.startsWith('INBOX/')),
    ...roots.filter((n) => !n.full.startsWith('INBOX/')),
  ]
}

function FolderTree({
  nodes,
  depth,
  view,
  onSelectView,
  expanded,
  onToggle,
}: {
  nodes: FolderNode[]
  depth: number
  view: View
  onSelectView: (view: View) => void
  expanded: ReadonlySet<string>
  onToggle: (path: string) => void
}) {
  return (
    <>
      {nodes.map((node) => {
        const hasChildren = node.children.length > 0
        const isOpen = expanded.has(node.full)
        const active = sameView(view, { kind: 'folder', folder: node.full })
        return (
          <div key={node.full}>
            <button
              type="button"
              onClick={() => onSelectView({ kind: 'folder', folder: node.full })}
              className={`flex w-full items-center gap-1 rounded px-2 py-[5px] text-left text-[13px] transition ${
                active ? 'bg-[#EBEEF9] font-medium text-tinte' : 'text-ink hover:bg-[#F1EFEA]'
              }`}
              style={{ paddingLeft: `${16 + depth * 14}px` }}
            >
              {hasChildren ? (
                <span
                  role="button"
                  aria-label={isOpen ? `${node.name} einklappen` : `${node.name} ausklappen`}
                  onClick={(e) => {
                    e.stopPropagation()
                    onToggle(node.full)
                  }}
                  className="-ml-1 rounded p-0.5 text-muted hover:bg-[#E5E2DB]"
                >
                  {isOpen ? <ChevronDownIcon size={11} /> : <ChevronRightIcon size={11} />}
                </span>
              ) : null}
              <span className="min-w-0 flex-1 truncate">{node.name}</span>
            </button>
            {hasChildren && isOpen ? (
              <FolderTree
                nodes={node.children}
                depth={depth + 1}
                view={view}
                onSelectView={onSelectView}
                expanded={expanded}
                onToggle={onToggle}
              />
            ) : null}
          </div>
        )
      })}
    </>
  )
}

export function Sidebar({
  accounts,
  accountSel,
  onSelectAccount,
  view,
  onSelectView,
  categories,
  inboxCount,
  unreadCount,
  draftsCount,
  outboxCount,
  remindersCount,
  remindersDue,
  subscriptionsCount,
  screenerCount,
  folders,
  status,
  onOpenSettings,
}: SidebarProps) {
  // Standardmäßig AUSGEKLAPPT — der eingeklappte Mini-Schalter war in der
  // Praxis nicht auffindbar (Nutzer-Feedback).
  const [foldersOpen, setFoldersOpen] = useState(true)
  // Unterordner-Äste (z. B. Gelöscht/…) standardmäßig zu
  const [expandedFolders, setExpandedFolders] = useState<ReadonlySet<string>>(new Set())
  const allSelected = accountSel === ALL_ACCOUNTS

  const toggleFolder = (path: string) =>
    setExpandedFolders((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })

  return (
    <aside className="flex h-full w-[220px] shrink-0 flex-col border-r border-hairline bg-paper">
      <div className="px-4 pb-2 pt-4">
        <h1 className="font-serif text-[22px] italic leading-none tracking-tight">Postfach</h1>
      </div>

      {/* Kontoumschalter */}
      <div className="px-2 pb-1 pt-2">
        <p className="px-2 pb-1 font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Konten</p>
        <NavRow label="Alle Konten" active={allSelected} onClick={() => onSelectAccount(ALL_ACCOUNTS)} />
        {accounts.map((a) => (
          <button
            key={a.name}
            type="button"
            onClick={() => onSelectAccount(a.name)}
            className={`w-full rounded px-2 py-[5px] text-left transition ${
              accountSel === a.name ? 'bg-[#EBEEF9]' : 'hover:bg-[#F1EFEA]'
            }`}
          >
            <span className={`flex items-center gap-1.5 truncate text-[13px] ${accountSel === a.name ? 'font-medium text-tinte' : 'text-ink'}`}>
              {a.name}
              {status[a.name] ? (
                <span
                  title={
                    status[a.name].connected
                      ? `Verbunden seit ${formatListDate(status[a.name].since ?? '')}`
                      : `Getrennt seit ${formatListDate(status[a.name].since ?? '')}${status[a.name].last_error ? ` — ${status[a.name].last_error}` : ''}`
                  }
                  aria-label={status[a.name].connected ? 'Verbunden' : 'Getrennt'}
                  className={`h-[7px] w-[7px] shrink-0 rounded-full ${status[a.name].connected ? 'bg-[#4C8A55]' : 'bg-[#B4483C]'}`}
                />
              ) : null}
            </span>
            <span className="block truncate font-mono text-[10px] text-muted">{a.address}</span>
            {status[a.name] && !status[a.name].connected ? (
              <span className="block truncate font-mono text-[10px] text-[#B4483C]">
                getrennt seit {formatListDate(status[a.name].since ?? '')} — verbinde neu …
              </span>
            ) : null}
          </button>
        ))}
      </div>

      <div className="mx-4 my-2 border-t border-hairline" />

      {/* Ansichten */}
      <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
        <NavRow label="Inbox" count={inboxCount} active={sameView(view, { kind: 'inbox' })} onClick={() => onSelectView({ kind: 'inbox' })} />
        <NavRow
          label="Ungelesen"
          count={unreadCount}
          active={sameView(view, { kind: 'unread' })}
          onClick={() => onSelectView({ kind: 'unread' })}
        />
        <NavRow
          label="Entwürfe"
          count={draftsCount}
          active={sameView(view, { kind: 'drafts' })}
          onClick={() => onSelectView({ kind: 'drafts' })}
        />
        {outboxCount > 0 ? (
          <NavRow
            label="Ausgang"
            count={outboxCount}
            active={sameView(view, { kind: 'outbox' })}
            onClick={() => onSelectView({ kind: 'outbox' })}
          />
        ) : null}
        {remindersCount > 0 ? (
          <NavRow
            label={remindersDue > 0 ? `Wiedervorlage — ${remindersDue} fällig` : 'Wiedervorlage'}
            count={remindersCount}
            active={sameView(view, { kind: 'reminders' })}
            onClick={() => onSelectView({ kind: 'reminders' })}
          />
        ) : null}

        <p className="px-2 pb-1 pt-3 font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Hygiene</p>
        <NavRow
          label="Abos"
          count={subscriptionsCount}
          active={sameView(view, { kind: 'subscriptions' })}
          onClick={() => onSelectView({ kind: 'subscriptions' })}
        />
        <NavRow
          label="Screener"
          count={screenerCount}
          active={sameView(view, { kind: 'screener' })}
          onClick={() => onSelectView({ kind: 'screener' })}
        />

        {categories.length > 0 ? (
          <>
            <p className="px-2 pb-1 pt-3 font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Kategorien</p>
            {categories.map((c) => (
              <NavRow
                key={c.name}
                label={c.name}
                count={c.count}
                active={sameView(view, { kind: 'category', category: c.name })}
                onClick={() => onSelectView({ kind: 'category', category: c.name })}
              />
            ))}
          </>
        ) : null}

        {/* Ordner: ausgeklappt per Default, große Klickfläche zum Einklappen.
            Bei "Alle Konten" gibt es keine Ordnerliste (/api/folders braucht
            ein konkretes Konto) — dann steht hier ein Hinweis statt Nichts. */}
        {!allSelected ? (
          <div className="pt-3">
            <button
              type="button"
              onClick={() => setFoldersOpen((v) => !v)}
              className="flex w-full items-center gap-1.5 rounded px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted transition hover:bg-[#F1EFEA]"
              title={foldersOpen ? 'Ordner einklappen' : 'Ordner ausklappen'}
            >
              {foldersOpen ? <ChevronDownIcon size={12} /> : <ChevronRightIcon size={12} />}
              Ordner
              <span className="ml-auto text-[9px] normal-case tracking-normal">{folders.length}</span>
            </button>
            {foldersOpen ? (
              <FolderTree
                nodes={buildFolderTree(folders)}
                depth={0}
                view={view}
                onSelectView={onSelectView}
                expanded={expandedFolders}
                onToggle={toggleFolder}
              />
            ) : null}
          </div>
        ) : (
          <div className="pt-3">
            <p className="px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
              Ordner
            </p>
            <p className="px-2 text-[12px] leading-snug text-muted">
              Konto links wählen, um dessen Ordner zu sehen.
            </p>
          </div>
        )}
      </nav>

      <footer className="flex items-center gap-2 border-t border-hairline px-3 py-2">
        <button
          type="button"
          onClick={onOpenSettings}
          title="Einstellungen (Signaturen & Snippets)"
          aria-label="Einstellungen"
          className="rounded p-1 text-muted transition hover:bg-[#F1EFEA] hover:text-tinte"
        >
          <GearIcon size={14} />
        </button>
        <p className="font-mono text-[10px] text-muted">⌘K Befehle</p>
      </footer>
    </aside>
  )
}
