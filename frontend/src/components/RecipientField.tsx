import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Contact } from '../lib/types'
import { XIcon } from './Icons'

type RecipientFieldProps = {
  /** Bereits erfasste Adressen (Chips). */
  value: string[]
  onChange: (next: string[]) => void
  /** Wird bei Auswahl aus dem Kontakte-Dropdown gerufen (z. B. für {vorname}-Snippets). */
  onPickContact?: (contact: Contact) => void
  autoFocus?: boolean
  placeholder?: string
  ariaLabel: string
}

/** Tipptext in Adressen zerlegen (Komma/Semikolon, auch beim Einfügen). */
function splitAddrs(raw: string): string[] {
  return raw
    .split(/[,;]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

/**
 * Chip-Empfängerfeld mit Kontakte-Autocomplete (GET /api/contacts?q=,
 * debounced 150 ms ab 2 Zeichen). Enter/Komma/Tab übernehmen den Tipptext,
 * Backspace entfernt den letzten Chip, Pfeiltasten + Enter wählen Vorschläge.
 */
export function RecipientField({ value, onChange, onPickContact, autoFocus, placeholder, ariaLabel }: RecipientFieldProps) {
  const [text, setText] = useState('')
  const [query, setQuery] = useState('') // debounced Suchbegriff
  const [open, setOpen] = useState(false)
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  // Debounce 150 ms: Tipptext → Suchbegriff
  useEffect(() => {
    const t = window.setTimeout(() => setQuery(text.trim()), 150)
    return () => window.clearTimeout(t)
  }, [text])

  const enabled = query.length >= 2
  const contactsQuery = useQuery({
    queryKey: ['contacts', query],
    queryFn: () => api.contacts(query),
    enabled,
    staleTime: 60_000,
  })
  // Adressvergleiche immer case-insensitiv — Header liefern Original-Case,
  // Kontakte sind lowercase gespeichert; sonst entstehen Doppel-Empfänger.
  const lower = new Set(value.map((a) => a.toLowerCase()))
  const suggestions = enabled ? (contactsQuery.data ?? []).filter((c) => !lower.has(c.addr.toLowerCase())) : []
  const dropdownOpen = open && suggestions.length > 0

  // Neue Vorschlagsliste → Auswahl zurück an den Anfang
  useEffect(() => {
    setActiveIdx(0)
  }, [query])

  const addAddrs = (addrs: string[]) => {
    const next = [...value]
    const have = new Set(next.map((a) => a.toLowerCase()))
    for (const a of addrs) {
      const key = a.toLowerCase()
      if (!have.has(key)) {
        have.add(key)
        next.push(a)
      }
    }
    if (next.length !== value.length) onChange(next)
  }

  const commitTyped = () => {
    // Nur plausible Adressen (mit @) werden Chips — Suchfragmente wie "mar"
    // bleiben als Tipptext stehen statt still als Müll-Empfänger zu enden.
    const parts = splitAddrs(text)
    const valid = parts.filter((p) => p.includes('@'))
    if (valid.length > 0) addAddrs(valid)
    setText(parts.filter((p) => !p.includes('@')).join(', '))
    if (valid.length > 0 || parts.length === 0) setOpen(false)
  }

  const pick = (contact: Contact) => {
    addAddrs([contact.addr])
    onPickContact?.(contact)
    setText('')
    setOpen(false)
    inputRef.current?.focus()
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (dropdownOpen && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
      e.preventDefault()
      setActiveIdx((i) => {
        const delta = e.key === 'ArrowDown' ? 1 : -1
        return Math.min(Math.max(i + delta, 0), suggestions.length - 1)
      })
      return
    }
    if (e.key === 'Enter') {
      if (dropdownOpen) {
        e.preventDefault()
        const hit = suggestions[activeIdx]
        if (hit) pick(hit)
      } else if (text.trim()) {
        e.preventDefault()
        commitTyped()
      }
      return
    }
    if (e.key === ',') {
      e.preventDefault()
      commitTyped()
      return
    }
    if (e.key === 'Tab') {
      // Nur abfangen, wenn es etwas zu übernehmen gibt — sonst normal weitertabben.
      if (text.trim()) {
        e.preventDefault()
        commitTyped()
      }
      return
    }
    if (e.key === 'Backspace' && text === '' && value.length > 0) {
      onChange(value.slice(0, -1))
      return
    }
    if (e.key === 'Escape' && dropdownOpen) {
      // Esc schließt nur das Dropdown, nicht den Composer.
      e.stopPropagation()
      setOpen(false)
    }
  }

  const onPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pasted = e.clipboardData.getData('text')
    if (/[,;]/.test(pasted)) {
      e.preventDefault()
      addAddrs(splitAddrs(text ? `${text},${pasted}` : pasted))
      setText('')
      setOpen(false)
    }
  }

  return (
    <div className="relative">
      <div
        className="mt-1 flex w-full flex-wrap items-center gap-1 rounded border border-hairline bg-paper px-2 py-1 focus-within:border-tinte"
        onClick={() => inputRef.current?.focus()}
      >
        {value.map((addr) => (
          <span
            key={addr}
            className="flex max-w-full items-center gap-1 rounded bg-[#EBEEF9] px-1.5 py-0.5 font-mono text-[11px] text-tinte"
          >
            <span className="min-w-0 truncate">{addr}</span>
            <button
              type="button"
              aria-label={`${addr} entfernen`}
              onClick={(e) => {
                e.stopPropagation()
                onChange(value.filter((a) => a !== addr))
              }}
              className="shrink-0 rounded text-tinte/60 transition hover:text-tinte"
            >
              <XIcon size={10} />
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          autoFocus={autoFocus}
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            setOpen(true)
          }}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
          onBlur={() => {
            if (text.trim()) commitTyped()
            setOpen(false)
          }}
          placeholder={value.length === 0 ? placeholder : undefined}
          aria-label={ariaLabel}
          className="min-w-[120px] flex-1 bg-transparent py-0.5 text-[13px] placeholder:text-muted focus:outline-none"
        />
      </div>

      {dropdownOpen ? (
        <ul
          // preventDefault auch hier: ein Griff zur Dropdown-Scrollbar darf den
          // Input nicht blurren (Blur committet den Tipptext).
          onMouseDown={(e) => e.preventDefault()}
          className="absolute inset-x-0 top-full z-20 mt-1 max-h-[200px] overflow-y-auto rounded border border-hairline bg-surface py-1 shadow-lg"
        >
          {suggestions.map((c, i) => (
            <li key={c.addr}>
              <button
                type="button"
                // preventDefault: Fokus (und damit onBlur des Inputs) nicht stehlen
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(c)}
                onMouseEnter={() => setActiveIdx(i)}
                className={`flex w-full items-baseline gap-1.5 px-2.5 py-1.5 text-left text-[12.5px] ${
                  i === activeIdx ? 'bg-[#EFF2FB] text-tinte' : 'text-ink'
                }`}
              >
                {c.name ? (
                  <>
                    <span className="min-w-0 truncate">{c.name}</span>
                    <span className="min-w-0 truncate font-mono text-[10.5px] text-muted">&lt;{c.addr}&gt;</span>
                  </>
                ) : (
                  <span className="min-w-0 truncate font-mono text-[11px]">{c.addr}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
