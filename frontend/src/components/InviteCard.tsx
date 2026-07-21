import type { Invite, InviteResponse } from '../lib/types'
import { formatInviteWhen } from '../lib/invite'
import { CheckIcon, ClockIcon, SpinnerIcon, XIcon } from './Icons'

// Statische Klassen (Tailwind kann keine dynamisch zusammengesetzten scannen).
const RESPONSE_HOVER: Record<InviteResponse, string> = {
  accepted: 'hover:border-success hover:text-success',
  tentative: 'hover:border-tinte hover:text-tinte',
  declined: 'hover:border-danger hover:text-danger',
}
const RESPONSE_LABEL: Record<InviteResponse, string> = {
  accepted: 'Zugesagt',
  tentative: 'Mit Vorbehalt',
  declined: 'Abgesagt',
}

/** Einladungskarte im Reader: Termin + Zusagen/Vielleicht/Absagen. */
export function InviteCard({
  invite,
  answered,
  pending,
  onRespond,
}: {
  invite: Invite
  /** Bereits gewählte Antwort (nach dem Senden) — sonst null. */
  answered: InviteResponse | null
  pending: boolean
  onRespond: (response: InviteResponse) => void
}) {
  return (
    <section className="mt-4 rounded-lg border border-tinte/40 bg-tint px-4 py-3" aria-label="Einladung">
      <div className="flex items-center gap-2">
        <ClockIcon size={13} className="text-tinte" />
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-tinte">Einladung</span>
      </div>
      <h3 className="mt-1.5 font-serif text-[18px] italic leading-tight">{invite.summary || '(Ohne Titel)'}</h3>
      <p className="mt-1 text-[13px] text-ink">{formatInviteWhen(invite)}</p>
      {invite.location ? <p className="text-[12.5px] text-muted">{invite.location}</p> : null}
      {invite.organizer_name || invite.organizer_email ? (
        <p className="mt-0.5 font-mono text-[10.5px] text-muted">
          Von {invite.organizer_name || invite.organizer_email}
        </p>
      ) : null}

      {answered ? (
        <p className="mt-2.5 inline-flex items-center gap-1 rounded border border-hairline bg-surface px-2 py-1 text-[12px] text-ink">
          <CheckIcon size={12} className="text-success" />
          {RESPONSE_LABEL[answered]} — Antwort gesendet
        </p>
      ) : (
        <div className="mt-2.5 flex items-center gap-2">
          {(['accepted', 'tentative', 'declined'] as const).map((r) => (
            <button
              key={r}
              type="button"
              disabled={pending}
              onClick={() => {
                if (pending) return // Doppelklick-Schutz VOR dem Re-Render
                onRespond(r)
              }}
              className={`flex items-center gap-1 rounded border border-hairline px-2.5 py-1 text-[12.5px] font-medium transition disabled:opacity-50 ${
                pending ? 'text-muted' : `text-ink ${RESPONSE_HOVER[r]}`
              }`}
            >
              {pending ? <SpinnerIcon size={11} /> : r === 'accepted' ? <CheckIcon size={12} /> : r === 'declined' ? <XIcon size={12} /> : <ClockIcon size={12} />}
              {r === 'accepted' ? 'Zusagen' : r === 'tentative' ? 'Vielleicht' : 'Absagen'}
            </button>
          ))}
        </div>
      )}
    </section>
  )
}
