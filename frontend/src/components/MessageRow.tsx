import { memo } from 'react'
import type { Summary } from '../lib/types'
import { formatListDate, msgKey } from '../lib/format'
import { folderLeaf } from '../lib/folders'
import { Chip } from './Chip'
import { ArchiveIcon, CheckIcon, MailIcon, MailOpenIcon, PaperclipIcon, TrashIcon } from './Icons'

type MessageRowProps = {
  msg: Summary
  index: number
  selected: boolean
  checked: boolean
  anyChecked: boolean
  /** Suche liefert Treffer aus allen Ordnern — dann den Ordner zeigen. */
  showFolder?: boolean
  onOpen: (msg: Summary) => void
  onArchive: (msg: Summary) => void
  onTrash: (msg: Summary) => void
  onToggleSeen: (msg: Summary) => void
  /** Auswahl togglen; mit range=true (Shift) bis zum letzten Anker erweitern. */
  onToggleCheck: (msg: Summary, range: boolean) => void
}

function QuickAction({
  title,
  onClick,
  children,
}: {
  title: string
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={(e) => {
        e.stopPropagation()
        onClick()
      }}
      className="rounded p-1 text-muted transition hover:bg-[#F1EFEA] hover:text-ink"
    >
      {children}
    </button>
  )
}

export const MessageRow = memo(function MessageRow({
  msg,
  index,
  selected,
  checked,
  anyChecked,
  showFolder = false,
  onOpen,
  onArchive,
  onTrash,
  onToggleSeen,
  onToggleCheck,
}: MessageRowProps) {
  const unread = !msg.seen
  return (
    <div
      data-msg={msgKey(msg)}
      role="button"
      tabIndex={-1}
      onClick={(e) => {
        // Shift-Klick erweitert die Auswahl statt zu öffnen; bei aktiver
        // Auswahl togglet jeder Klick (Triage-Modus wie in Gmail).
        if (e.shiftKey) onToggleCheck(msg, true)
        else if (anyChecked) onToggleCheck(msg, false)
        else onOpen(msg)
      }}
      className={`row-enter group relative cursor-pointer border-b border-hairline px-4 py-2.5 transition ${
        checked ? 'bg-[#E9EDFA]' : selected ? 'bg-[#EFF2FB]' : 'hover:bg-[#F8F7F4]'
      }`}
      style={{ animationDelay: `${Math.min(index, 15) * 22}ms` }}
    >
      {selected && !checked ? (
        <span className="absolute inset-y-0 left-0 w-[2px] bg-tinte" aria-hidden="true" />
      ) : null}

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          aria-label={checked ? 'Auswahl entfernen' : 'Auswählen'}
          aria-pressed={checked}
          title="Auswählen (x) · Shift-Klick für Bereich"
          onClick={(e) => {
            e.stopPropagation()
            onToggleCheck(msg, e.shiftKey)
          }}
          className={`flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded-full border transition ${
            checked
              ? 'border-tinte bg-tinte text-white'
              : anyChecked
                ? 'border-hairline bg-paper text-transparent hover:border-tinte'
                : 'border-hairline bg-paper text-transparent opacity-0 hover:border-tinte group-hover:opacity-100'
          }`}
        >
          <CheckIcon size={9} />
        </button>
        {unread ? <span className="h-[6px] w-[6px] shrink-0 rounded-full bg-unread" aria-label="Ungelesen" /> : null}
        <span className={`min-w-0 flex-1 truncate text-[13px] ${unread ? 'font-semibold' : ''}`}>
          {msg.from_name || msg.from_addr}
          {msg.thread_count > 1 ? (
            <span className="ml-1.5 font-mono text-[10.5px] font-normal text-muted" title={`${msg.thread_count} Mails im Gespräch`}>
              ({msg.thread_count})
            </span>
          ) : null}
        </span>
        <span className="flex shrink-0 items-center gap-1.5 text-muted group-hover:invisible">
          {showFolder && msg.folder !== 'INBOX' ? (
            <span className="max-w-[110px] truncate rounded bg-[#F1EFEA] px-1 font-mono text-[9.5px]">
              {folderLeaf(msg.folder)}
            </span>
          ) : null}
          {msg.has_attachments ? <PaperclipIcon size={12} /> : null}
          <time className="font-mono text-[10.5px]">{formatListDate(msg.date)}</time>
        </span>
      </div>

      <div className="mt-0.5 flex items-center gap-2 pl-[21px]">
        <p className="min-w-0 flex-1 truncate text-[12.5px]">
          <span className={unread ? 'font-medium' : ''}>{msg.subject || '(Kein Betreff)'}</span>
          {msg.snippet ? <span className="text-muted"> — {msg.snippet}</span> : null}
        </p>
        {msg.category ? <Chip category={msg.category} className="shrink-0" /> : null}
      </div>

      {/* Quick-Actions bei Hover */}
      <div className="absolute right-2 top-1.5 hidden items-center gap-0.5 rounded border border-hairline bg-surface px-0.5 py-px shadow-sm group-hover:flex">
        <QuickAction title="Archivieren (e)" onClick={() => onArchive(msg)}>
          <ArchiveIcon size={13} />
        </QuickAction>
        <QuickAction title="Papierkorb (#)" onClick={() => onTrash(msg)}>
          <TrashIcon size={13} />
        </QuickAction>
        <QuickAction title={unread ? 'Als gelesen markieren (u)' : 'Als ungelesen markieren (u)'} onClick={() => onToggleSeen(msg)}>
          {unread ? <MailOpenIcon size={13} /> : <MailIcon size={13} />}
        </QuickAction>
      </div>
    </div>
  )
})
