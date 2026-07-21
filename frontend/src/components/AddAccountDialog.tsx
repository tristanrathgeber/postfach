import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import type { AccountTestResult } from '../lib/types'
import { SpinnerIcon, XIcon } from './Icons'
import { useToast } from './Toast'

/** Konto einrichten ohne YAML: Provider wählen (füllt Host/Port), testen,
 * speichern. Das Passwort geht direkt in den macOS-Schlüsselbund. */
export function AddAccountDialog({ onClose }: { onClose: () => void }) {
  const { showToast } = useToast()
  const qc = useQueryClient()
  const providersQuery = useQuery({ queryKey: ['providers'], queryFn: api.providers, staleTime: Infinity })
  const providers = useMemo(() => providersQuery.data ?? [], [providersQuery.data])

  const [providerId, setProviderId] = useState('gmx')
  const [name, setName] = useState('')
  const [address, setAddress] = useState('')
  const [password, setPassword] = useState('')
  const [imapHost, setImapHost] = useState('')
  const [imapPort, setImapPort] = useState(993)
  const [smtpHost, setSmtpHost] = useState('')
  const [smtpPort, setSmtpPort] = useState(587)
  const [testResult, setTestResult] = useState<AccountTestResult | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const preset = providers.find((p) => p.id === providerId)
  const isCustom = providerId === 'custom'

  // Sobald die Presets geladen sind, den Default (GMX) einmal übernehmen —
  // ohne das blieben Host/Port beim ersten Öffnen leer.
  useEffect(() => {
    if (preset && !isCustom && !imapHost) {
      setImapHost(preset.imap_host)
      setImapPort(preset.imap_port)
      setSmtpHost(preset.smtp_host)
      setSmtpPort(preset.smtp_port)
    }
  }, [preset, isCustom, imapHost])

  // Provider wechseln → Host/Port aus dem Preset übernehmen (custom bleibt manuell).
  const selectProvider = (id: string) => {
    setProviderId(id)
    setTestResult(null)
    const p = providers.find((x) => x.id === id)
    if (p && id !== 'custom') {
      setImapHost(p.imap_host)
      setImapPort(p.imap_port)
      setSmtpHost(p.smtp_host)
      setSmtpPort(p.smtp_port)
    }
  }

  const body = () => ({
    provider: providerId === 'gmail' ? 'gmail' : 'imap',
    address: address.trim(),
    imap_host: imapHost.trim(),
    imap_port: imapPort,
    smtp_host: smtpHost.trim(),
    smtp_port: smtpPort,
    password,
  })

  const testMutation = useMutation({
    mutationFn: () => api.accountTest(body()),
    onSuccess: (result) => setTestResult(result),
    onError: (e) => showToast(`Test fehlgeschlagen: ${errText(e)}`, 'error'),
  })

  const addMutation = useMutation({
    mutationFn: () => api.accountAdd({ ...body(), name: name.trim() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['accounts'] })
      showToast('Konto gespeichert. Live-Benachrichtigungen ab dem nächsten Neustart.')
      onClose()
    },
    onError: (e) => showToast(`Speichern fehlgeschlagen: ${errText(e)}`, 'error'),
  })

  const canSubmit = name.trim() && address.includes('@') && password && (isCustom ? imapHost.trim() : true)
  const testOk = testResult !== null && testResult.ok

  return (
    <div
      className="fade-in fixed inset-0 z-[60] flex items-start justify-center bg-black/20 pt-[8vh]"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="w-[520px] max-w-[92vw] rounded-lg border border-hairline bg-surface p-7 shadow-xl">
        <div className="flex items-center">
          <h2 className="flex-1 font-serif text-[22px] italic">Konto hinzufügen</h2>
          <button type="button" onClick={onClose} aria-label="Schließen" className="rounded p-1 text-muted transition hover:text-ink">
            <XIcon size={16} />
          </button>
        </div>

        <div className="mt-4 space-y-3">
          <label className="block">
            <span className="font-mono text-[10px] uppercase tracking-wide text-muted">Anbieter</span>
            <select
              value={providerId}
              onChange={(e) => selectProvider(e.target.value)}
              className="mt-1 w-full rounded border border-hairline bg-paper px-2.5 py-1.5 text-[13px] focus:border-tinte focus:outline-none"
            >
              {providers.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
            {preset?.note ? <span className="mt-1 block text-[11.5px] text-muted">{preset.note}</span> : null}
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="font-mono text-[10px] uppercase tracking-wide text-muted">Name (frei)</span>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="z. B. Privat"
                className="mt-1 w-full rounded border border-hairline bg-paper px-2.5 py-1.5 text-[13px] focus:border-tinte focus:outline-none" />
            </label>
            <label className="block">
              <span className="font-mono text-[10px] uppercase tracking-wide text-muted">E-Mail</span>
              <input value={address} onChange={(e) => { setAddress(e.target.value); setTestResult(null) }} type="email" placeholder="du@gmx.de"
                className="mt-1 w-full rounded border border-hairline bg-paper px-2.5 py-1.5 text-[13px] focus:border-tinte focus:outline-none" />
            </label>
          </div>

          <label className="block">
            <span className="font-mono text-[10px] uppercase tracking-wide text-muted">Passwort (bleibt im Schlüsselbund)</span>
            <input value={password} onChange={(e) => { setPassword(e.target.value); setTestResult(null) }} type="password" autoComplete="off"
              className="mt-1 w-full rounded border border-hairline bg-paper px-2.5 py-1.5 text-[13px] focus:border-tinte focus:outline-none" />
          </label>

          <details open={isCustom} className="rounded border border-hairline bg-paper px-3 py-2">
            <summary className="cursor-pointer font-mono text-[10.5px] uppercase tracking-wide text-muted">Server (aus dem Anbieter vorausgefüllt)</summary>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <label className="block">
                <span className="text-[11px] text-muted">IMAP-Host</span>
                <input value={imapHost} onChange={(e) => { setImapHost(e.target.value); setTestResult(null) }} disabled={!isCustom}
                  className="mt-0.5 w-full rounded border border-hairline bg-surface px-2 py-1 text-[12.5px] disabled:opacity-60 focus:border-tinte focus:outline-none" />
              </label>
              <label className="block">
                <span className="text-[11px] text-muted">IMAP-Port</span>
                <input value={imapPort} onChange={(e) => { setImapPort(Number(e.target.value)); setTestResult(null) }} disabled={!isCustom} type="number"
                  className="mt-0.5 w-full rounded border border-hairline bg-surface px-2 py-1 text-[12.5px] disabled:opacity-60 focus:border-tinte focus:outline-none" />
              </label>
              <label className="block">
                <span className="text-[11px] text-muted">SMTP-Host</span>
                <input value={smtpHost} onChange={(e) => { setSmtpHost(e.target.value); setTestResult(null) }} disabled={!isCustom}
                  className="mt-0.5 w-full rounded border border-hairline bg-surface px-2 py-1 text-[12.5px] disabled:opacity-60 focus:border-tinte focus:outline-none" />
              </label>
              <label className="block">
                <span className="text-[11px] text-muted">SMTP-Port</span>
                <input value={smtpPort} onChange={(e) => { setSmtpPort(Number(e.target.value)); setTestResult(null) }} disabled={!isCustom} type="number"
                  className="mt-0.5 w-full rounded border border-hairline bg-surface px-2 py-1 text-[12.5px] disabled:opacity-60 focus:border-tinte focus:outline-none" />
              </label>
            </div>
          </details>

          {testResult ? (
            'demo' in testResult ? (
              <p className="rounded bg-tint px-3 py-2 text-[12.5px] text-tinte">Demo-Modus: Verbindungstest übersprungen.</p>
            ) : testResult.ok ? (
              <p className="rounded bg-success-bg px-3 py-2 text-[12.5px] text-success">Verbindung erfolgreich — IMAP und SMTP erreichbar.</p>
            ) : (
              <p className="rounded bg-danger-bg px-3 py-2 text-[12.5px] text-danger">
                {testResult.imap ? 'SMTP' : 'IMAP'} fehlgeschlagen{testResult.error ? `: ${testResult.error}` : ''}
              </p>
            )
          ) : null}
        </div>

        <div className="mt-5 flex items-center gap-2">
          <button
            type="button"
            onClick={() => testMutation.mutate()}
            disabled={!canSubmit || testMutation.isPending}
            className="flex items-center gap-1.5 rounded border border-hairline px-3 py-1.5 text-[13px] transition enabled:hover:border-tinte enabled:hover:text-tinte disabled:opacity-40"
          >
            {testMutation.isPending ? <SpinnerIcon size={12} /> : null}
            Verbindung testen
          </button>
          <span className="flex-1" />
          <button type="button" onClick={onClose} className="rounded px-3 py-1.5 text-[13px] text-muted transition hover:text-ink">
            Abbrechen
          </button>
          <button
            type="button"
            onClick={() => addMutation.mutate()}
            disabled={!canSubmit || !testOk || addMutation.isPending}
            title={testOk ? 'Konto speichern' : 'Bitte zuerst die Verbindung testen'}
            className="flex items-center gap-1.5 rounded bg-btn px-3 py-1.5 text-[13px] font-medium text-white transition hover:bg-btn-strong disabled:opacity-40"
          >
            {addMutation.isPending ? <SpinnerIcon size={12} /> : null}
            Speichern
          </button>
        </div>
      </div>
    </div>
  )
}
