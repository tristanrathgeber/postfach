import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react'

type ToastKind = 'info' | 'error'
/** Optionale Inline-Aktion im Toast (z. B. "Rückgängig"). */
type ToastAction = { label: string; run: () => void }
type ToastItem = { id: number; message: string; kind: ToastKind; action?: ToastAction }

type ToastContextValue = { showToast: (message: string, kind?: ToastKind, action?: ToastAction) => void }

const ToastContext = createContext<ToastContextValue | null>(null)

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast muss innerhalb des ToastProviders verwendet werden')
  return ctx
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const nextId = useRef(1)

  const showToast = useCallback((message: string, kind: ToastKind = 'info', action?: ToastAction) => {
    const id = nextId.current++
    setToasts((prev) => [...prev, { id, message, kind, action }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, action ? 6000 : 3500) // Mit Aktion (z. B. Rückgängig) etwas länger sichtbar
  }, [])

  const value = useMemo(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex flex-col items-end gap-2">
        {toasts.map((t) => {
          const action = t.action
          return (
            <div
              key={t.id}
              className={`fade-in pointer-events-auto rounded border bg-surface px-3 py-2 text-[13px] shadow-sm ${
                t.kind === 'error' ? 'border-danger/50 text-danger' : 'border-hairline text-ink'
              }`}
            >
              {t.message}
              {action ? (
                <button
                  type="button"
                  onClick={() => {
                    action.run()
                    setToasts((prev) => prev.filter((x) => x.id !== t.id))
                  }}
                  className="ml-1.5 font-medium text-tinte transition hover:underline"
                >
                  {action.label}
                </button>
              ) : null}
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}
