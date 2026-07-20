import { useEffect } from 'react'

/** Lauscht auf Server-Sent Events (/api/events): der IMAP-IDLE-Watcher im
    Backend meldet neue Mails praktisch sofort. EventSource reconnectet
    von selbst; als Sicherheitsnetz pollen die Queries zusätzlich langsam. */
export function useLiveEvents(onNewMail: (account: string) => void) {
  useEffect(() => {
    const source = new EventSource('/api/events')
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'new_mail' && typeof data.account === 'string') {
          onNewMail(data.account)
        }
      } catch {
        // Keepalive/unbekannte Events ignorieren
      }
    }
    return () => source.close()
  }, [onNewMail])
}
