import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import type { Account } from '../lib/types'
import { useToast } from './Toast'

/** Konten-Übersicht in den Einstellungen: per UI angelegte Konten sind
 * löschbar (Zweitklick-Bestätigung), config.yaml-Konten schreibgeschützt. */
export function AccountsSection({ accounts }: { accounts: Account[] }) {
  const { showToast } = useToast()
  const qc = useQueryClient()
  const [armed, setArmed] = useState<string | null>(null)
  const armTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => () => { if (armTimer.current) clearTimeout(armTimer.current) }, [])

  const deleteMutation = useMutation({
    mutationFn: (name: string) => api.accountDelete(name),
    onSuccess: (_r, name) => {
      qc.invalidateQueries({ queryKey: ['accounts'] })
      showToast(`Konto „${name}" entfernt.`)
    },
    onError: (e) => showToast(`Entfernen fehlgeschlagen: ${errText(e)}`, 'error'),
  })

  return (
    <section>
      <h3 className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Konten</h3>
      <p className="mt-0.5 text-[11.5px] text-muted">
        Per „+ Konto hinzufügen" angelegte Konten liegen mit Passwort im macOS-Schlüsselbund und
        sind hier entfernbar. Aus der config.yaml stammende Konten bleiben unangetastet.
      </p>
      <div className="mt-2 space-y-1">
        {accounts.map((a) => (
          <div key={a.name} className="flex items-center gap-2 text-[13px]">
            <span className="min-w-0 flex-1 truncate">
              {a.name} <span className="font-mono text-[10.5px] text-muted">{a.address}</span>
            </span>
            {a.managed ? (
              <button
                type="button"
                disabled={deleteMutation.isPending}
                onClick={() => {
                  if (armed === a.name) {
                    setArmed(null)
                    deleteMutation.mutate(a.name)
                  } else {
                    setArmed(a.name)
                    if (armTimer.current) clearTimeout(armTimer.current)
                    armTimer.current = setTimeout(() => setArmed((c) => (c === a.name ? null : c)), 4000)
                  }
                }}
                className={`shrink-0 rounded border px-2 py-0.5 text-[11.5px] transition ${
                  armed === a.name ? 'border-red-700 bg-red-700 text-white' : 'border-hairline text-muted hover:border-red-700 hover:text-red-800'
                }`}
              >
                {armed === a.name ? 'Wirklich entfernen?' : 'Entfernen'}
              </button>
            ) : (
              <span className="shrink-0 font-mono text-[10px] text-muted">config.yaml</span>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
