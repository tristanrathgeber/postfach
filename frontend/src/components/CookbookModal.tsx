import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import type { CookbookModel, PullProgress } from '../lib/types'
import { SpinnerIcon, XIcon } from './Icons'
import { useToast } from './Toast'

/** Modell-Assistent („Cookbook"): scannt das System, empfiehlt das Modell, das
 * am besten zu Postfach passt UND hier läuft, lädt es und aktiviert es (setzt es
 * als Emilias Modell — zugleich fürs Sortieren/Entwerfen, wenn die lokal laufen). */
export function CookbookModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const { showToast } = useToast()
  const query = useQuery({ queryKey: ['cookbook'], queryFn: api.cookbook, staleTime: 5_000 })
  const [pulling, setPulling] = useState<string | null>(null)
  const [progress, setProgress] = useState<PullProgress | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !pulling) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, pulling])

  useEffect(() => () => abortRef.current?.abort(), [])

  const activate = useMutation({
    mutationFn: (model: string) => api.cookbookActivate(model),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['cookbook'] })
      qc.invalidateQueries({ queryKey: ['emilia-status'] })
      showToast(`„${r.active_model}“ ist jetzt Emilias Modell.`)
    },
    onError: (e) => showToast(errText(e), 'error'),
  })

  /** Modell laden (Streaming-Fortschritt), danach optional gleich aktivieren. */
  const pull = async (model: string, thenActivate: boolean) => {
    if (pulling) return
    setPulling(model)
    setProgress({ status: 'Verbindung zu Ollama …' })
    const ctrl = new AbortController()
    abortRef.current = ctrl
    let failed: string | null = null
    try {
      await api.cookbookPull(
        model,
        (e) => {
          if (e.error) failed = e.error
          else setProgress(e)
        },
        ctrl.signal,
      )
    } catch (e) {
      failed = errText(e)
    }
    abortRef.current = null
    setPulling(null)
    setProgress(null)
    if (failed) {
      showToast(failed, 'error')
      return
    }
    await qc.invalidateQueries({ queryKey: ['cookbook'] })
    showToast(`„${model}“ geladen.`)
    if (thenActivate) activate.mutate(model)
  }

  const data = query.data
  const busy = activate.isPending || !!pulling
  const recommended = data?.catalog.find((m) => m.recommended)

  return (
    <div
      className="fade-in fixed inset-0 z-[60] flex items-start justify-center bg-black/20 pt-[7vh]"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !pulling) onClose()
      }}
    >
      <div className="flex max-h-[86vh] w-[660px] max-w-[94vw] flex-col overflow-hidden rounded-lg border border-hairline bg-surface shadow-xl">
        <header className="flex items-center gap-3 border-b border-hairline px-6 py-4">
          <div className="flex-1">
            <h2 className="font-serif text-[22px] italic leading-none">Modell-Assistent</h2>
            <p className="mt-1 text-[12px] text-muted">
              Die beste lokale KI für Postfach auf deinem Mac — finden, laden, einrichten.
            </p>
          </div>
          <button
            type="button"
            onClick={() => !pulling && onClose()}
            aria-label="Schließen"
            className="rounded p-1 text-muted transition hover:text-ink disabled:opacity-40"
            disabled={!!pulling}
          >
            <XIcon size={16} />
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-5">
          {query.isLoading ? (
            <div className="flex items-center gap-2 py-10 text-muted">
              <SpinnerIcon size={15} /> System wird gescannt …
            </div>
          ) : query.isError || !data ? (
            <p className="py-8 text-[13px] text-danger">{errText(query.error)}</p>
          ) : (
            <>
              {/* System */}
              <section className="rounded-lg border border-hairline bg-paper px-4 py-3">
                <p className="font-mono text-[9.5px] uppercase tracking-[0.12em] text-muted">Dein System</p>
                <p className="mt-1 text-[14px]">
                  <span className="font-medium">{data.system.chip}</span>
                  <span className="text-muted">
                    {' · '}
                    {data.system.ram_gb > 0 ? `${data.system.ram_gb} GB RAM` : 'RAM unbekannt'}
                    {' · '}
                    {data.system.cores} Kerne
                  </span>
                </p>
              </section>

              {!data.ollama_reachable && (
                <p className="rounded-lg border border-warm/40 bg-warm-bg px-4 py-2.5 text-[12.5px] text-warm">
                  Ollama läuft gerade nicht. Starte Ollama (die lokale KI-Laufzeit), damit Postfach
                  installierte Modelle sehen, laden und aktivieren kann.
                </p>
              )}

              {data.demo && (
                <p className="rounded-lg border border-hairline bg-tint px-4 py-2.5 text-[12.5px] text-tinte">
                  Demo: Auswahl und Empfehlung sind echt — Laden &amp; Aktivieren funktioniert in der
                  installierten App.
                </p>
              )}

              {/* Empfehlung */}
              {recommended && (
                <section className="rounded-lg border-2 border-tinte bg-tint px-4 py-3.5">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="font-mono text-[9.5px] uppercase tracking-[0.12em] text-tinte">
                      Empfohlen für Postfach
                    </p>
                    <span className="font-mono text-[10px] text-muted">Passung {recommended.fit}%</span>
                  </div>
                  <p className="mt-1 text-[16px] font-semibold">{recommended.label}</p>
                  <p className="mt-0.5 text-[12.5px] text-ink/90">{recommended.note}</p>
                  <div className="mt-2.5">
                    <ModelAction
                      model={recommended}
                      active={data.active_model === recommended.id}
                      demo={data.demo}
                      busy={busy}
                      pullingThis={pulling === recommended.id}
                      progress={pulling === recommended.id ? progress : null}
                      onActivate={() => activate.mutate(recommended.id)}
                      onPull={(then) => pull(recommended.id, then)}
                      primary
                    />
                  </div>
                </section>
              )}

              {/* Katalog */}
              <section>
                <p className="mb-2 font-mono text-[9.5px] uppercase tracking-[0.12em] text-muted">
                  Alle Modelle
                </p>
                <ul className="space-y-2">
                  {data.catalog.map((m) => (
                    <li
                      key={m.id}
                      className={`rounded-lg border px-4 py-3 ${
                        m.recommended ? 'border-tinte/40' : 'border-hairline'
                      } ${!m.runs && !m.installed ? 'opacity-55' : ''}`}
                    >
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="text-[14px] font-medium">{m.label}</span>
                        <span className="font-mono text-[10px] text-muted">{m.params}</span>
                        {data.active_model === m.id && <Badge tone="tinte">Aktiv</Badge>}
                        {m.recommended && data.active_model !== m.id && <Badge tone="tinte">Empfohlen</Badge>}
                        {m.installed && data.active_model !== m.id && <Badge tone="muted">Installiert</Badge>}
                        {!m.runs && !m.installed && <Badge tone="warm">Zu wenig RAM</Badge>}
                        <span className="flex-1" />
                        <span className="font-mono text-[10.5px] text-muted">
                          {m.size_gb} GB · ab {m.min_ram_gb} GB
                        </span>
                      </div>
                      <p className="mt-1 text-[12px] text-muted">{m.strengths.join(' · ')}</p>
                      <div className="mt-2">
                        <ModelAction
                          model={m}
                          active={data.active_model === m.id}
                          demo={data.demo}
                          busy={busy}
                          pullingThis={pulling === m.id}
                          progress={pulling === m.id ? progress : null}
                          onActivate={() => activate.mutate(m.id)}
                          onPull={(then) => pull(m.id, then)}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            </>
          )}
        </div>

        <footer className="flex items-center gap-2 border-t border-hairline px-6 py-3">
          <span className="text-[11.5px] text-muted">
            Aktiv: <span className="font-mono text-ink">{data?.active_model ?? '…'}</span>
          </span>
          <span className="flex-1" />
          <button
            type="button"
            onClick={() => !pulling && onClose()}
            disabled={!!pulling}
            className="rounded-md bg-btn px-3.5 py-1.5 text-[13px] font-medium text-btn-ink transition hover:bg-btn-strong disabled:opacity-50"
          >
            Fertig
          </button>
        </footer>
      </div>
    </div>
  )
}

function Badge({ tone, children }: { tone: 'tinte' | 'muted' | 'warm'; children: React.ReactNode }) {
  const cls =
    tone === 'tinte'
      ? 'bg-tinte/12 text-tinte'
      : tone === 'warm'
        ? 'bg-warm-bg text-warm'
        : 'bg-hover text-muted'
  return <span className={`rounded px-1.5 py-0.5 font-mono text-[9.5px] uppercase tracking-wide ${cls}`}>{children}</span>
}

function pct(p: PullProgress | null): number | null {
  if (!p || typeof p.total !== 'number' || typeof p.completed !== 'number' || p.total <= 0) return null
  return Math.min(100, Math.round((p.completed / p.total) * 100))
}

function ModelAction({
  model,
  active,
  demo,
  busy,
  pullingThis,
  progress,
  onActivate,
  onPull,
  primary,
}: {
  model: CookbookModel
  active: boolean
  demo: boolean
  busy: boolean
  pullingThis: boolean
  progress: PullProgress | null
  onActivate: () => void
  onPull: (thenActivate: boolean) => void
  primary?: boolean
}) {
  if (pullingThis) {
    const p = pct(progress)
    return (
      <div>
        <div className="flex items-center gap-2 text-[12px] text-muted">
          <SpinnerIcon size={13} />
          <span className="truncate">{progress?.status ?? 'Lädt …'}</span>
          {p !== null && <span className="font-mono">{p}%</span>}
        </div>
        <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-hover">
          <div
            className="h-full rounded-full bg-tinte transition-[width] duration-300"
            style={{ width: p !== null ? `${p}%` : '30%' }}
          />
        </div>
      </div>
    )
  }

  if (active) {
    return <span className="text-[12.5px] font-medium text-success">✓ Aktiv — Emilia nutzt dieses Modell.</span>
  }

  const btn = (label: string, onClick: () => void, kind: 'primary' | 'ghost') => (
    <button
      type="button"
      onClick={onClick}
      disabled={busy || demo}
      className={
        kind === 'primary'
          ? 'rounded-md bg-btn px-3.5 py-1.5 text-[13px] font-medium text-btn-ink transition hover:bg-btn-strong disabled:opacity-50'
          : 'rounded-md border border-hairline px-3 py-1.5 text-[12.5px] text-ink transition hover:border-muted disabled:opacity-50'
      }
    >
      {label}
    </button>
  )

  if (model.installed) {
    return btn('Aktivieren', onActivate, primary ? 'primary' : 'ghost')
  }
  if (!model.runs) {
    return <span className="text-[12px] text-muted">Läuft auf diesem Mac nicht flüssig.</span>
  }
  // Nicht installiert, läuft: laden. Bei der Empfehlung gleich mit Aktivieren.
  return btn(primary ? 'Laden & aktivieren' : 'Laden', () => onPull(!!primary), primary ? 'primary' : 'ghost')
}
