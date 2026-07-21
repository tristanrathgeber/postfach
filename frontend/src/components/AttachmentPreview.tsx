import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import type { Attachment } from '../lib/types'
import { attachmentKind } from '../lib/attachmentKind'
import { formatSize } from '../lib/format'
import { ChevronRightIcon, DownloadIcon, PaperclipIcon, SpinnerIcon, XIcon } from './Icons'
import { useToast } from './Toast'

type Props = {
  account: string
  uid: number
  folder: string
  attachments: Attachment[]
  startIndex: number
  onClose: () => void
}

/** Anhang-Vorschau als schließbares Overlay: Bilder, PDFs und Text inline
 * (nur sichere Typen — der Server liefert alles andere als Download aus), mit
 * ‹ › zwischen mehreren Anhängen. Esc / ✕ / Klick daneben schließen. */
export function AttachmentPreview({ account, uid, folder, attachments, startIndex, onClose }: Props) {
  const { showToast } = useToast()
  const [pos, setPos] = useState(() => Math.min(Math.max(startIndex, 0), attachments.length - 1))
  const dialogRef = useRef<HTMLDivElement>(null)

  const current = attachments[pos]
  const many = attachments.length > 1
  const prev = useCallback(() => setPos((p) => (p - 1 + attachments.length) % attachments.length), [attachments.length])
  const next = useCallback(() => setPos((p) => (p + 1) % attachments.length), [attachments.length])

  useEffect(() => {
    // Capture-Phase + stopPropagation: solange die Vorschau offen ist, erreicht
    // KEINE Taste die globalen Shortcuts — sonst würde z. B. „e" die Mail
    // darunter archivieren. Esc schließt, ←/→ blättern.
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      } else if (many && e.key === 'ArrowLeft') {
        e.preventDefault()
        prev()
      } else if (many && e.key === 'ArrowRight') {
        e.preventDefault()
        next()
      }
      e.stopPropagation()
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [onClose, prev, next, many])

  useEffect(() => {
    dialogRef.current?.focus()
  }, [])

  const save = useMutation({
    mutationFn: () => api.saveAttachment(account, uid, current.index, folder),
    onSuccess: (r) => showToast(`In „Downloads" gespeichert: ${r.filename}`),
    onError: (e) => showToast(`Speichern fehlgeschlagen: ${errText(e)}`, 'error'),
  })

  if (!current) return null

  // Klick auf den freien Rand (nicht auf ein Kind) schließt.
  const closeOnBackdrop = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }

  return (
    <div className="fade-in fixed inset-0 z-[70] flex flex-col bg-black/60" onMouseDown={closeOnBackdrop}>
      {/* Kopf */}
      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-label={`Vorschau: ${current.filename}`}
        className="flex items-center gap-3 px-4 py-2.5 text-white outline-none"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <PaperclipIcon size={14} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] font-medium">{current.filename}</p>
          <p className="font-mono text-[10.5px] text-white/60">
            {formatSize(current.size)}
            {many ? ` · ${pos + 1} von ${attachments.length}` : ''}
          </p>
        </div>
        <DownloadButton
          onClick={() => save.mutate()}
          pending={save.isPending}
          className="bg-white/15 hover:bg-white/25"
        />
        <button
          type="button"
          onClick={onClose}
          aria-label="Schließen"
          className="rounded-md p-1.5 text-white/80 transition hover:bg-white/15 hover:text-white"
        >
          <XIcon size={16} />
        </button>
      </div>

      {/* Bühne */}
      <div className="relative flex min-h-0 flex-1 items-center justify-center px-4 pb-4" onMouseDown={closeOnBackdrop}>
        {many && (
          <NavButton side="left" onClick={prev} />
        )}
        <PreviewBody
          key={current.index}
          url={api.attachmentUrl(account, uid, current.index, folder, true)}
          contentType={current.content_type}
          filename={current.filename}
          onDownload={() => save.mutate()}
          saving={save.isPending}
        />
        {many && <NavButton side="right" onClick={next} />}
      </div>
    </div>
  )
}

function NavButton({ side, onClick }: { side: 'left' | 'right'; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={side === 'left' ? 'Vorheriger Anhang' : 'Nächster Anhang'}
      className={`absolute top-1/2 -translate-y-1/2 ${side === 'left' ? 'left-3' : 'right-3'} z-10 rounded-full bg-white/15 p-2 text-white transition hover:bg-white/30`}
    >
      <span className={side === 'left' ? 'block rotate-180' : 'block'}>
        <ChevronRightIcon size={20} />
      </span>
    </button>
  )
}

function PreviewBody({
  url,
  contentType,
  filename,
  onDownload,
  saving,
}: {
  url: string
  contentType: string
  filename: string
  onDownload: () => void
  saving: boolean
}) {
  const kind = attachmentKind(contentType)

  if (kind === 'image') {
    return (
      <img
        src={url}
        alt={filename}
        className="max-h-full max-w-full rounded-lg bg-white object-contain shadow-2xl"
      />
    )
  }

  if (kind === 'pdf') {
    // Sicher: der Server liefert INLINE nur echte PDFs (gefährliche Typen kommen
    // als octet-stream-Download zurück und würden hier gar nicht rendern).
    return (
      <iframe
        title={filename}
        src={url}
        className="h-full w-full max-w-[1000px] rounded-lg border-0 bg-white shadow-2xl"
      />
    )
  }

  if (kind === 'text') {
    return <TextPreview url={url} />
  }

  // Kein sicher darstellbarer Typ → ehrliche Karte mit Download.
  return (
    <div className="max-w-sm rounded-xl bg-surface px-6 py-8 text-center shadow-2xl">
      <PaperclipIcon size={22} />
      <p className="mt-3 text-[14px] font-medium text-ink">Keine Vorschau möglich</p>
      <p className="mt-1 text-[12.5px] text-muted">Dieser Dateityp lässt sich nicht sicher anzeigen — du kannst ihn aber herunterladen.</p>
      <DownloadButton
        onClick={onDownload}
        pending={saving}
        className="mt-4 bg-btn text-btn-ink hover:bg-btn-strong"
      />
    </div>
  )
}

/** „Herunterladen"-Knopf mit Spinner-Zustand; Aussehen kommt per className. */
function DownloadButton({ onClick, pending, className }: { onClick: () => void; pending: boolean; className: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={pending}
      className={`inline-flex items-center gap-1.5 rounded-md px-3.5 py-1.5 text-[12.5px] font-medium transition disabled:opacity-50 ${className}`}
    >
      {pending ? <SpinnerIcon size={13} /> : <DownloadIcon size={13} />}
      Herunterladen
    </button>
  )
}

function TextPreview({ url }: { url: string }) {
  const [state, setState] = useState<{ text?: string; error?: string }>({})

  useEffect(() => {
    let alive = true
    fetch(url)
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`Fehler ${r.status}`))))
      .then((t) => alive && setState({ text: t.slice(0, 200_000) }))
      .catch((e) => alive && setState({ error: String(e?.message || e) }))
    return () => {
      alive = false
    }
  }, [url])

  if (state.error) return <p className="text-[13px] text-white/80">{state.error}</p>
  if (state.text === undefined) {
    return (
      <div className="flex items-center gap-2 text-white/80">
        <SpinnerIcon size={15} /> Lädt …
      </div>
    )
  }
  return (
    <pre className="mail-paper h-full w-full max-w-[900px] overflow-auto rounded-lg p-5 text-[12.5px] leading-relaxed shadow-2xl">
      {state.text}
    </pre>
  )
}
