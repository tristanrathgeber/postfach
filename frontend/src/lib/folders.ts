// Ordner-Rollen-Heuristik — Leaf-Exakt-Match, deckungsgleich mit
// backend/src/postfach/mail_imap.py (_JUNK_NAMES). Substring-Matching wäre
// eine Falle („Junkfood-Rezepte"). Echte Server-Rollen (\Junk) kommen mit v0.5.
const JUNK_NAMES = new Set(['spam', 'junk', 'junk-e-mail', 'spamverdacht', 'werbung', 'bulk mail'])

export function isSpamFolder(folder: string): boolean {
  const leaf = folder.split('/').at(-1)?.split('.').at(-1)?.toLowerCase() ?? ''
  return JUNK_NAMES.has(folder.toLowerCase()) || JUNK_NAMES.has(leaf)
}
