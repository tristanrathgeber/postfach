import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import { useGlobalKeydown } from '../lib/keyboard'
import { FIELD_INPUT, FIELD_LABEL } from '../lib/form'
import { useSettings, useSnippets } from '../hooks/useLocalStores'
import type { Account, Snippet } from '../lib/types'
import { useToast } from './Toast'
import { SpinnerIcon, XIcon } from './Icons'
import { FolderMapSection } from './FolderMapSection'
import { AccountsSection } from './AccountsSection'
import { PALETTES } from '../lib/themes'

type Appearance = {
  theme: import('../hooks/usePreferences').Theme
  onThemeChange: (t: import('../hooks/usePreferences').Theme) => void
  density: import('../hooks/usePreferences').Density
  onDensityChange: (d: import('../hooks/usePreferences').Density) => void
  palette: import('../lib/themes').PaletteId
  onPaletteChange: (p: import('../lib/themes').PaletteId) => void
  accent: string | null
  onAccentChange: (a: string | null) => void
}

type SettingsModalProps = Appearance & {
  accounts: Account[]
  onClose: () => void
}

/** Einstellungen (Zahnrad): Signaturen pro Konto + Snippets — Speichern per PUT beim Schließen. */
export function SettingsModal({ accounts, onClose, ...appearance }: SettingsModalProps) {
  const settingsQuery = useSettings()
  const snippetsQuery = useSnippets()
  const ready = settingsQuery.data !== undefined && snippetsQuery.data !== undefined

  if (ready) {
    return (
      <SettingsForm
        accounts={accounts}
        {...appearance}
        initialSignatures={settingsQuery.data.signatures}
        initialNotifications={settingsQuery.data.notifications}
        initialUndoSeconds={settingsQuery.data.undo_seconds}
        initialAiEnabled={settingsQuery.data.ai_enabled}
        initialSnippets={snippetsQuery.data}
        onClose={onClose}
      />
    )
  }

  return (
    <ModalOverlay onDismiss={onClose}>
      <div className="w-[620px] max-w-[92vw] rounded-lg border border-hairline bg-surface p-8 shadow-xl">
        {settingsQuery.isError || snippetsQuery.isError ? (
          <div className="flex items-center gap-3">
            <p className="flex-1 text-[13px] text-danger">
              Einstellungen nicht ladbar: {errText(settingsQuery.error ?? snippetsQuery.error)}
            </p>
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-hairline px-2.5 py-1.5 text-[12.5px] transition hover:border-tinte hover:text-tinte"
            >
              Schließen
            </button>
          </div>
        ) : (
          <p className="fade-in text-center font-mono text-[11px] text-muted">Lädt …</p>
        )}
      </div>
    </ModalOverlay>
  )
}

function ModalOverlay({ onDismiss, children }: { onDismiss: () => void; children: React.ReactNode }) {
  return (
    <div
      className="fade-in fixed inset-0 z-50 flex items-start justify-center bg-black/20 pt-[10vh]"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onDismiss()
      }}
    >
      {children}
    </div>
  )
}

