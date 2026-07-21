// Ansichten der Nachrichtenliste. Alle außer "folder" und "search" arbeiten auf INBOX.

export type View =
  | { kind: 'inbox' }
  | { kind: 'unread' }
  | { kind: 'drafts' }
  | { kind: 'outbox' }
  | { kind: 'reminders' }
  | { kind: 'subscriptions' }
  | { kind: 'screener' }
  | { kind: 'category'; category: string }
  | { kind: 'folder'; folder: string }
  | { kind: 'search'; query: string; folder: string }

export function viewTitle(view: View): string {
  switch (view.kind) {
    case 'inbox':
      return 'Inbox'
    case 'unread':
      return 'Ungelesen'
    case 'drafts':
      return 'Entwürfe'
    case 'outbox':
      return 'Ausgang'
    case 'reminders':
      return 'Wiedervorlage'
    case 'subscriptions':
      return 'Abos'
    case 'screener':
      return 'Screener'
    case 'category':
      return view.category
    case 'folder':
      return view.folder
    case 'search':
      return 'Suche'
  }
}

/** Ordner, aus dem die Ansicht ihre Daten bezieht. Die Suche behält den Ordner, aus dem sie gestartet wurde. */
export function viewFolder(view: View): string {
  switch (view.kind) {
    case 'folder':
    case 'search':
      return view.folder
    default:
      return 'INBOX'
  }
}

/** Stabiler Schlüssel einer Ansicht (Identität + Listen-Reset in der UI). */
export function viewKey(view: View): string {
  switch (view.kind) {
    case 'category':
      return `category:${view.category}`
    case 'folder':
      return `folder:${view.folder}`
    case 'search':
      return `search:${view.folder}:${view.query}`
    default:
      return view.kind
  }
}

export function sameView(a: View, b: View): boolean {
  return viewKey(a) === viewKey(b)
}
