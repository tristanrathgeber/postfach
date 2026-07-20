import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import type { EmiliaSource } from '../lib/types'
import { SparklesIcon, SpinnerIcon, XIcon } from './Icons'
import { useToast } from './Toast'

type ChatMessage = { role: 'user' | 'emilia'; text: string; sources?: EmiliaSource[] }

/** Kontext-Hinweis: die gerade geöffnete Mail, die Emilias Fragen begleitet. */
export type EmiliaContext = { folder: string; uid: number; subject: string }

export function EmiliaPanel({
  account,
  context,
  onOpenSource,
  onClose,
}: {
  account: string | null
  context: EmiliaContext | null
  onOpenSource: (source: EmiliaSource) => void
  onClose: () => void
}) {
  const { showToast } = useToast()
  const qc = useQueryClient()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [contextDismissed, setContextDismissed] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Neuer Mail-Kontext → Hinweis wieder anzeigen
  const contextKey = context ? `${context.folder}:${context.uid}` : null
  useEffect(() => setContextDismissed(false), [contextKey])

  const status = useQuery({ queryKey: ['emilia-status'], queryFn: api.emiliaStatus })

  const indexMutation = useMutation({
    mutationFn: () => api.emiliaIndex({ account: account! }),
    onSuccess: ({ indexed }) => {
      qc.invalidateQueries({ queryKey: ['emilia-status'] })
      showToast(`Gedächtnis aufgebaut: ${indexed} Mails.`)
    },
    onError: (e) => showToast(`Gedächtnis fehlgeschlagen: ${errText(e)}`, 'error'),
  })

  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      api.emiliaChat({
        account: account!,
        message,
        ...(context && !contextDismissed ? { folder: context.folder, uid: context.uid } : {}),
      }),
    onSuccess: ({ reply, sources }) => {
      setMessages((prev) => [...prev, { role: 'emilia', text: reply, sources }])
    },
    onError: (e) => {
      setMessages((prev) => [...prev, { role: 'emilia', text: `Da ist etwas schiefgegangen: ${errText(e)}` }])
    },
  })

  const send = useCallback(() => {
    const message = input.trim()
    if (!message || !account || chatMutation.isPending) return
    setMessages((prev) => [...prev, { role: 'user', text: message }])
    setInput('')
    chatMutation.mutate(message)
  }, [input, account, chatMutation])

  // Ans Ende scrollen, wenn neue Nachrichten kommen
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages.length, chatMutation.isPending])

  return (
    <aside className="flex h-full w-[340px] shrink-0 flex-col border-l border-hairline bg-paper">
      <header className="border-b border-hairline px-4 py-3">
        <div className="flex items-center gap-2">
          <h2 className="font-serif text-[19px] italic leading-none">Emilia</h2>
          <span className="flex-1" />
          <button
            type="button"
            onClick={onClose}
            title="Schließen (Esc)"
            aria-label="Emilia schließen"
            className="rounded p-1 text-muted transition hover:text-ink"
          >
            <XIcon size={14} />
          </button>
        </div>
        <p className="pt-1 font-mono text-[10px] text-muted">
          {status.data
            ? `${status.data.model} · lokal · ${status.data.indexed_mails} Mails im Gedächtnis`
            : 'Status wird geladen …'}
          {account ? ` · ${account}` : ''}
        </p>
      </header>

      {status.data && status.data.indexed_mails === 0 ? (
        <div className="mx-3 mt-3 rounded border border-hairline bg-surface px-3 py-2.5">
          <p className="text-[12.5px] leading-snug text-ink">
            Emilia kennt deine Mails noch nicht. Das Gedächtnis wird lokal aufgebaut und bleibt auf
            diesem Rechner.
          </p>
          <button
            type="button"
            onClick={() => indexMutation.mutate()}
            disabled={!account || indexMutation.isPending}
            className="mt-2 flex items-center gap-1.5 rounded bg-tinte px-2.5 py-1.5 text-[12px] font-medium text-white transition hover:bg-[#1D3494] disabled:opacity-60"
          >
            {indexMutation.isPending ? <SpinnerIcon size={12} /> : <SparklesIcon size={12} />}
            {indexMutation.isPending ? 'Baue Gedächtnis …' : 'Gedächtnis aufbauen'}
          </button>
        </div>
      ) : null}

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {messages.length === 0 ? (
          <div className="px-2 pt-8 text-center">
            <p className="font-serif text-[17px] italic text-ink">Frag mich etwas.</p>
            <p className="pt-1.5 font-mono text-[10.5px] leading-relaxed text-muted">
              „Was wollte der Steuerberater?" · „Wann ist der Zahnarzttermin?" · „Fasse die Mail
              zusammen"
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {messages.map((m, i) =>
              m.role === 'user' ? (
                <div key={i} className="ml-8 self-end rounded-lg bg-[#EBEEF9] px-3 py-2 text-[13px] leading-relaxed">
                  {m.text}
                </div>
              ) : (
                <div key={i} className="mr-4 border-l-2 border-hairline pl-3">
                  <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink">{m.text}</p>
                  {m.sources && m.sources.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5 pt-2">
                      {m.sources.map((s) => (
                        <button
                          key={`${s.folder}:${s.uid}`}
                          type="button"
                          onClick={() => onOpenSource(s)}
                          title={`${s.subject} — öffnen`}
                          className="max-w-[200px] truncate rounded border border-hairline bg-surface px-2 py-0.5 text-left font-mono text-[9.5px] text-muted transition hover:border-tinte hover:text-tinte"
                        >
                          {s.subject || '(ohne Betreff)'}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ),
            )}
            {chatMutation.isPending ? (
              <p className="border-l-2 border-hairline pl-3 font-mono text-[11px] text-muted">Emilia denkt …</p>
            ) : null}
          </div>
        )}
      </div>

      <footer className="border-t border-hairline px-3 py-2.5">
        {context && !contextDismissed ? (
          <p className="flex items-center gap-1 pb-1.5 font-mono text-[9.5px] text-muted">
            <span className="min-w-0 truncate">Kontext: {context.subject || 'geöffnete Mail'}</span>
            <button
              type="button"
              onClick={() => setContextDismissed(true)}
              aria-label="Kontext entfernen"
              className="shrink-0 rounded p-0.5 transition hover:text-ink"
            >
              <XIcon size={10} />
            </button>
          </p>
        ) : null}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send()
            }
            e.stopPropagation()
          }}
          rows={Math.min(4, Math.max(1, input.split('\n').length))}
          placeholder={account ? 'Emilia fragen … (Enter sendet)' : 'Kein Konto verfügbar'}
          disabled={!account}
          className="w-full resize-none rounded border border-hairline bg-surface px-2.5 py-2 text-[13px] leading-relaxed focus:border-tinte focus:outline-none disabled:opacity-50"
        />
      </footer>
    </aside>
  )
}
