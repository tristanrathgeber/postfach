import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import type { Detail, MsgRef, ThreadMail } from '../lib/types'
import { formatFullDate, formatListDate, formatSize } from '../lib/format'
import { TimePresetMenu } from './TimePresetMenu'
import { folderLeaf, isSpamFolder } from '../lib/folders'
import { Chip } from './Chip'
import { EmptyState } from './EmptyState'
import { HtmlMailFrame } from './HtmlMailFrame'
import { InviteCard } from './InviteCard'
import { EntityChips } from './EntityChips'
import { useToast } from './Toast'
import { AlertIcon, ArchiveIcon, ClockIcon, DownloadIcon, ForwardIcon, MailIcon, MailOpenIcon, PaperclipIcon, ReplyIcon, SparklesIcon, SpinnerIcon, TrashIcon } from './Icons'
import type { InviteResponse } from '../lib/types'
import { recordMouseAction } from '../lib/shortcutTeach'

type ReaderProps = {
  opened: MsgRef | null
  imagesEnabled: boolean
  onEnableImages: () => void
  onReply: (detail: Detail) => void
  onForward: (detail: Detail) => void
  onArchive: (detail: Detail) => void
  onTrash: (detail: Detail) => void
  onToggleSeen: (detail: Detail) => void
  /** spam=true → in den Spam-Ordner; false → zurück in die Inbox. */
  onToggleSpam: (detail: Detail, spam: boolean) => void
  /** Mail bis <iso> wegschlafen (Ordner „Später", Rückkehr ungelesen). */
  onSnooze: (detail: Detail, until: string) => void
  /** Alle konfigurierten Kategorien fürs Korrektur-Menü. */
  categories: string[]
  onChangeCategory: (detail: Detail, category: string) => void
  /** Klick auf eine Faden-Mail: im Reader öffnen. */
  onOpenThreadMail: (mail: ThreadMail) => void
  /** Globaler KI-Schalter — aus blendet „Zusammenfassen" aus. */
  aiEnabled?: boolean
  /** Faden-Triage (Gesendet-Kopien sind bereits herausgefiltert). */
  onThreadAction: (mails: ThreadMail[], action: 'archive' | 'trash') => void
}

