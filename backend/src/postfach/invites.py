"""ICS-Einladungen: parsen (Anzeige) und RFC-5546-REPLY bauen (RSVP).

ICS-Inhalte sind UNTRUSTED Mail-Daten — `parse_invite` fängt jeden Parser-
Fehler ab und liefert None statt eine Route zu Fall zu bringen. Der REPLY wird
konservativ aus den Original-Eckdaten (UID/SEQUENCE/DTSTART/ORGANIZER) gebaut;
gesendet wird ausschließlich über den normalen, nutzergeklickten Versandpfad.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from icalendar import Calendar, Event, vCalAddress, vText

_PARTSTAT = {"accepted": "ACCEPTED", "tentative": "TENTATIVE", "declined": "DECLINED"}


@dataclass(frozen=True)
class Invite:
    summary: str
    start: str  # ISO-8601 (DATE-TIME) oder JJJJ-MM-TT (all_day)
    end: str
    all_day: bool
    location: str
    organizer_name: str
    organizer_email: str
    method: str
    uid: str


def _addr(value) -> tuple[str, str]:
    """(name, email) aus einem ORGANIZER/ATTENDEE-Wert (`mailto:…`, CN-Param)."""
    if value is None:
        return "", ""
    email = str(value).strip()
    if email.lower().startswith("mailto:"):
        email = email[7:]
    name = ""
    params = getattr(value, "params", None)
    if params:
        name = str(params.get("CN", "")).strip()
    return name, email


def _iso(value, *, all_day: bool) -> str:
    if value is None:
        return ""
    dt = getattr(value, "dt", value)
    if all_day and isinstance(dt, _dt.date) and not isinstance(dt, _dt.datetime):
        return dt.isoformat()
    if isinstance(dt, _dt.datetime):
        return dt.isoformat()
    return str(dt)


def _first_event(calendar_raw: str) -> tuple[Calendar, Event] | None:
    cal = Calendar.from_ical(calendar_raw)
    for component in cal.walk("VEVENT"):
        return cal, component
    return None


def parse_invite(calendar_raw: str | None) -> Invite | None:
    if not calendar_raw or "VEVENT" not in calendar_raw:
        return None
    try:
        found = _first_event(calendar_raw)
        if found is None:
            return None
        cal, event = found
        dtstart = event.get("dtstart")
        all_day = bool(
            dtstart is not None
            and isinstance(dtstart.dt, _dt.date)
            and not isinstance(dtstart.dt, _dt.datetime)
        )
        org_name, org_email = _addr(event.get("organizer"))
        method = str(cal.get("method") or event.get("method") or "").upper()
        return Invite(
            summary=str(event.get("summary") or "").strip(),
            start=_iso(dtstart, all_day=all_day),
            end=_iso(event.get("dtend"), all_day=all_day),
            all_day=all_day,
            location=str(event.get("location") or "").strip(),
            organizer_name=org_name,
            organizer_email=org_email,
            method=method,
            uid=str(event.get("uid") or "").strip(),
        )
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def build_invite_reply_ics(calendar_raw: str, attendee_email: str, response: str) -> bytes:
    """RFC-5546-REPLY: Original-Eckdaten echoen, EIGENEN ATTENDEE mit PARTSTAT.
    `response` ∈ accepted|tentative|declined."""
    partstat = _PARTSTAT.get(response)
    if partstat is None:
        raise ValueError(f"Unbekannte Antwort: {response!r}")
    found = _first_event(calendar_raw)
    if found is None:
        raise ValueError("Keine VEVENT in der Einladung")
    _cal, src = found

    reply = Calendar()
    reply.add("prodid", "-//Postfach//RSVP//DE")
    reply.add("version", "2.0")
    reply.add("method", "REPLY")

    event = Event()
    for prop in ("uid", "summary", "dtstart", "dtend", "sequence", "organizer"):
        if prop in src:
            event.add(prop, src[prop])
    if "sequence" not in src:
        event.add("sequence", 0)

    attendee = vCalAddress(f"mailto:{attendee_email}")
    attendee.params["PARTSTAT"] = vText(partstat)
    event.add("attendee", attendee, encode=0)
    event.add("dtstamp", _dt.datetime.now(_dt.timezone.utc))
    reply.add_component(event)
    return reply.to_ical()
