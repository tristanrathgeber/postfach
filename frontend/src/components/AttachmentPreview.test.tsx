import { describe, expect, it, vi, afterEach } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AttachmentPreview } from './AttachmentPreview'
import { ToastProvider } from './Toast'
import { resetOverlays } from '../lib/overlay'
import type { Attachment } from '../lib/types'

vi.mock('../lib/api', () => ({
  api: {
    attachmentUrl: (_account: string, _uid: number, index: number) => `blob://anhang-${index}`,
    saveAttachment: vi.fn().mockResolvedValue({ path: '/tmp/x', filename: 'a.png' }),
  },
  errText: (e: unknown) => String(e),
}))

const attachments: Attachment[] = [
  { index: 0, filename: 'erste.png', content_type: 'image/png', size: 1024 },
  { index: 1, filename: 'zweite.png', content_type: 'image/png', size: 2048 },
]

function renderPreview(overrides: Partial<Parameters<typeof AttachmentPreview>[0]> = {}) {
  const queryClient = new QueryClient()
  const onClose = vi.fn()
  render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AttachmentPreview
          account="a@example.com"
          uid={1}
          folder="INBOX"
          attachments={attachments}
          startIndex={0}
          onClose={onClose}
          {...overrides}
        />
      </ToastProvider>
    </QueryClientProvider>,
  )
  return { onClose }
}

afterEach(() => {
  cleanup()
  resetOverlays()
})

describe('AttachmentPreview — Blättern', () => {
  it('zeigt die Position im Kopf und blättert mit den Pfeiltasten', () => {
    renderPreview()
    expect(screen.getByText('1 von 2', { exact: false })).toBeTruthy()

    fireEvent.keyDown(document.body, { key: 'ArrowRight', bubbles: true })
    expect(screen.getByText('2 von 2', { exact: false })).toBeTruthy()
    expect(screen.getByRole('dialog').getAttribute('aria-label')).toContain('zweite.png')

    fireEvent.keyDown(document.body, { key: 'ArrowLeft', bubbles: true })
    expect(screen.getByText('1 von 2', { exact: false })).toBeTruthy()
  })

  it('blättert am Rand herum (letzter -> erster und umgekehrt)', () => {
    renderPreview()
    fireEvent.keyDown(document.body, { key: 'ArrowLeft', bubbles: true }) // vor dem ersten -> letzter
    expect(screen.getByText('2 von 2', { exact: false })).toBeTruthy()

    fireEvent.keyDown(document.body, { key: 'ArrowRight', bubbles: true }) // vor dem letzten -> erster
    expect(screen.getByText('1 von 2', { exact: false })).toBeTruthy()
  })

  it('zeigt bei nur einem Anhang keine Blätter-Knöpfe und ignoriert Pfeiltasten', () => {
    renderPreview({ attachments: [attachments[0]] })
    expect(screen.queryByLabelText('Vorheriger Anhang')).toBeNull()
    expect(screen.queryByLabelText('Nächster Anhang')).toBeNull()

    fireEvent.keyDown(document.body, { key: 'ArrowRight', bubbles: true })
    expect(screen.getByRole('dialog').getAttribute('aria-label')).toContain('erste.png')
  })
})

describe('AttachmentPreview — Schließen', () => {
  it('schließt per Esc-Taste', () => {
    const { onClose } = renderPreview()
    fireEvent.keyDown(document.body, { key: 'Escape', bubbles: true })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('schließt per Klick auf den Rand, nicht per Klick auf den Inhalt', () => {
    const { onClose } = renderPreview()
    fireEvent.mouseDown(screen.getByRole('dialog'))
    expect(onClose).not.toHaveBeenCalled()

    const backdrop = document.querySelector('.fixed.inset-0') as HTMLElement
    fireEvent.mouseDown(backdrop, { target: backdrop })
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})

describe('AttachmentPreview — Tastenabschirmung', () => {
  it('lässt keine Taste zu einem älteren globalen Fenster-Listener durch (Vorschau schluckt sie zuerst)', () => {
    // Nachbildung des globalen App-Kürzels (window.addEventListener, Bubble-Phase,
    // wie in App.tsx/Reader.tsx) — muss VOR dem Rendern registriert sein, damit die
    // Registrierungsreihenfolge der echten App entspricht.
    const globalShortcut = vi.fn()
    window.addEventListener('keydown', globalShortcut)
    try {
      renderPreview()
      fireEvent.keyDown(document.body, { key: 'v', bubbles: true })
      expect(globalShortcut).not.toHaveBeenCalled()
    } finally {
      window.removeEventListener('keydown', globalShortcut)
    }
  })

  it('meldet den Dialog beim Overlay-Zähler an und wieder ab', async () => {
    const { overlayOpen } = await import('../lib/overlay')
    expect(overlayOpen()).toBe(false)
    const { unmount } = render(
      <QueryClientProvider client={new QueryClient()}>
        <ToastProvider>
          <AttachmentPreview account="a" uid={1} folder="INBOX" attachments={attachments} startIndex={0} onClose={vi.fn()} />
        </ToastProvider>
      </QueryClientProvider>,
    )
    expect(overlayOpen()).toBe(true)
    unmount()
    expect(overlayOpen()).toBe(false)
  })
})
