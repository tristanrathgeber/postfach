import { useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import { SpinnerIcon, XIcon } from './Icons'

/** Über Postfach: Version, verifizierbare Privatheit (ALLE ausgehenden Ziele,
 * inkl. Cloud-LLM falls aktiv) und ein MANUELLER Update-Check. */
export function AboutDialog({ onClose }: { onClose: () => void }) {
  const versionQuery = useQuery({ queryKey: ['version'], queryFn: () => api.version(false), staleTime: Infinity })
  const netQuery = useQuery({ queryKey: ['network-info'], queryFn: api.networkInfo, staleTime: 60_000 })
  const checkMutation = useMutation({ mutationFn: () => api.version(true) })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const version = versionQuery.data?.version ?? '…'
  const net = netQuery.data
  const check = checkMutation.data

  return (
    <div
      className="fade-in fixed inset-0 z-[60] flex items-start justify-center bg-black/20 pt-[10vh]"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="w-[480px] max-w-[92vw] rounded-lg border border-hairline bg-surface p-7 shadow-xl">
        <div className="flex items-center">
          <h2 className="flex-1 font-serif text-[22px] italic">Über Postfach</h2>
          <button type="button" onClick={onClose} aria-label="Schließen" className="rounded p-1 text-muted transition hover:text-ink">
            <XIcon size={16} />
          </button>
        </div>

        <p className="mt-3 text-[13px] text-ink">
          Version <span className="font-mono">{version}</span> · lokal auf deinem Mac · MIT-Lizenz
        </p>

        <div className="mt-4">
          <p className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Verifizierbare Privatheit</p>
          <p className="mt-1 text-[12.5px] leading-relaxed text-ink">
            Keine Telemetrie, kein Analytics, kein Phone-Home. Die vollständige Liste der Server,
            mit denen Postfach spricht:
          </p>
          <ul className="mt-2 space-y-1.5 text-[12px]">
            {net?.targets.map((t) => (
              <li key={`${t.host}:${t.port}`} className="leading-snug">
                <span className={`font-mono ${t.cloud ? 'text-danger' : 'text-muted'}`}>
                  {t.host}:{t.port}
                </span>
                <span className="text-ink"> — {t.why}</span>
              </li>
            ))}
            {net && net.targets.length === 0 ? (
              <li className="text-muted">Noch kein Konto — bis dahin geht nichts nach außen.</li>
            ) : null}
          </ul>
          {net?.cloud_llm ? (
            <p className="mt-2 rounded bg-danger-bg px-2.5 py-1.5 text-[11.5px] text-danger">
              KI-Cloud aktiv: Sortieren/Entwürfe schicken Mail-Inhalte an {net.cloud_llm.host}.
              Für rein lokal <span className="font-mono">sort_local</span> + <span className="font-mono">draft_local</span> aktivieren.
            </p>
          ) : null}
        </div>

        <div className="mt-5 flex items-center gap-2">
          <button
            type="button"
            onClick={() => checkMutation.mutate()}
            disabled={checkMutation.isPending}
            title="Fragt einmalig GitHub nach der neuesten Version — nur auf diesen Klick."
            className="flex items-center gap-1.5 rounded border border-hairline px-3 py-1.5 text-[12.5px] transition enabled:hover:border-tinte enabled:hover:text-tinte disabled:opacity-50"
          >
            {checkMutation.isPending ? <SpinnerIcon size={12} /> : null}
            Nach Updates suchen
          </button>
          <span className="min-w-0 flex-1 text-[12px]">
            {checkMutation.isError ? (
              <span className="text-danger">Fehlgeschlagen: {errText(checkMutation.error)}</span>
            ) : check?.update_available ? (
              <a
                href="https://github.com/tristanrathgeber/postfach/releases/latest"
                target="_blank"
                rel="noreferrer"
                className="text-tinte hover:underline"
              >
                Neue Version {check.latest} verfügbar →
              </a>
            ) : check?.checked ? (
              <span className="text-muted">Du hast die neueste Version.</span>
            ) : check ? (
              <span className="text-muted">GitHub nicht erreichbar — später erneut versuchen.</span>
            ) : (
              <span className="text-muted">Wird nie automatisch geprüft.</span>
            )}
          </span>
        </div>
      </div>
    </div>
  )
}
