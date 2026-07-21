import { useEffect } from 'react'

/** Lauscht auf Server-Sent Events (/api/events): der IMAP-IDLE-Watcher im
    Backend meldet neue Mails und Verbindungswechsel praktisch sofort.
    EventSource reconnectet von selbst; als Sicherheitsnetz pollen die
    Queries zusätzlich langsam. */
export function useLiveEvents(onNewMail: (account: string) => void, onStatus?: (account: string, connected: boolean) => void) {
  useEffect(() => {
    const source = new EventSource('/api/events')
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'new_mail' && typeof data.account === 'string') {
          onNewMail(data.account)
        } else if (data.type === 'status' && typeof data.account === 'string') {
          onStatus?.(data.account, Boolean(data.connected))
        }
      } catch {
        // Keepalive/unbekannte Events ignorieren
      }
    }
    return () => source.close()
  }, [onNewMail, onStatus])
}
