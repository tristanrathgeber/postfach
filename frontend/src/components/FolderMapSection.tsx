import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api, errText } from '../lib/api'
import { useToast } from './Toast'

/** Ordner-Zuordnung: je AI-Kategorie ein bestehender Ziel-Ordner statt
 * AI/<Kategorie> (wichtig bei Anbietern mit Ordner-Limit wie GMX). */
export function FolderMapSection({ account }: { account: string | null }) {
  const { showToast } = useToast()
  const query = useQuery({
    queryKey: ['folder-map', account],
    queryFn: () => api.folderMap(account!),
    enabled: account !== null,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })
  // Lokaler State ist nach dem ersten Laden autoritativ (wir schreiben die
  // GANZE Map je Auswahl) — ein Refetch darf einen noch nicht persistierten
  // Eintrag nicht überschreiben. Nur einmal je Konto seeden.
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const seededFor = useRef<string | null>(null)
  useEffect(() => {
    if (query.data && seededFor.current !== account) {
      setMapping(query.data.mapping)
      seededFor.current = account
    }
  }, [query.data, account])

  const saveMutation = useMutation({
    mutationFn: (next: Record<string, string>) => api.putFolderMap(next),
    onSuccess: () => showToast('Ordner-Zuordnung gespeichert.'),
    onError: (e) => showToast(`Speichern fehlgeschlagen: ${errText(e)}`, 'error'),
  })

  const setCategory = (category: string, folder: string) => {
    // Leere Auswahl = Standard (AI/<Kategorie>) → Eintrag entfernen.
    const next = { ...mapping }
    if (folder) next[category] = folder
    else delete next[category]
    setMapping(next)
    saveMutation.mutate(next)
  }

  if (!account) return null

  return (
    <section>
      <h3 className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-muted">Ordner-Zuordnung</h3>
      <p className="mt-0.5 text-[11.5px] text-muted">
        Wohin Postfach archiviert. Ohne Zuordnung wandert eine Kategorie in „AI/&lt;Kategorie&gt;" —
        wähle einen bestehenden Ordner, wenn dein Anbieter keine neuen zulässt (z. B. GMX).
      </p>
      {query.isError ? (
        <p className="mt-2 text-[12px] text-danger">Ordner nicht ladbar: {errText(query.error)}</p>
      ) : !query.data ? (
        <p className="mt-2 font-mono text-[11px] text-muted">Lädt …</p>
      ) : (
        <div className="mt-2 space-y-1.5">
          {query.data.categories.map((cat) => {
            const def = query.data!.defaults[cat] ?? `AI/${cat}`
            // Ein AI/-Standard ohne eigenes Mapping wird von GMX & Co. abgelehnt —
            // solche Zeilen markieren, damit klar ist, was noch zu tun ist.
            const needsAttention = mapping[cat] === undefined && def.startsWith('AI/')
            return (
              <label key={cat} className="flex items-center gap-2 text-[13px]">
                <span className="w-32 shrink-0 truncate">{cat}</span>
                <select
                  value={mapping[cat] ?? ''}
                  onChange={(e) => setCategory(cat, e.target.value)}
                  className={`min-w-0 flex-1 rounded border bg-paper px-2 py-1 text-[12.5px] focus:border-tinte focus:outline-none ${
                    needsAttention ? 'border-warm text-warm' : 'border-hairline'
                  }`}
                >
                  <option value="">
                    Standard → {def}
                    {def.startsWith('AI/') ? ' (Anbieter lehnt evtl. ab)' : ''}
                  </option>
                  {query.data!.folders.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </label>
            )
          })}
        </div>
      )}
    </section>
  )
}
