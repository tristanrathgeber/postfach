/** Wie ein Anhang in der Vorschau dargestellt wird. Muss zur Server-Leitplanke
 * `attach.inline_safe` passen: HTML/SVG/XML sind bewusst NICHT vorschaubar
 * (würden sonst als Dokument auf dem App-Origin Skripte ausführen). */
export type AttachmentKind = 'image' | 'pdf' | 'text' | 'none'

export function attachmentKind(contentType: string | null | undefined): AttachmentKind {
  const ct = (contentType || '').split(';', 1)[0].trim().toLowerCase()
  if (ct === 'application/pdf') return 'pdf'
  if (ct === 'text/plain' || ct === 'text/csv') return 'text'
  if (ct === 'image/svg+xml') return 'none' // SVG kann Skripte enthalten
  if (ct.startsWith('image/')) return 'image'
  return 'none'
}

/** Vorschaubar = alles außer 'none'. */
export function canPreview(contentType: string | null | undefined): boolean {
  return attachmentKind(contentType) !== 'none'
}
