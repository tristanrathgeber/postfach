import { useCallback, useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import { useGlobalKeydown } from '../lib/keyboard'
import { formatFullDate, formatSize } from '../lib/format'
import { FIELD_INPUT, FIELD_LABEL } from '../lib/form'
import { expandSnippet, matchAbbrev } from '../lib/snippets'
import { useSnippets } from '../hooks/useLocalStores'
import type { Account, Contact, Detail, Draft, EmiliaImproveMode, Snippet } from '../lib/types'
import { useToast } from './Toast'
import { RecipientField } from './RecipientField'
import { PaperclipIcon, SparklesIcon, SpinnerIcon, XIcon } from './Icons'

export type ComposerState =
  | { mode: 'new'; account: string; draft?: Draft }
  | { mode: 'reply'; detail: Detail; draft?: Draft }
  | { mode: 'forward'; detail: Detail; draft?: Draft }

/** Client-seitiges Anhang-Limit — der Server antwortet ab hier mit 413. */
const MAX_ATTACH_BYTES = 25 * 1024 * 1024

const FORWARD_MARKER = '\n\n---------- Weitergeleitete Nachricht ----------'

function forwardQuote(d: Detail): string {
  return `${FORWARD_MARKER}\nVon: ${d.from_name} <${d.from_addr}>\nDatum: ${formatFullDate(d.date)}\nBetreff: ${d.subject}\nAn: ${d.to.join(', ')}\n\n${d.body_text}`
}

function sigBlockFor(signatures: Record<string, string>, account: string): string | null {
  const raw = (signatures[account] ?? '').trim()
  return raw ? `\n\n-- \n${raw}` : null
}

export function Composer({
  state,
  accounts,
  signatures,
  snippetInsertRef,
  persistRef,
  modalAbove = false,
  onClose,
}: {
  state: ComposerState
  accounts: Account[]
  /** Signaturen pro Konto (aus den Einstellungen) — synchron beim Öffnen eingefügt. */
  signatures: Record<string, string>
  /** ⌘K-Palette fügt darüber Snippets an der Cursor-Position ein. */
  snippetInsertRef?: MutableRefObject<((snip: Snippet) => void) | null>
  /** App sichert darüber den Entwurf, bevor sie den Composer ersetzt (⌘K-Aktionen). */
  persistRef?: MutableRefObject<(() => void) | null>
  /** Ein Modal (Einstellungen) liegt über dem Composer — Esc gehört dann dem Modal. */
  modalAbove?: boolean
  onClose: () => void
}) {
  const { showToast } = useToast()
  const qc = useQueryClient()
  const draft = state.draft
  const reply = state.mode === 'reply' ? state.detail : null
  const forward = state.mode === 'forward' ? state.detail : null
  const refDetail = reply ?? forward

  const initialAccount = draft ? draft.account : state.mode === 'new' ? state.account : state.detail.account

  // Signatur synchron in den Start-Body rechnen — kein Nachträglich-Einfügen
  // per Effekt (das erzeugte Doppel-Signaturen und KI-Text unter der Signatur).
  const initial = useMemo(() => {
    if (draft) return { to: draft.to, cc: draft.cc, bcc: draft.bcc, subject: draft.subject, body: draft.body }
    const sig = sigBlockFor(signatures, initialAccount) ?? ''
    if (reply) {
      // Präfix-Erkennung analog zur Drafter-Regel im Backend (Re/AW/Antw/Fwd/WG).
      const subject = /^\s*(re|aw|antw|fwd?|wg)\s*:/i.test(reply.subject) ? reply.subject : `Re: ${reply.subject}`
      return { to: [reply.reply_to || reply.from_addr], cc: [], bcc: [], subject, body: sig }
    }
    if (forward) {
      const subject = /^\s*(fwd?|wg)\s*:/i.test(forward.subject) ? forward.subject : `Fwd: ${forward.subject}`
      return { to: [], cc: [], bcc: [], subject, body: sig + forwardQuote(forward) }
    }
    return { to: [], cc: [], bcc: [], subject: '', body: sig }
  }, [draft, reply, forward, signatures, initialAccount])

  const [account, setAccount] = useState(initialAccount)
  const [to, setTo] = useState<string[]>(initial.to)
  const [cc, setCc] = useState<string[]>(initial.cc)
  const [bcc, setBcc] = useState<string[]>(initial.bcc)
  const [ccOpen, setCcOpen] = useState(initial.cc.length > 0)
  const [bccOpen, setBccOpen] = useState(initial.bcc.length > 0)
  const [subject, setSubject] = useState(initial.subject)
  const [body, setBody] = useState(initial.body)
  const [files, setFiles] = useState<File[]>([])
  const [dragOver, setDragOver] = useState(false)
  const [includeAtts, setIncludeAtts] = useState(
    draft ? (draft.include_attachments ?? true) : state.mode === 'forward',
  )
  const [touched, setTouched] = useState(false) // Nutzer hat inhaltlich editiert → Auto-Save aktiv
  const [sendError, setSendError] = useState<string | null>(null)
  const [armed, setArmed] = useState(false) // "Wirklich senden?"-Zweitklick
  const [discardArmed, setDiscardArmed] = useState(false) // Esc bei ungespeichertem Text
  const armTimer = useRef<number | null>(null)
  const discardTimer = useRef<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const bodyRef = useRef<HTMLTextAreaElement>(null)

  // Jede inhaltliche Änderung aktiviert den Auto-Save — ein Helper statt
  // neun verstreuter setTouched(true)-Zeilen (Vergessen wäre Datenverlust).
  const edit = useCallback(<T,>(setter: (v: T) => void) => (v: T) => {
    setTouched(true)
    setter(v)
  }, [])

  // Adresse → Anzeigename für {vorname}-Snippets: startet mit dem Original-
  // Absender (Reply/Forward), Kontakte-Picks in den Empfängerfeldern ergänzen.
  // Keys lowercase — Header-Case und Kontakt-Case unterscheiden sich.
  const namesRef = useRef<Map<string, string> | null>(null)
  if (namesRef.current === null) {
    const names = new Map<string, string>()
    if (refDetail?.from_name) {
      names.set(refDetail.from_addr.toLowerCase(), refDetail.from_name)
      if (refDetail.reply_to) names.set(refDetail.reply_to.toLowerCase(), refDetail.from_name)
    }
    namesRef.current = names
  }
  const rememberName = useCallback((c: Contact) => {
    if (c.name) namesRef.current?.set(c.addr.toLowerCase(), c.name)
  }, [])

  // Das Limit zählt Uploads UND mitzusendende Original-Anhänge der Weiterleitung.
  const forwardAttsSize =
    forward && includeAtts ? forward.attachments.reduce((sum, a) => sum + a.size, 0) : 0
  const totalSize = files.reduce((sum, f) => sum + f.size, 0) + forwardAttsSize
  const overLimit = totalSize > MAX_ATTACH_BYTES
  const dirty = touched || files.length > 0

  // --- Signatur: steckt bereits im Start-Body; hier nur der Kontowechsel-Tausch ---
  const sigRef = useRef<string | null>(null) // aktuell automatisch eingefügter Block
  if (sigRef.current === null) {
    const block = sigBlockFor(signatures, initialAccount)
    // Bei Draft-Resume zählt die Signatur nur als "automatisch", wenn sie
    // unverändert im gespeicherten Body steht — sonst doppelt der Kontowechsel sie.
    sigRef.current = block && initial.body.includes(block) ? block : ''
  }
  const prevAccountRef = useRef(account)

  useEffect(() => {
    const accountChanged = prevAccountRef.current !== account
    prevAccountRef.current = account
    if (!accountChanged) return
    const block = sigBlockFor(signatures, account)
    const old = sigRef.current || null
    if (old === block) return
    setTouched(true) // der Tausch ist eine inhaltliche Änderung — speichern
    setBody((prev) => {
      if (old) {
        if (!prev.includes(old)) return prev // Nutzer hat die Signatur angefasst — nicht anrühren
        sigRef.current = block ?? ''
        return prev.replace(old, block ?? '')
      }
      if (block && !prev.includes(block)) {
        sigRef.current = block
        const idx = prev.indexOf(FORWARD_MARKER)
        return idx >= 0 ? prev.slice(0, idx) + block + prev.slice(idx) : prev + block
      }
      return prev
    })
  }, [signatures, account])

  // --- Entwürfe (Nachtrag v0.3): Auto-Save-Upsert über stabile id ---
  const draftIdRef = useRef(draft?.id ?? crypto.randomUUID())
  const savedRef = useRef(!!draft) // existiert der Entwurf server-seitig?
  const sentRef = useRef(false) // nach dem Senden keinen Auto-Save mehr starten
  const saveInFlightRef = useRef<Promise<unknown> | null>(null) // laufender Auto-Save-Request

  const buildDraft = useCallback(
    () => ({
      id: draftIdRef.current,
      account,
      to,
      cc,
      bcc,
      subject,
      body,
      mode: state.mode,
      include_attachments: includeAtts,
      ...(refDetail ? { ref_folder: refDetail.folder, ref_uid: refDetail.uid } : {}),
    }),
    [account, to, cc, bcc, subject, body, state.mode, includeAtts, refDetail],
  )

  useEffect(() => {
    if (!touched) return
    const t = window.setTimeout(() => {
      if (sentRef.current) return
      // Saves verketten: laufen zwei gleichzeitig, könnte der ältere den
      // neueren (oder das Löschen nach dem Senden) überholen.
      saveInFlightRef.current = (saveInFlightRef.current ?? Promise.resolve())
        .then(() => {
          if (sentRef.current) return
          return api.saveDraft(buildDraft()).then(() => {
            savedRef.current = true
            qc.invalidateQueries({ queryKey: ['drafts'] })
          })
        })
        .catch(() => {
          // Auto-Save still halten — die nächste Änderung versucht es erneut.
        })
    }, 1500)
    return () => window.clearTimeout(t)
  }, [touched, buildDraft, qc])

  // --- Senden ---
  // Der Server löscht den Entwurf nach erfolgreichem Versand (draft_id im Request).
  // Vor dem POST noch die Save-Kette abwarten, damit kein später ankommender
  // Auto-Save den Entwurf wieder anlegt.
  const sendMutation = useMutation({
    mutationFn: async () => {
      await (saveInFlightRef.current ?? Promise.resolve())
      const req = {
        account,
        to,
        cc,
        bcc,
        subject,
        body,
        draft_id: draftIdRef.current,
        ...(reply ? { reply_to_uid: reply.uid, folder: reply.folder } : {}),
        ...(forward
          ? {
              forward_of: {
                folder: forward.folder,
                uid: forward.uid,
                include_attachments: includeAtts && forward.attachments.length > 0,
              },
            }
          : {}),
      }
      return files.length > 0 ? api.sendWithAttachments(req, files) : api.send(req)
    },
    onSuccess: ({ warning }) => {
      savedRef.current = false
      qc.invalidateQueries({ queryKey: ['drafts'] })
      showToast('Gesendet.')
      if (warning) showToast(warning, 'error') // SMTP ok, Ablage fehlgeschlagen — NICHT erneut senden
      onClose()
    },
    onError: (e) => {
      sentRef.current = false
      setSendError(errText(e)) // Text bleibt erhalten
    },
  })

  const draftMutation = useMutation({
    mutationFn: () => api.draft({ account: reply!.account, folder: reply!.folder, uid: reply!.uid }),
    onSuccess: ({ text }) => {
      // Manuelles Schreiben nie blockieren/überschreiben: ergänzen — aber VOR
      // der automatischen Signatur bzw. dem Weiterleitungs-Zitat.
      setTouched(true)
      setBody((prev) => {
        const sig = sigRef.current
        let idx = sig && prev.includes(sig) ? prev.indexOf(sig) : -1
        if (idx < 0) {
          const marker = prev.indexOf(FORWARD_MARKER)
          idx = marker >= 0 ? marker : prev.length
        }
        const before = prev.slice(0, idx)
        return before + (before.trim() ? '\n\n' : '') + text + prev.slice(idx)
      })
    },
  })

  // Emilia (lokal): Text korrigieren/verbessern, mit Rückgängig im Toast.
  const prevBodyRef = useRef<string | null>(null)
  const improveMutation = useMutation({
    mutationFn: (mode: EmiliaImproveMode) => api.emiliaImprove({ text: body, mode }),
    onSuccess: ({ text }, mode) => {
      prevBodyRef.current = body
      setTouched(true)
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
    if (sendMutation.isPending || overLimit) return
    if (to.length === 0) {
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
    sentRef.current = true
    sendMutation.mutate()
  }, [armed, overLimit, sendMutation, to])

  // Schließen behält den Entwurf (Sicherheitsnetz) — außer er ist komplett leer.
  const persistAndClose = useCallback(() => {
    if (!sentRef.current && touched) {
      const stripped = sigRef.current ? body.replace(sigRef.current, '') : body
      const empty = to.length === 0 && cc.length === 0 && bcc.length === 0 && !subject.trim() && !stripped.trim()
      if (empty) {
        if (savedRef.current) {
          savedRef.current = false
          api
            .deleteDraft(draftIdRef.current)
            .then(() => qc.invalidateQueries({ queryKey: ['drafts'] }))
            .catch(() => {})
        }
      } else {
        // Letzte Änderungen sofort sichern (der 1,5-s-Debounce könnte noch ausstehen).
        api
          .saveDraft(buildDraft())
          .then(() => qc.invalidateQueries({ queryKey: ['drafts'] }))
          .catch(() => {})
      }
    }
    if (files.length > 0 && !sentRef.current) {
      // Ehrlich bleiben: Entwürfe tragen keine Dateien.
      showToast('Anhänge werden nicht im Entwurf gesichert.', 'error')
    }
    onClose()
  }, [bcc, body, buildDraft, cc, files.length, onClose, qc, showToast, subject, to, touched])

  // App kann den Entwurf sichern, bevor sie den Composer ersetzt (⌘K → neuer Composer).
  useEffect(() => {
    if (!persistRef) return
    persistRef.current = persistAndClose
    return () => {
      persistRef.current = null
    }
  }, [persistRef, persistAndClose])

  const tryClose = useCallback(() => {
    if (!dirty || discardArmed) {
      persistAndClose()
      return
    }
    // Bestätigung ohne confirm(): zweites Esc innerhalb von 3 s schließt.
    setDiscardArmed(true)
    if (discardTimer.current) window.clearTimeout(discardTimer.current)
    discardTimer.current = window.setTimeout(() => setDiscardArmed(false), 3000)
  }, [dirty, discardArmed, persistAndClose])

  useGlobalKeydown((e) => {
    // Liegt ein Modal über dem Composer, gehört Esc dem Modal.
    if (e.key === 'Escape' && !modalAbove) tryClose()
  })

  // Bestätigungs-Timer beim Unmount aufräumen.
  useEffect(
    () => () => {
      if (armTimer.current) window.clearTimeout(armTimer.current)
      if (discardTimer.current) window.clearTimeout(discardTimer.current)
    },
    [],
  )

  // --- Anhänge ---
  const addFiles = useCallback((list: FileList | null) => {
    if (!list || list.length === 0) return
    // FileList ist live: sofort kopieren, bevor `input.value = ''` sie leert —
    // der setFiles-Updater läuft erst nach dem Event-Handler.
    const items = Array.from(list)
    setFiles((prev) => {
      const key = (f: File) => `${f.name}|${f.size}|${f.lastModified}`
      const have = new Set(prev.map(key))
      return [...prev, ...items.filter((f) => !have.has(key(f)))]
    })
  }, [])

  // --- Snippets: ;kürzel + Tab im Body sowie Einfügen über die ⌘K-Palette ---
  const snippetsQuery = useSnippets()

  const onBodyKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== 'Tab') return
    const el = e.currentTarget
    const pos = el.selectionStart
    if (el.selectionEnd !== pos) return
    const m = matchAbbrev(body.slice(0, pos))
    if (!m) return
    const snip = (snippetsQuery.data ?? []).find((s) => s.abbrev === m.abbrev)
    if (!snip) return
    e.preventDefault()
    const text = expandSnippet(snip.text, to[0], namesRef.current ?? undefined)
    setTouched(true)
    setBody(body.slice(0, m.start) + text + body.slice(pos))
    const caret = m.start + text.length
    requestAnimationFrame(() => el.setSelectionRange(caret, caret))
  }

  const insertSnippet = useCallback(
    (snip: Snippet) => {
      const text = expandSnippet(snip.text, to[0], namesRef.current ?? undefined)
      const el = bodyRef.current
      setTouched(true)
      if (!el) {
        setBody((prev) => prev + text)
        return
      }
      const pos = el.selectionStart
      setBody((prev) => prev.slice(0, pos) + text + prev.slice(pos))
      requestAnimationFrame(() => {
        el.focus()
        el.setSelectionRange(pos + text.length, pos + text.length)
      })
    },
    [to],
  )

  useEffect(() => {
    if (!snippetInsertRef) return
    snippetInsertRef.current = insertSnippet
    return () => {
      snippetInsertRef.current = null
    }
  }, [snippetInsertRef, insertSnippet])

  const title = forward ? 'Weiterleiten' : reply ? 'Antworten' : 'Verfassen'

  return (
    <>
      <div className="fade-in fixed inset-0 z-40 bg-black/10" onMouseDown={tryClose} aria-hidden="true" />
      <aside
        onDragOver={(e) => {
          if (e.dataTransfer.types.includes('Files')) {
            e.preventDefault()
            setDragOver(true)
          }
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragOver(false)
        }}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          addFiles(e.dataTransfer.files)
        }}
        className={`slide-in-right fixed inset-y-0 right-0 z-40 flex w-[460px] max-w-full flex-col border-l border-hairline bg-surface shadow-lg ${
          dragOver ? 'ring-2 ring-inset ring-tinte' : ''
        }`}
      >
        <header className="flex items-center gap-2 border-b border-hairline px-4 py-3">
          <h2 className="text-[15px] font-semibold">{title}</h2>
          {refDetail ? (
            <span className="min-w-0 truncate font-mono text-[10.5px] text-muted">zu „{refDetail.subject}“</span>
          ) : null}
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
          {state.mode === 'new' && accounts.length > 1 ? (
            <label className="block">
              <span className={FIELD_LABEL}>Von</span>
              <select value={account} onChange={(e) => edit(setAccount)(e.target.value)} className={`mt-1 ${FIELD_INPUT}`}>
                {accounts.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.name} — {a.address}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <div>
            <span className={FIELD_LABEL}>An</span>
            <RecipientField
              value={to}
              onChange={edit(setTo)}
              onPickContact={rememberName}
              autoFocus={!reply}
              placeholder="adresse@example.org, weitere@example.org"
              ariaLabel="An"
            />
          </div>

          {!ccOpen || !bccOpen ? (
            <div className="flex items-center gap-3">
              {!ccOpen ? (
                <button
                  type="button"
                  onClick={() => setCcOpen(true)}
                  className="font-mono text-[10.5px] text-muted transition hover:text-tinte"
                >
                  + CC
                </button>
              ) : null}
              {!bccOpen ? (
                <button
                  type="button"
                  onClick={() => setBccOpen(true)}
                  className="font-mono text-[10.5px] text-muted transition hover:text-tinte"
                >
                  + BCC
                </button>
              ) : null}
            </div>
          ) : null}

          {ccOpen ? (
            <div>
              <span className={FIELD_LABEL}>CC</span>
              <RecipientField
                value={cc}
                onChange={edit(setCc)}
                onPickContact={rememberName}
                ariaLabel="CC"
              />
            </div>
          ) : null}

          {bccOpen ? (
            <div>
              <span className={FIELD_LABEL}>BCC</span>
              <RecipientField
                value={bcc}
                onChange={edit(setBcc)}
                onPickContact={rememberName}
                ariaLabel="BCC"
              />
            </div>
          ) : null}

          <label className="block">
            <span className={FIELD_LABEL}>Betreff</span>
            <input
              value={subject}
              onChange={(e) => edit(setSubject)(e.target.value)}
              className={`mt-1 ${FIELD_INPUT}`}
            />
          </label>

          <label className="flex min-h-0 flex-1 flex-col">
            <span className={FIELD_LABEL}>Nachricht</span>
            <textarea
              ref={bodyRef}
              autoFocus={!!reply}
              value={body}
              onChange={(e) => edit(setBody)(e.target.value)}
              onKeyDown={onBodyKeyDown}
              className="mt-1 min-h-[180px] flex-1 resize-none rounded border border-hairline bg-paper px-2.5 py-2 text-[13.5px] leading-relaxed focus:border-tinte focus:outline-none"
            />
          </label>

          {forward && forward.attachments.length > 0 ? (
            <label className="flex items-center gap-2 text-[12.5px]">
              <input
                type="checkbox"
                checked={includeAtts}
                onChange={(e) => edit(setIncludeAtts)(e.target.checked)}
                className="accent-tinte"
              />
              Original-Anhänge mitsenden ({forward.attachments.length})
            </label>
          ) : null}

          {/* Anhänge: Dateiauswahl + Drag & Drop auf den Composer */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              title="Dateien anhängen (oder in den Composer ziehen)"
              className="flex items-center gap-1.5 rounded border border-hairline px-2.5 py-1.5 text-[12.5px] transition hover:border-tinte hover:text-tinte"
            >
              <PaperclipIcon size={13} />
              Anhängen
            </button>
            {files.length > 0 ? (
              <span className="font-mono text-[10.5px] text-muted">
                {files.length} {files.length === 1 ? 'Datei' : 'Dateien'} · {formatSize(totalSize)}
              </span>
            ) : (
              <span className="font-mono text-[10px] text-muted">oder Dateien hierher ziehen</span>
            )}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              aria-label="Dateien anhängen"
              onChange={(e) => {
                addFiles(e.target.files)
                e.target.value = ''
              }}
            />
          </div>

          {files.length > 0 ? (
            <ul className="flex flex-wrap gap-1.5">
              {files.map((f, i) => (
                <li
                  key={`${f.name}-${i}`}
                  className="flex items-center gap-1.5 rounded border border-hairline bg-paper px-2 py-1 text-[12px]"
                >
                  <span className="max-w-[180px] truncate">{f.name}</span>
                  <span className="font-mono text-[10px] text-muted">{formatSize(f.size)}</span>
                  <button
                    type="button"
                    aria-label={`${f.name} entfernen`}
                    onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                    className="rounded text-muted transition hover:text-ink"
                  >
                    <XIcon size={11} />
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          {overLimit ? (
            <p className="text-[12px] text-red-700">
              Anhänge zu groß: {formatSize(totalSize)} — Limit 25 MB. Senden ist deaktiviert.
            </p>
          ) : null}

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
          {discardArmed ? (
            <span className="font-mono text-[10.5px] text-red-700">
              {files.length > 0
                ? 'Nochmal Esc: Schließen (Text bleibt als Entwurf, Anhänge gehen verloren)'
                : 'Nochmal Esc: Schließen (Entwurf bleibt)'}
            </span>
          ) : null}
          <button
            type="button"
            onClick={trySend}
            disabled={sendMutation.isPending || overLimit}
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
