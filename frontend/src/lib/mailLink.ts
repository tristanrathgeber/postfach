/** Welche Links aus einer HTML-Mail darf die App öffnen?
 *
 * Mail-HTML läuft in einer Sandbox ohne `allow-popups`/`allow-top-navigation` —
 * ein `target="_blank"` kann dort gar nichts öffnen, weshalb die App den Klick
 * selbst ausführt. Damit dabei nichts Ungutes durchrutscht (javascript:,
 * data:, file: …), kommen nur diese Schemata durch.
 */
const SAFE_SCHEMES = new Set(['http:', 'https:', 'mailto:'])

/**
 * Gibt die zu öffnende URL zurück — oder null, wenn der Link nicht sicher
 * (oder gar keine absolute URL) ist. Relative Links haben in einer Mail keinen
 * sinnvollen Bezugspunkt und werden bewusst verworfen.
 */
export function openableHref(href: string | null | undefined): string | null {
  const raw = (href || '').trim()
  if (!raw) return null
  let url: URL
  try {
    url = new URL(raw) // ohne Basis: relative Links werfen und fallen raus
  } catch {
    return null
  }
  return SAFE_SCHEMES.has(url.protocol) ? url.href : null
}