function ActionButton({
  label,
  hint,
  onClick,
  children,
}: {
  label: string
  hint?: string
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={hint ? `${label} (${hint})` : label}
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

function ThreadRail({
  thread,
  current,
  aiEnabled,
  onOpen,
  onAction,
}: {
  thread: ThreadMail[]
  current: MsgRef
  aiEnabled: boolean
  onOpen: (mail: ThreadMail) => void
  onAction: (mails: ThreadMail[], action: 'archive' | 'trash') => void
}) {
  // Gesendet-Kopien räumt man nicht weg — das Wissen liefert der Server.
  const triagable = thread.filter((m) => !m.is_sent)
  // Zusammenfassung NUR auf Klick (nie automatisch) — pro geöffneter Mail zurückgesetzt.
  const [summary, setSummary] = useState<string | null>(null)
  const currentKey = `${current.account}:${current.folder}:${current.uid}`
  useEffect(() => setSummary(null), [currentKey])
  const summaryMutation = useMutation({
    mutationFn: () => api.threadSummary({ account: current.account, folder: current.folder, uid: current.uid }),
    onSuccess: (result) => setSummary(result.summary),
    onError: (e) => setSummary(`Zusammenfassung fehlgeschlagen: ${errText(e)}`),
  })
  return (
    <section className="mt-4 rounded border border-hairline bg-surface" aria-label="Konversation">
      <header className="flex items-center gap-2 border-b border-hairline px-3 py-1.5">
        <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
          Konversation ({thread.length})
        </span>
        <span className="flex-1" />
        {aiEnabled && thread.length >= 3 && summary === null ? (
          <button
            type="button"
            onClick={() => summaryMutation.mutate()}
            disabled={summaryMutation.isPending}
            title="Emilia fasst den Faden zusammen (lokal, nur auf Klick)"
            className="flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[10.5px] text-muted transition hover:bg-[#F1EFEA] hover:text-tinte disabled:opacity-50"
          >
            {summaryMutation.isPending ? <SpinnerIcon size={10} /> : <SparklesIcon size={10} />}
            Zusammenfassen
          </button>
        ) : null}
        {triagable.length > 0 ? (
          <>
            <button
              type="button"
              onClick={() => onAction(triagable, 'archive')}
              title="Alle empfangenen Mails des Fadens archivieren"
              className="rounded px-1.5 py-0.5 font-mono text-[10.5px] text-muted transition hover:bg-[#F1EFEA] hover:text-tinte"
            >
              Faden archivieren
            </button>
            <button
              type="button"
              onClick={() => onAction(triagable, 'trash')}
              title="Alle empfangenen Mails des Fadens in den Papierkorb"
              className="rounded px-1.5 py-0.5 font-mono text-[10.5px] text-muted transition hover:bg-[#F1EFEA] hover:text-red-700"
            >
              Papierkorb
            </button>
          </>
        ) : null}
      </header>
      {summary !== null ? (
        <div className="flex items-start gap-2 border-b border-hairline bg-paper px-3 py-2">
          <p className="min-w-0 flex-1 whitespace-pre-wrap text-[12px] leading-relaxed text-ink">{summary}</p>
          <button
            type="button"
            onClick={() => setSummary(null)}
            aria-label="Zusammenfassung schließen"
            className="shrink-0 rounded p-0.5 font-mono text-[10px] text-muted transition hover:text-ink"
          >
            ×
          </button>
        </div>
      ) : null}
      <ol>
        {thread.map((m) => {
          const isCurrent = m.account === current.account && m.folder === current.folder && m.uid === current.uid
          return (
            <li key={`${m.folder}:${m.uid}`}>
              <button
                type="button"
                disabled={isCurrent}
                onClick={() => onOpen(m)}
                aria-current={isCurrent || undefined}
                className={`flex w-full items-baseline gap-2 border-b border-hairline px-3 py-1.5 text-left last:border-b-0 ${
                  isCurrent ? 'bg-[#EFF2FB]' : 'hover:bg-[#F8F7F4]'
                }`}
              >
                {!m.seen ? <span className="h-[5px] w-[5px] shrink-0 self-center rounded-full bg-unread" aria-label="Ungelesen" /> : null}
                <span className={`min-w-0 shrink-0 truncate text-[12.5px] ${isCurrent ? 'font-medium text-tinte' : ''}`}>
                  {m.from_name || m.from_addr}
                </span>
                <span className="min-w-0 flex-1 truncate text-[12px] text-muted">{m.snippet}</span>
                <span className="shrink-0 rounded bg-[#F1EFEA] px-1 font-mono text-[9.5px] text-muted">
                  {folderLeaf(m.folder)}
                </span>
                <time className="shrink-0 font-mono text-[10px] text-muted">{formatListDate(m.date)}</time>
              </button>
            </li>
          )
        })}
      </ol>
    </section>
  )
}

export function Reader({ opened, imagesEnabled, onEnableImages, onReply, onForward, onArchive, onTrash, onToggleSeen, onToggleSpam, onSnooze, categories, onChangeCategory, onOpenThreadMail, aiEnabled = true, onThreadAction }: ReaderProps) {
  const { showToast } = useToast()
  // Behutsames Shortcut-Teaching: nur bei Maus-Klicks (nicht den Tastatur-
  // Handlern), höchstens einmal je Aktion.
  const teach = (action: string) => {
    const hint = recordMouseAction(action)
    if (hint) showToast(hint)
  }
  const [snoozeOpen, setSnoozeOpen] = useState(false)
  useEffect(() => setSnoozeOpen(false), [opened])
  // RSVP-Antwort merken (pro geöffneter Mail), damit die Karte nach dem Senden
  // den Status zeigt statt erneut die Knöpfe.
  const [answered, setAnswered] = useState<InviteResponse | null>(null)
  const openedKey = opened ? `${opened.account}:${opened.folder}:${opened.uid}` : null
  useEffect(() => setAnswered(null), [openedKey])
  const detailQuery = useQuery({
    queryKey: ['message', opened?.account, opened?.folder, opened?.uid],
    queryFn: () => api.message(opened!.account, opened!.uid, opened!.folder),
    enabled: opened !== null,
  })
  const rsvpMutation = useMutation({
    mutationFn: (v: { ref: MsgRef; response: InviteResponse }) =>
      api.inviteRespond({ account: v.ref.account, folder: v.ref.folder, uid: v.ref.uid, response: v.response }),
    onSuccess: (result, v) => {
      setAnswered(v.response)
      showToast(result.warning ?? 'Antwort an den Organisator gesendet.')
    },
    onError: (e) => showToast(`Antwort fehlgeschlagen: ${errText(e)}`, 'error'),
  })
  const exportMutation = useMutation({
    mutationFn: (ref: MsgRef) => api.exportMarkdown(ref.account, ref.uid, ref.folder),
    onSuccess: ({ filename, markdown }) => {
      // Lokaler Download (Blob) + optionale Kopie — kein Server-Roundtrip.
      const url = URL.createObjectURL(new Blob([markdown], { type: 'text/markdown' }))
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      // Revoke erst nach dem Tick — sofortiges Revoke kann große Downloads kappen.
      setTimeout(() => URL.revokeObjectURL(url), 0)
      // Toast nur „kopiert" melden, wenn die Zwischenablage wirklich verfügbar war.
      const copy = navigator.clipboard?.writeText(markdown)
      if (copy) {
        copy.then(
          () => showToast('Als Markdown kopiert und heruntergeladen.'),
          () => showToast('Als Markdown heruntergeladen.'),
        )
      } else {
        showToast('Als Markdown heruntergeladen.')
      }
    },
    onError: (e) => showToast(`Export fehlgeschlagen: ${errText(e)}`, 'error'),
  })
  const threadQuery = useQuery({
    queryKey: ['thread', opened?.account, opened?.folder, opened?.uid],
    queryFn: () => api.thread(opened!.account, opened!.uid, opened!.folder),
    enabled: opened !== null,
    staleTime: 30_000,
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
              {detail.category ? (
                <label className="relative mt-1 shrink-0 cursor-pointer" title="Kategorie ändern — deine Korrektur bleibt, die KI überschreibt sie nie">
                  <Chip category={detail.category} />
                  <select
                    value={detail.category}
                    onChange={(e) => onChangeCategory(detail, e.target.value)}
                    aria-label="Kategorie ändern"
                    className="absolute inset-0 cursor-pointer opacity-0"
                  >
                    {(categories.includes(detail.category) ? categories : [detail.category, ...categories]).map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
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
              <ActionButton label="Antworten" hint="r" onClick={() => { teach('reply'); onReply(detail) }}>
                <ReplyIcon size={13} />
              </ActionButton>
              <ActionButton label="Weiterleiten" hint="f" onClick={() => { teach('forward'); onForward(detail) }}>
                <ForwardIcon size={13} />
              </ActionButton>
              <ActionButton label="Archivieren" hint="e" onClick={() => { teach('archive'); onArchive(detail) }}>
                <ArchiveIcon size={13} />
              </ActionButton>
              <ActionButton label="Papierkorb" hint="#" onClick={() => { teach('trash'); onTrash(detail) }}>
                <TrashIcon size={13} />
              </ActionButton>
              <div className="relative">
                <ActionButton label="Später" hint="z" onClick={() => { teach('later'); setSnoozeOpen((v) => !v) }}>
                  <ClockIcon size={13} />
                </ActionButton>
                {snoozeOpen ? (
                  <TimePresetMenu
                    heading="Wiedervorlage"
                    placementClass="left-0 top-full mt-1"
                    onPick={(iso) => {
                      setSnoozeOpen(false)
                      onSnooze(detail, iso)
                    }}
                    onClose={() => setSnoozeOpen(false)}
                  />
                ) : null}
              </div>
              <ActionButton
                label={isSpamFolder(detail.folder) ? 'Kein Spam' : 'Spam'}
                hint="!"
                onClick={() => onToggleSpam(detail, !isSpamFolder(detail.folder))}
              >
                <AlertIcon size={13} />
              </ActionButton>
              <ActionButton label={detail.seen ? 'Ungelesen' : 'Gelesen'} hint="u" onClick={() => { teach('seen'); onToggleSeen(detail) }}>
                {detail.seen ? <MailIcon size={13} /> : <MailOpenIcon size={13} />}
              </ActionButton>
              <ActionButton
                label={exportMutation.isPending ? 'Exportiere …' : 'Als Markdown'}
                onClick={() => exportMutation.mutate(opened)}
              >
                <DownloadIcon size={13} />
              </ActionButton>
              {detail.attachments.length > 0 ? (
                <span className="ml-auto flex items-center gap-1 font-mono text-[11px] text-muted">
                  <PaperclipIcon size={12} />
                  {detail.attachments.length} {detail.attachments.length === 1 ? 'Anhang' : 'Anhänge'}
                </span>
              ) : null}
            </div>
          </header>

          {detail.invite ? (
            <InviteCard
              invite={detail.invite}
              answered={answered}
              pending={rsvpMutation.isPending}
              onRespond={(response) => rsvpMutation.mutate({ ref: opened, response })}
            />
          ) : null}

          {(detail.entities?.length ?? 0) > 0 ? <EntityChips entities={detail.entities} /> : null}

          {(threadQuery.data?.length ?? 0) > 1 ? (
            <ThreadRail
              thread={threadQuery.data!}
              current={opened}
              aiEnabled={aiEnabled}
              onOpen={onOpenThreadMail}
              onAction={onThreadAction}
            />
          ) : null}

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
