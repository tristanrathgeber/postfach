import { useCallback, useMemo, useRef, useState } from 'react'

// Minimales Basis-CSS, das in das (serverseitig sanitisierte) Mail-HTML injiziert wird:
// lesbare Schrift, max-width 720px, Bilder nie breiter als der Frame.
const FRAME_CSS = `
  html, body { margin: 0; padding: 0; }
  /* Mail-Inhalt bleibt IMMER auf hellem Papier — E-Mails sind für Weiß
     gestaltet; Invertieren zerstört Layout und Bilder. */
  body {
    padding: 4px 1px 16px;
    font-family: -apple-system, 'Segoe UI', system-ui, sans-serif;
    font-size: 15px;
    line-height: 1.55;
    color: #1a1917;
    background: #ffffff;
    max-width: 720px;
    word-break: break-word;
  }
  img { max-width: 100% !important; height: auto; }
  table { max-width: 100%; }
  pre { white-space: pre-wrap; }
  a { color: #2440b3; }
  blockquote { margin: 0 0 0 4px; padding-left: 12px; border-left: 2px solid #e8e5df; color: #6f6a61; }
`

function wrapHtml(html: string): string {
  return `<!doctype html><html><head><meta charset="utf-8"><style>${FRAME_CSS}</style></head><body>${html}</body></html>`
}

/**
 * Rendert Mail-HTML isoliert in einem sandboxed <iframe srcDoc>.
 *
 * SICHERHEIT / WARUM sandbox="allow-same-origin":
 * Mit sandbox="" bekommt der Frame eine opaque origin — `contentDocument` ist dann
 * für den Parent unzugänglich, und die Höhe ließe sich ohne allow-scripts nicht
 * messen (kein postMessage möglich, weil keine Skripte laufen dürfen).
 * Deshalb sandbox="allow-same-origin" OHNE allow-scripts: Skripte im Mail-HTML
 * bleiben vollständig blockiert (Ausführung bräuchte allow-scripts), ebenso
 * Formulare, Popups und Top-Navigation. allow-same-origin erlaubt hier nur dem
 * Parent, das eingebettete Dokument zu vermessen (scrollHeight) — das HTML selbst
 * ist zusätzlich bereits serverseitig sanitisiert (siehe API-Vertrag).
 */
export function HtmlMailFrame({ html }: { html: string }) {
  const frameRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(240)
  const srcDoc = useMemo(() => wrapHtml(html), [html])

  const measure = useCallback(() => {
    const doc = frameRef.current?.contentDocument
    if (!doc) return
    const h = Math.max(doc.documentElement?.scrollHeight ?? 0, doc.body?.scrollHeight ?? 0)
    if (h > 0) setHeight((prev) => (prev === h ? prev : h))
  }, [])

  const handleLoad = useCallback(() => {
    measure()
    // Bilder laden asynchron nach — nach jedem geladenen Bild neu messen.
    const doc = frameRef.current?.contentDocument
    if (!doc) return
    for (const img of Array.from(doc.images)) {
      if (!img.complete) img.addEventListener('load', measure, { once: true })
    }
  }, [measure])

  return (
    <iframe
      ref={frameRef}
      title="Nachrichteninhalt"
      sandbox="allow-same-origin"
      srcDoc={srcDoc}
      onLoad={handleLoad}
      className="block w-full border-0"
      style={{ height }}
    />
  )
}
