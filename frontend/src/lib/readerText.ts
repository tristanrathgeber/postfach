// Reader-View: den neuen Mail-Text herausschälen — zitierten Verlauf abschneiden.
// Konservativ: nur an klaren Zitat-Markern kappen, und nie so viel wegwerfen,
// dass fast nichts übrig bleibt (dann lieber den ganzen Text zeigen).

// „Am 01.01. um 12:00 schrieb Max Mustermann:" endet mit dem Namen, nicht mit
// „schrieb" — daher nach schrieb/wrote bis zum Doppelpunkt am Zeilenende laufen.
const ATTRIBUTION = /^\s*(Am|On)\s.+\b(schrieb|wrote|geschrieben)\b.*:\s*$/i
const QUOTE_LINE = /^>/
const ORIGINAL_MSG = /^-{3,}\s*(Ursprüngliche Nachricht|Original Message)/i
const OUTLOOK_RULE = /^_{5,}\s*$/
const HEADER_FROM = /^(Von|From):\s.+/
// Companion-Header, die einen ECHTEN weitergeleiteten/zitierten Kopf ausweisen.
const HEADER_COMPANION = /^(An|To|Gesendet|Sent|Betreff|Subject|Cc|Datum|Date):\s/

function isSimpleQuoteStart(line: string): boolean {
  return QUOTE_LINE.test(line) || ATTRIBUTION.test(line) || ORIGINAL_MSG.test(line) || OUTLOOK_RULE.test(line)
}

/** Index der ersten Zeile, die einen zitierten Verlauf beginnt, oder -1.
 * „Von:" gilt nur mit Companion-Header in den Folgezeilen als Kopf — sonst wäre
 * „Von: unserem Lieferanten …" im Fließtext ein Falsch-Positiv. */
function findCutIndex(lines: string[]): number {
  for (let i = 0; i < lines.length; i++) {
    if (isSimpleQuoteStart(lines[i])) return i
    if (HEADER_FROM.test(lines[i])) {
      const companion = lines.slice(i + 1, i + 4).some((l) => HEADER_COMPANION.test(l))
      if (companion) return i
    }
  }
  return -1
}

/** Gibt den führenden (neuen) Teil des Texts zurück; der zitierte Verlauf wird
 * abgeschnitten. Fällt auf den Volltext zurück, wenn zu wenig übrig bliebe. */
export function simplifyBody(text: string): string {
  const full = text.trim()
  const lines = text.split('\n')
  const cut = findCutIndex(lines)
  if (cut < 0) return full
  const head = lines.slice(0, cut).join('\n').trim()
  // Nur wenn NICHTS Neues davor steht (Marker ganz oben) → Volltext; eine kurze
  // echte Antwort wie „Kurze Antwort." bleibt erhalten.
  return head ? head : full
}

/** True nur, wenn simplifyBody wirklich etwas gekürzt hat — EINZIGE Quelle für
 * den „ausgeblendet"-Hinweis, damit er nie lügt. */
export function wasTruncated(text: string): boolean {
  return simplifyBody(text) !== text.trim()
}
