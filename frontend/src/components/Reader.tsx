import { useQuery } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import type { Detail, MsgRef } from '../lib/types'
import { formatFullDate, formatSize } from '../lib/format'
import { Chip } from './Chip'
import { EmptyState } from './EmptyState'
import { HtmlMailFrame } from './HtmlMailFrame'
import { ArchiveIcon, DownloadIcon, MailIcon, MailOpenIcon, PaperclipIcon, ReplyIcon, TrashIcon } from './Icons'

type ReaderProps = {
  opened: MsgRef | null
  imagesEnabled: boolean
  onEnableImages: () => void
  onReply: (detail: Detail) => void
  onArchive: (detail: Detail) => void
  onTrash: (detail: Detail) => void
  onToggleSeen: (detail: Detail) => void
}

function ActionButton({
  label,
  hint,
  onClick,
  children,
}: {
  label: string
  hint: string
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={`${label} (${hint})`}
      className="flex items-center gap-1.5 rounded border border-hairline bg-surface px-2.5 py-1 text-[12px] transition hover:border-tinte hover:text-tinte"
    >
      {children}
      {label}
    </button>
  )
}

function AddressLine({ label, value }: { label: string; value: string }) {
  return (
    <p className="min-w-0 truncate text-[12px] text-muted">
      <span className="font-mono text-[10.5px] uppercase tracking-wide">{label}</span>{' '}
      <span className="font-mono text-[11.5px]">{value}</span>
    </p>
  )
}

export function Reader({ opened, imagesEnabled, onEnableImages, onReply, onArchive, onTrash, onToggleSeen }: ReaderProps) {
  const detailQuery = useQuery({
    queryKey: ['message', opened?.account, opened?.folder, opened?.uid],
    queryFn: () => api.message(opened!.account, opened!.uid, opened!.folder),
    enabled: opened !== null,
  })

  if (!opened) {
    return (
      <section className="h-full min-w-0 flex-1 bg-paper">
        <EmptyState title="Nichts geöffnet." subline="j/k wählen · Enter öffnen · ⌘K Befehle" />
      </section>
    )
  }

  if (detailQuery.isError) {
    return (
      <section className="h-full min-w-0 flex-1 bg-paper">
        <EmptyState title="Nachricht nicht ladbar." subline={errText(detailQuery.error)} />
      </section>
    )
  }

  const detail = detailQuery.data
  if (!detail) {
    return (
      <section className="flex h-full min-w-0 flex-1 items-center justify-center bg-paper">
        <p className="fade-in font-mono text-[11px] text-muted">Lädt …</p>
      </section>
    )
  }

  const blockedImages = detail.body_html_images !== null
  const html = imagesEnabled && detail.body_html_images !== null ? detail.body_html_images : detail.body_html

  return (
    <section className="flex h-full min-w-0 flex-1 flex-col bg-paper">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <article className="fade-in mx-auto max-w-[780px] px-8 py-6">
          {/* Kopf */}
          <header className="border-b border-hairline pb-4">
            <div className="flex items-start gap-3">
              <h1 className="min-w-0 flex-1 text-[20px] font-semibold leading-snug">
                {detail.subject || '(Kein Betreff)'}
              </h1>
              {detail.category ? <Chip category={detail.category} className="mt-1 shrink-0" /> : null}
            </div>
            <div className="mt-3 space-y-0.5">
              <p className="min-w-0 truncate text-[13px]">
                <span className="font-medium">{detail.from_name || detail.from_addr}</span>{' '}
                <span className="font-mono text-[11.5px] text-muted">&lt;{detail.from_addr}&gt;</span>
              </p>
              {detail.to.length > 0 ? <AddressLine label="An" value={detail.to.join(', ')} /> : null}
              {detail.cc.length > 0 ? <AddressLine label="CC" value={detail.cc.join(', ')} /> : null}
              <p className="font-mono text-[11px] text-muted">{formatFullDate(detail.date)}</p>
            </div>

            {/* Aktionsleiste */}
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <ActionButton label="Antworten" hint="r" onClick={() => onReply(detail)}>
                <ReplyIcon size={13} />
              </ActionButton>
              <ActionButton label="Archivieren" hint="e" onClick={() => onArchive(detail)}>
                <ArchiveIcon size={13} />
              </ActionButton>
              <ActionButton label="Papierkorb" hint="#" onClick={() => onTrash(detail)}>
                <TrashIcon size={13} />
              </ActionButton>
              <ActionButton label={detail.seen ? 'Ungelesen' : 'Gelesen'} hint="u" onClick={() => onToggleSeen(detail)}>
                {detail.seen ? <MailIcon size={13} /> : <MailOpenIcon size={13} />}
              </ActionButton>
              {detail.attachments.length > 0 ? (
                <span className="ml-auto flex items-center gap-1 font-mono text-[11px] text-muted">
                  <PaperclipIcon size={12} />
                  {detail.attachments.length} {detail.attachments.length === 1 ? 'Anhang' : 'Anhänge'}
                </span>
              ) : null}
            </div>
          </header>

          {/* Banner: blockierte externe Bilder */}
          {blockedImages && !imagesEnabled ? (
            <div className="mt-4 flex items-center gap-2 rounded border border-hairline bg-surface px-3 py-1.5">
              <span className="font-mono text-[11px] text-muted">Externe Bilder blockiert</span>
              <span className="flex-1" />
              <button
                type="button"
                onClick={onEnableImages}
                className="text-[12px] font-medium text-tinte transition hover:underline"
              >
                Bilder laden
              </button>
            </div>
          ) : null}

          {/* Inhalt */}
          <div className="mt-4 rounded border border-hairline bg-surface px-5 py-4">
            {html !== null ? (
              <HtmlMailFrame html={html} />
            ) : (
              <pre className="whitespace-pre-wrap break-words font-sans text-[14px] leading-relaxed">
                {detail.body_text}
              </pre>
            )}
          </div>

          {/* Anhänge */}
          {detail.attachments.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {detail.attachments.map((a) => (
                <a
                  key={a.index}
                  href={api.attachmentUrl(detail.account, detail.uid, a.index, detail.folder)}
                  download={a.filename}
                  className="flex items-center gap-1.5 rounded border border-hairline bg-surface px-2.5 py-1.5 text-[12px] transition hover:border-tinte hover:text-tinte"
                >
                  <DownloadIcon size={13} />
                  <span className="max-w-[220px] truncate">{a.filename}</span>
                  <span className="font-mono text-[10px] text-muted">{formatSize(a.size)}</span>
                </a>
              ))}
            </div>
          ) : null}
        </article>
      </div>
    </section>
  )
}
