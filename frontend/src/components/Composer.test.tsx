import { describe, expect, it, vi, afterEach } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Composer, type ComposerState } from './Composer'
import { ToastProvider } from './Toast'
import type { Account } from '../lib/types'

vi.mock('../lib/api', () => ({
  api: {
    contacts: vi.fn().mockResolvedValue([]),
    snippets: vi.fn().mockResolvedValue([]),
    send: vi.fn().mockResolvedValue({ ok: true }),
    sendWithAttachments: vi.fn().mockResolvedValue({ ok: true }),
    saveDraft: vi.fn().mockResolvedValue({ id: 'entwurf-1' }),
    deleteDraft: vi.fn().mockResolvedValue({ ok: true }),
  },
  errText: (e: unknown) => String(e),
}))

const { api } = await import('../lib/api')

const accounts: Account[] = [{ name: 'privat', address: 'privat@example.org', provider: 'imap' }]

function renderComposer(state: ComposerState = { mode: 'new', account: 'privat' }) {
  const queryClient = new QueryClient()
  const onClose = vi.fn()
  render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <Composer state={state} accounts={accounts} signatures={{}} onClose={onClose} />
      </ToastProvider>
    </QueryClientProvider>,
  )
  return { onClose }
}

function addRecipient(addr: string) {
  const input = screen.getByLabelText('An')
  fireEvent.change(input, { target: { value: addr } })
  fireEvent.keyDown(input, { key: 'Enter' })
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('Composer — Senden', () => {
  it('verweigert das Senden ohne Empfänger, ohne den Bestätigungs-Button zu bewaffnen', () => {
    renderComposer()
    fireEvent.click(screen.getByRole('button', { name: 'Senden' }))

    expect(screen.getByText(/Mindestens ein Empfänger nötig/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Senden' })).toBeTruthy() // nicht "Wirklich senden?"
    expect(api.send).not.toHaveBeenCalled()
  })

  it('sendet erst nach dem zweiten Klick (Doppel-Klick-Bestätigung statt confirm())', async () => {
    const { onClose } = renderComposer()
    addRecipient('empfang@example.org')

    fireEvent.click(screen.getByRole('button', { name: 'Senden' }))
    expect(api.send).not.toHaveBeenCalled()
    const armedButton = screen.getByRole('button', { name: 'Wirklich senden?' })

    fireEvent.click(armedButton)
    await waitFor(() => expect(api.send).toHaveBeenCalledTimes(1))
    expect(api.send).toHaveBeenCalledWith(expect.objectContaining({ to: ['empfang@example.org'] }))
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })
})

describe('Composer — Anhänge', () => {
  it('zeigt hinzugefügte Anhänge an und entfernt sie wieder über den X-Knopf', () => {
    renderComposer()
    const file = new File(['Inhalt'], 'anhang.txt', { type: 'text/plain' })
    fireEvent.change(screen.getByLabelText('Dateien anhängen'), { target: { files: [file] } })

    expect(screen.getByText('anhang.txt')).toBeTruthy()

    fireEvent.click(screen.getByLabelText('anhang.txt entfernen'))
    expect(screen.queryByText('anhang.txt')).toBeNull()
  })

  it('deaktiviert Senden, sobald die Anhänge das 25-MB-Limit überschreiten', () => {
    renderComposer()
    const big = new File(['x'], 'riesig.bin', { type: 'application/octet-stream' })
    Object.defineProperty(big, 'size', { value: 26 * 1024 * 1024 })
    fireEvent.change(screen.getByLabelText('Dateien anhängen'), { target: { files: [big] } })

    expect(screen.getByText(/Limit 25 MB/)).toBeTruthy()
    const sendButton = screen.getByRole('button', { name: 'Senden' }) as HTMLButtonElement
    expect(sendButton.disabled).toBe(true)
  })
})

describe('Composer — Schließen', () => {
  it('braucht bei ungespeicherten Änderungen ein zweites Esc, bevor der Entwurf verlassen wird', async () => {
    const { onClose } = renderComposer()
    fireEvent.change(screen.getByLabelText('Betreff'), { target: { value: 'Wichtiger Betreff' } })

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
    expect(screen.getByText(/Nochmal Esc: Schließen/)).toBeTruthy()

    fireEvent.keyDown(window, { key: 'Escape' })
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })
})