function SettingsForm({
  accounts,
  theme,
  onThemeChange,
  density,
  onDensityChange,
  palette,
  onPaletteChange,
  accent,
  onAccentChange,
  initialSignatures,
  initialNotifications,
  initialUndoSeconds,
  initialAiEnabled,
  initialSnippets,
  onClose,
}: Appearance & {
  accounts: Account[]
  initialSignatures: Record<string, string>
  initialNotifications: Record<string, boolean>
  initialUndoSeconds: number
  initialAiEnabled: boolean
  initialSnippets: Snippet[]
  onClose: () => void
}) {
  const { showToast } = useToast()
  const qc = useQueryClient()
  const [signatures, setSignatures] = useState<Record<string, string>>(initialSignatures)
  const [notifications, setNotifications] = useState<Record<string, boolean>>(initialNotifications)
  const [undoSeconds, setUndoSeconds] = useState<number>(initialUndoSeconds)
  const [aiEnabled, setAiEnabled] = useState<boolean>(initialAiEnabled)
  const [snippets, setSnippets] = useState<Snippet[]>(initialSnippets)

  const cleanedSnippets = snippets
    .map((s) => ({ abbrev: s.abbrev.trim(), title: s.title.trim(), text: s.text }))
    .filter((s) => s.abbrev || s.title || s.text.trim())

  const settingsDirty =
    JSON.stringify(signatures) !== JSON.stringify(initialSignatures) ||
    JSON.stringify(notifications) !== JSON.stringify(initialNotifications) ||
    undoSeconds !== initialUndoSeconds ||
    aiEnabled !== initialAiEnabled
  const snippetsDirty = JSON.stringify(cleanedSnippets) !== JSON.stringify(initialSnippets)

  const saveMutation = useMutation({
    mutationFn: () =>
      Promise.all([
        settingsDirty ? api.putSettings({ signatures, notifications, undo_seconds: undoSeconds, ai_enabled: aiEnabled }) : Promise.resolve({ ok: true as const }),
        snippetsDirty ? api.putSnippets(cleanedSnippets) : Promise.resolve({ ok: true as const }),
      ]),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings'] })
      qc.invalidateQueries({ queryKey: ['snippets'] })
      showToast('Einstellungen gespeichert.')
      onClose()
    },
    // Bei Fehler offen bleiben — nichts geht verloren, erneut versuchbar.
    onError: (e) => showToast(`Speichern fehlgeschlagen: ${errText(e)}`, 'error'),
  })

  const requestClose = () => {
    if (saveMutation.isPending) return
    if (settingsDirty || snippetsDirty) saveMutation.mutate()
    else onClose()
  }

  useGlobalKeydown((e) => {
    if (e.key === 'Escape') {
      e.stopPropagation()
      requestClose()
    }
  })

  const updateSnippet = (index: number, patch: Partial<Snippet>) =>
    setSnippets((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)))

  return (
    <ModalOverlay onDismiss={requestClose}>
      <div className="flex max-h-[80vh] w-[620px] max-w-[92vw] flex-col overflow-hidden rounded-lg border border-hairline bg-surface shadow-xl">
      <header className="flex items-center gap-2 border-b border-hairline px-4 py-3">
        <h2 className="text-[15px] font-semibold">Einstellungen</h2>
        <span className="flex-1" />
        <button
          type="button"
          onClick={requestClose}
          title="Schließen (Esc) — speichert Änderungen"
          aria-label="Schließen"
          className="rounded p-1 text-muted transition hover:text-ink"
        >
          <XIcon size={15} />
        </button>
      </header>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4">
        {/* Erscheinungsbild: Theme + Dichte (lokal, sofort) */}
        <section>
          <h3 className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Erscheinungsbild</h3>
          <div className="mt-2 flex flex-wrap items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-[13px]">Theme</span>
              <div className="flex rounded border border-hairline p-0.5">
                {(['system', 'light', 'dark'] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => onThemeChange(t)}
                    className={`rounded px-2.5 py-1 text-[12px] transition ${theme === t ? 'bg-tint text-tinte' : 'text-muted hover:text-ink'}`}
                  >
                    {t === 'system' ? 'System' : t === 'light' ? 'Hell' : 'Dunkel'}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[13px]">Dichte</span>
              <div className="flex rounded border border-hairline p-0.5">
                {(['comfortable', 'compact'] as const).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => onDensityChange(d)}
                    className={`rounded px-2.5 py-1 text-[12px] transition ${density === d ? 'bg-tint text-tinte' : 'text-muted hover:text-ink'}`}
                  >
                    {d === 'comfortable' ? 'Komfortabel' : 'Kompakt'}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <p className="mt-1.5 text-[11.5px] text-muted">Dunkel lässt die Original-Mail auf hellem Papier — E-Mails sind für Weiß gestaltet.</p>

          {/* Farbthema: kuratierte Paletten + optionaler eigener Akzent */}
          <div className="mt-4">
            <span className="text-[13px]">Farbthema</span>
            <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-6">
              {PALETTES.map((p) => {
                const active = palette === p.id
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => onPaletteChange(p.id)}
                    title={p.hint}
                    aria-pressed={active}
                    className={`flex flex-col items-center gap-1.5 rounded-lg border p-2 text-center transition ${
                      active ? 'border-tinte bg-tint' : 'border-hairline hover:border-muted'
                    }`}
                  >
                    <span
                      className="flex h-7 w-full items-center justify-center gap-1 rounded"
                      style={{ background: p.swatch[0] }}
                    >
                      <span className="h-3.5 w-3.5 rounded-full" style={{ background: p.swatch[1] }} />
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: p.swatch[2] }} />
                    </span>
                    <span className={`text-[11px] ${active ? 'text-tinte' : 'text-muted'}`}>{p.label}</span>
                  </button>
                )
              })}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-[13px]">
                <span>Eigener Akzent</span>
                <input
                  type="color"
                  value={accent ?? '#2440b3'}
                  onChange={(e) => onAccentChange(e.target.value)}
                  className="h-7 w-9 cursor-pointer rounded border border-hairline bg-surface p-0.5"
                  aria-label="Akzentfarbe wählen"
                />
              </label>
              {accent && (
                <button
                  type="button"
                  onClick={() => onAccentChange(null)}
                  className="rounded px-2 py-1 text-[12px] text-muted transition hover:text-ink"
                >
                  Zurücksetzen
                </button>
              )}
              <span className="text-[11.5px] text-muted">
                {accent ? 'Überschreibt den Palettenakzent.' : 'Aus — die Palette bestimmt den Akzent.'}
              </span>
            </div>
          </div>
        </section>

        {/* Signaturen pro Konto */}
        <section>
          <h3 className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Signaturen</h3>
          <p className="mt-0.5 text-[11.5px] text-muted">
            Wird beim Verfassen automatisch mit „-- “-Trenner angefügt, bei Antworten vor dem Zitat.
          </p>
          <div className="mt-2 space-y-3">
            {accounts.length === 0 ? (
              <p className="text-[12px] text-muted">Keine Konten konfiguriert.</p>
            ) : (
              accounts.map((a) => (
                <label key={a.name} className="block">
                  <span className={FIELD_LABEL}>
                    {a.name} — {a.address}
                  </span>
                  <textarea
                    value={signatures[a.name] ?? ''}
                    onChange={(e) => setSignatures((prev) => ({ ...prev, [a.name]: e.target.value }))}
                    rows={3}
                    placeholder="Keine Signatur"
                    className={`mt-1 resize-y ${FIELD_INPUT}`}
                  />
                </label>
              ))
            )}
          </div>
        </section>

        {/* Benachrichtigungen */}
        <section>
          <h3 className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Benachrichtigungen</h3>
          <p className="mt-0.5 text-[11.5px] text-muted">
            Native macOS-Meldung bei neuer Mail (Absender + Betreff) — pro Konto schaltbar.
          </p>
          <div className="mt-2 space-y-1.5">
            {accounts.map((a) => (
              <label key={a.name} className="flex cursor-pointer items-center gap-2 text-[13px]">
                <input
                  type="checkbox"
                  checked={notifications[a.name] ?? true}
                  onChange={(e) => setNotifications((prev) => ({ ...prev, [a.name]: e.target.checked }))}
                  className="accent-tinte"
                />
                {a.name}
                <span className="font-mono text-[10.5px] text-muted">{a.address}</span>
              </label>
            ))}
          </div>
        </section>

        {/* Senden */}
        <section>
          <h3 className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Senden</h3>
          <p className="mt-0.5 text-[11.5px] text-muted">
            Rückgängig-Fenster: Mails gehen erst nach dieser Zeit wirklich raus.
          </p>
          <label className="mt-2 flex items-center gap-2 text-[13px]">
            Rückgängig möglich für
            <select
              value={undoSeconds}
              onChange={(e) => setUndoSeconds(Number(e.target.value))}
              aria-label="Undo-Fenster"
              className="rounded border border-hairline bg-paper px-2 py-1 text-[13px] focus:border-tinte focus:outline-none"
            >
              <option value={0}>aus — sofort senden</option>
              <option value={10}>10 Sekunden</option>
              <option value={15}>15 Sekunden</option>
              <option value={20}>20 Sekunden</option>
              <option value={30}>30 Sekunden</option>
            </select>
          </label>
        </section>

        {/* Emilia & KI — der globale Schalter: aus heißt aus (Anti-Superhuman) */}
        <section>
          <h3 className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Emilia &amp; KI</h3>
          <p className="mt-0.5 text-[11.5px] text-muted">
            Ein Schalter für alles: Sortieren, Entwürfe, Chat, Umformulieren, KI-Suche. Alles läuft
            lokal — und aus heißt wirklich aus. Bereits vergebene Kategorien bleiben sichtbar.
          </p>
          <label className="mt-2 flex items-center gap-2 text-[13px]">
            <input
              type="checkbox"
              checked={aiEnabled}
              onChange={(e) => setAiEnabled(e.target.checked)}
              className="h-3.5 w-3.5 accent-tinte"
            />
            KI aktiviert
          </label>
        </section>

        {/* Konten (verwaltete löschbar) + Ordner-Zuordnung */}
        <AccountsSection accounts={accounts} />
        <FolderMapSection account={accounts[0]?.name ?? null} />

        {/* Snippets */}
        <section>
          <h3 className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Snippets</h3>
          <p className="mt-0.5 text-[11.5px] text-muted">
            Im Body per ;kürzel + Tab oder über ⌘K einfügen. Variablen: {'{vorname}'}, {'{datum}'}.
          </p>
          <div className="mt-2 space-y-2">
            {snippets.map((s, i) => (
              <div key={i} className="flex items-start gap-2">
                <input
                  value={s.abbrev}
                  onChange={(e) => updateSnippet(i, { abbrev: e.target.value })}
                  placeholder="kürzel"
                  aria-label={`Snippet ${i + 1}: Kürzel`}
                  className={`w-[110px] shrink-0 font-mono ${FIELD_INPUT}`}
                />
                <input
                  value={s.title}
                  onChange={(e) => updateSnippet(i, { title: e.target.value })}
                  placeholder="Titel"
                  aria-label={`Snippet ${i + 1}: Titel`}
                  className={`w-[150px] shrink-0 ${FIELD_INPUT}`}
                />
                <textarea
                  value={s.text}
                  onChange={(e) => updateSnippet(i, { text: e.target.value })}
                  placeholder="Text"
                  aria-label={`Snippet ${i + 1}: Text`}
                  rows={1}
                  className={`min-w-0 flex-1 resize-y ${FIELD_INPUT}`}
                />
                <button
                  type="button"
                  onClick={() => setSnippets((prev) => prev.filter((_, j) => j !== i))}
                  title="Snippet entfernen"
                  aria-label={`Snippet ${i + 1} entfernen`}
                  className="mt-1.5 rounded p-1 text-muted transition hover:text-ink"
                >
                  <XIcon size={13} />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => setSnippets((prev) => [...prev, { abbrev: '', title: '', text: '' }])}
              className="font-mono text-[10.5px] text-muted transition hover:text-tinte"
            >
              + Snippet
            </button>
          </div>
        </section>
      </div>

      <footer className="flex items-center gap-2 border-t border-hairline px-4 py-3">
        <span className="font-mono text-[10px] text-muted">
          {settingsDirty || snippetsDirty ? 'Ungespeicherte Änderungen' : 'Alles gespeichert'}
        </span>
        <span className="flex-1" />
        <button
          type="button"
          onClick={requestClose}
          disabled={saveMutation.isPending}
          className="flex items-center gap-1.5 rounded bg-btn px-3.5 py-1.5 text-[12.5px] font-medium text-white transition hover:bg-btn-strong disabled:opacity-60"
        >
          {saveMutation.isPending ? <SpinnerIcon size={12} /> : null}
          Fertig
        </button>
      </footer>
      </div>
    </ModalOverlay>
  )
}
