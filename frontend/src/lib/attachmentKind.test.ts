import { describe, expect, it } from 'vitest'
import { attachmentKind, canPreview } from './attachmentKind'

describe('attachmentKind', () => {
  it('maps pdf, images and text to previewable kinds', () => {
    expect(attachmentKind('application/pdf')).toBe('pdf')
    expect(attachmentKind('image/png')).toBe('image')
    expect(attachmentKind('image/jpeg')).toBe('image')
    expect(attachmentKind('text/plain')).toBe('text')
    expect(attachmentKind('text/csv')).toBe('text')
  })

  it('never previews script-capable types (matches backend whitelist)', () => {
    for (const ct of ['image/svg+xml', 'text/html', 'application/xhtml+xml', 'text/xml', 'application/xml']) {
      expect(attachmentKind(ct)).toBe('none')
      expect(canPreview(ct)).toBe(false)
    }
  })

  it('treats unknown/binary and empty as not previewable', () => {
    for (const ct of ['application/zip', 'application/octet-stream', '', null, undefined]) {
      expect(attachmentKind(ct)).toBe('none')
    }
  })

  it('ignores content-type parameters and case', () => {
    expect(attachmentKind('TEXT/PLAIN; charset=utf-8')).toBe('text')
    expect(attachmentKind('Application/PDF')).toBe('pdf')
  })
})
