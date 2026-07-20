import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import { useGlobalKeydown } from '../lib/keyboard'
import type { Account, Detail, EmiliaImproveMode, SendRequest } from '../lib/types'
import { useToast } from './Toast'
import { SparklesIcon, SpinnerIcon, XIcon } from './Icons'

export type ComposerState = { mode: 'new'; account: string } | { mode: 'reply'; detail: Detail }

function parseAddrs(raw: string): string[] {
  return raw
    .split(/[,;]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

const FIELD_LABEL = 'font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted'
const FIELD_INPUT =
  'w-full rounded border border-hairline bg-paper px-2.5 py-1.5 text-[13px] focus:border-tinte focus:outline-none'

export function Composer({
  state,
  accounts,
  onClose,
}: {
  state: ComposerState
  accounts: Account[]
  onClose: () => void
}) {
  const { showToast } = useToast()
  const reply = state.mode === 'reply' ? state.detail : null

  const initial = useMemo(() => {
    if (reply) {
      // Präfix-Erkennung analog zur Drafter-Regel im Backend (Re/AW/Antw/Fwd/WG).
      const subject = /^\s*(re|aw|antw|fwd?|wg)\s*:/i.test(reply.subject) ? reply.subject : `Re: ${reply.subject}`
      return { to: reply.reply_to || reply.from_addr, subject }
    }
    return { to: '', subject: '' }
  }, [reply])

  const [account, setAccount] = useState(state.mode === 'reply' ? state.detail.account : state.account)
  const [to, setTo] = useState(initial.to)
  const [cc, setCc] = useState('')
  const [ccOpen, setCcOpen] = useState(false)
  const [subject, setSubject] = useState(initial.subject)
  const [body, setBody] = useState('')
  const [sendError, setSendError] = useState<string | null>(null)
  const [armed, setArmed] = useState(false) // "Wirklich senden?"-Zweitklick
  const [discardArmed, setDiscardArmed] = useState(false) // Esc bei ungespeichertem Text
  const armTimer = useRef<number | null>(null)
  const discardTimer = useRef<number | null>(null)

  const dirty = to !== initial.to || cc !== '' || subject !== initial.subject || body !== ''

  const sendMutation = useMutation({
    mutationFn: (req: SendRequest) => api.send(req),
    onSuccess: () => {
      showToast('Gesendet.')
      onClose()
    },
    onError: (e) => setSendError(errText(e)), // Text bleibt erhalten
  })

  const draftMutation = useMutation({
    mutationFn: () => api.draft({ account: reply!.account, folder: reply!.folder, uid: reply!.uid }),
    onSuccess: ({ text }) => {
      // Manuelles Schreiben nie blockieren/überschreiben: vorhandenen Text ergänzen.
      setBody((prev) => (prev.trim() ? `${prev}\n\n${text}` : text))
    },
  })

  // Emilia (lokal): Text korrigieren/verbessern, mit Rückgängig im Toast.
  const prevBodyRef = useRef<string | null>(null)
  const improveMutation = useMutation({
    mutationFn: (mode: EmiliaImproveMode) => api.emiliaImprove({ text: body, mode }),
    onSuccess: ({ text }, mode) => {
      prevBodyRef.current = body
      setBody(text)
      showToast(mode === 'korrigieren' ? 'Emilia hat korrigiert.' : 'Emilia hat überarbeitet.', 'info', {
        label: 'Rückgängig',
        run: () => {
          if (prevBodyRef.current !== null) setBody(prevBodyRef.current)
        },
      })
    },
    onError: (e) => showToast(`Emilia fehlgeschlagen: ${errText(e)}`, 'error'),
  })

  const trySend = useCallback(() => {
    if (sendMutation.isPending) return
    const toList = parseAddrs(to)
    if (toList.length === 0) {
      setSendError('Mindestens ein Empfänger nötig.')
      return
    }
    if (!armed) {
      // Bestätigung ohne confirm(): Button wird für 3 s zu "Wirklich senden?"
      setArmed(true)
      if (armTimer.current) window.clearTimeout(armTimer.current)
      armTimer.current = window.setTimeout(() => setArmed(false), 3000)
      return
    }
    setArmed(false)
    setSendError(null)
    sendMutation.mutate({
      account,
      to: toList,
      cc: parseAddrs(cc),
      subject,
      body,
      ...(reply ? { reply_to_uid: reply.uid, folder: reply.folder } : {}),
    })
  }, [account, armed, body, cc, reply, sendMutation, subject, to])

  const tryClose = useCallback(() => {
    if (!dirty || discardArmed) {
      onClose()
      return
    }
    // Verwerfen-Bestätigung ohne confirm(): zweites Esc innerhalb von 3 s schließt.
    setDiscardArmed(true)
    if (discardTimer.current) window.clearTimeout(discardTimer.current)
    discardTimer.current = window.setTimeout(() => setDiscardArmed(false), 3000)
  }, [dirty, discardArmed, onClose])

  useGlobalKeydown((e) => {
    if (e.key === 'Escape') tryClose()
  })

  // Bestätigungs-Timer beim Unmount aufräumen.
  useEffect(
    () => () => {
      if (armTimer.current) window.clearTimeout(armTimer.current)
      if (discardTimer.current) window.clearTimeout(discardTimer.current)
    },
    [],
  )

  return (
    <>
      <div className="fade-in fixed inset-0 z-40 bg-black/10" onMouseDown={tryClose} aria-hidden="true" />
      <aside className="slide-in-right fixed inset-y-0 right-0 z-40 flex w-[460px] max-w-full flex-col border-l border-hairline bg-surface shadow-lg">
        <header className="flex items-center gap-2 border-b border-hairline px-4 py-3">
          <h2 className="text-[15px] font-semibold">{reply ? 'Antworten' : 'Verfassen'}</h2>
          {reply ? <span className="min-w-0 truncate font-mono text-[10.5px] text-muted">zu „{reply.subject}“</span> : null}
          <span className="flex-1" />
          <button
            type="button"
            onClick={tryClose}
            title="Schließen (Esc)"
            aria-label="Schließen"
            className="rounded p-1 text-muted transition hover:text-ink"
          >
            <XIcon size={15} />
          </button>
        </header>

        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-3">
          {!reply && accounts.length > 1 ? (
            <label className="block">
              <span className={FIELD_LABEL}>Von</span>
              <select value={account} onChange={(e) => setAccount(e.target.value)} className={`mt-1 ${FIELD_INPUT}`}>
                {accounts.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.name} — {a.address}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label className="block">
            <span className={FIELD_LABEL}>An</span>
            <input
              autoFocus={!reply}
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder="adresse@example.org, weitere@example.org"
              className={`mt-1 ${FIELD_INPUT}`}
            />
          </label>

          {ccOpen ? (
            <label className="block">
              <span className={FIELD_LABEL}>CC</span>
              <input value={cc} onChange={(e) => setCc(e.target.value)} className={`mt-1 ${FIELD_INPUT}`} />
            </label>
          ) : (
            <button
              type="button"
              onClick={() => setCcOpen(true)}
              className="self-start font-mono text-[10.5px] text-muted transition hover:text-tinte"
            >
              + CC
            </button>
          )}

          <label className="block">
            <span className={FIELD_LABEL}>Betreff</span>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} className={`mt-1 ${FIELD_INPUT}`} />
          </label>

          <label className="flex min-h-0 flex-1 flex-col">
            <span className={FIELD_LABEL}>Nachricht</span>
            <textarea
              autoFocus={!!reply}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className={`mt-1 min-h-[180px] flex-1 resize-none rounded border border-hairline bg-paper px-2.5 py-2 text-[13.5px] leading-relaxed focus:border-tinte focus:outline-none`}
            />
          </label>

          {draftMutation.isError ? (
            <p className="text-[12px] text-red-700">KI-Entwurf fehlgeschlagen: {errText(draftMutation.error)}</p>
          ) : null}
          {sendError ? <p className="text-[12px] text-red-700">Senden fehlgeschlagen: {sendError}</p> : null}
        </div>

        <footer className="flex items-center gap-2 border-t border-hairline px-4 py-3">
          <button
            type="button"
            onClick={() => draftMutation.mutate()}
            disabled={!reply || draftMutation.isPending}
            title={reply ? 'Antwortentwurf per KI erzeugen' : 'Nur bei Antworten verfügbar'}
            className="flex items-center gap-1.5 rounded border border-hairline px-2.5 py-1.5 text-[12.5px] transition enabled:hover:border-tinte enabled:hover:text-tinte disabled:opacity-40"
          >
            {draftMutation.isPending ? <SpinnerIcon size={12} /> : <SparklesIcon size={13} />}
            AI-Entwurf
          </button>
          <button
            type="button"
            onClick={() => improveMutation.mutate('korrigieren')}
            disabled={!body.trim() || improveMutation.isPending}
            title="Emilia korrigiert Rechtschreibung & Grammatik (lokal)"
            className="rounded border border-hairline px-2.5 py-1.5 text-[12.5px] transition enabled:hover:border-tinte enabled:hover:text-tinte disabled:opacity-40"
          >
            Korrigieren
          </button>
          <button
            type="button"
            onClick={() => improveMutation.mutate('verbessern')}
            disabled={!body.trim() || improveMutation.isPending}
            title="Emilia verbessert Stil & Klarheit (lokal)"
            className="rounded border border-hairline px-2.5 py-1.5 text-[12.5px] transition enabled:hover:border-tinte enabled:hover:text-tinte disabled:opacity-40"
          >
            {improveMutation.isPending ? <SpinnerIcon size={12} /> : 'Verbessern'}
          </button>
          <span className="flex-1" />
          {discardArmed ? <span className="font-mono text-[10.5px] text-red-700">Nochmal Esc: Verwerfen</span> : null}
          <button
            type="button"
            onClick={trySend}
            disabled={sendMutation.isPending}
            className={`rounded px-3.5 py-1.5 text-[12.5px] font-medium text-white transition disabled:opacity-60 ${
              armed ? 'bg-[#8C2F2F] hover:bg-[#7A2828]' : 'bg-tinte hover:bg-[#1D3494]'
            }`}
          >
            {sendMutation.isPending ? 'Senden …' : armed ? 'Wirklich senden?' : 'Senden'}
          </button>
        </footer>
      </aside>
    </>
  )
}
