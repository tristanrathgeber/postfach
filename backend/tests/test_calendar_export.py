"""Batch 8: ICS-Einladungen (RSVP), Markdown-Export, Struktur-Extraktion."""

import pytest

from postfach.extract import extract_entities
from postfach.invites import build_invite_reply_ics, parse_invite


_INVITE_ICS = """BEGIN:VCALENDAR
PRODID:-//Test//EN
VERSION:2.0
METHOD:REQUEST
BEGIN:VEVENT
UID:evt-4711@example.org
SEQUENCE:0
SUMMARY:Projektbesprechung Q3
DTSTART:20260724T130000Z
DTEND:20260724T140000Z
LOCATION:Konferenzraum 2\\, Hauptgebäude
ORGANIZER;CN=Petra Meyer:mailto:petra@example.org
ATTENDEE;CN=Alex;PARTSTAT=NEEDS-ACTION:mailto:alex@demo.example
END:VEVENT
END:VCALENDAR
"""

_ALLDAY_ICS = """BEGIN:VCALENDAR
METHOD:REQUEST
VERSION:2.0
BEGIN:VEVENT
UID:allday-1@example.org
SUMMARY:Betriebsausflug
DTSTART;VALUE=DATE:20260801
DTEND;VALUE=DATE:20260802
ORGANIZER:mailto:chef@example.org
END:VEVENT
END:VCALENDAR
"""


# --- ICS-Parsing ---


def test_parse_invite_extracts_fields():
    inv = parse_invite(_INVITE_ICS)
    assert inv.summary == "Projektbesprechung Q3"
    assert inv.method == "REQUEST"
    assert inv.uid == "evt-4711@example.org"
    assert inv.organizer_email == "petra@example.org"
    assert inv.organizer_name == "Petra Meyer"
    assert inv.location == "Konferenzraum 2, Hauptgebäude"
    assert inv.all_day is False
    assert inv.start.startswith("2026-07-24T13:00")


def test_parse_invite_all_day():
    inv = parse_invite(_ALLDAY_ICS)
    assert inv.all_day is True
    assert inv.start == "2026-08-01"
    assert inv.summary == "Betriebsausflug"


def test_parse_invite_garbage_is_none():
    assert parse_invite("nicht mal ICS") is None
    assert parse_invite("") is None


def test_build_reply_echoes_uid_and_sets_partstat():
    reply = build_invite_reply_ics(_INVITE_ICS, "alex@demo.example", "accepted")
    text = reply.decode("utf-8")
    assert "METHOD:REPLY" in text
    assert "UID:evt-4711@example.org" in text
    assert "PARTSTAT=ACCEPTED" in text
    assert "mailto:alex@demo.example" in text.lower() or "alex@demo.example" in text
    # Deklination genauso
    declined = build_invite_reply_ics(_INVITE_ICS, "alex@demo.example", "declined").decode()
    assert "PARTSTAT=DECLINED" in declined


def test_build_reply_rejects_unknown_response():
    with pytest.raises(ValueError):
        build_invite_reply_ics(_INVITE_ICS, "alex@demo.example", "maybe-not")


# --- Struktur-Extraktion ---


def test_extract_amount_and_date():
    ents = extract_entities("Ihre Rechnung über 39,95 € ist fällig am 24.07.2026 um 14:30 Uhr.")
    kinds = {e["kind"] for e in ents}
    assert "amount" in kinds and "date" in kinds
    amount = next(e for e in ents if e["kind"] == "amount")
    assert "39,95" in amount["text"]


def test_extract_tracking_number_with_carrier_link():
    ents = extract_entities("Deine Sendung 1Z999AA10123456784 ist unterwegs.")
    track = next(e for e in ents if e["kind"] == "tracking")
    assert track["value"] == "1Z999AA10123456784"
    assert track["url"].startswith("https://") and "1Z999AA10123456784" in track["url"]


def test_extract_dedupes_and_caps():
    text = "Betrag 10,00 € " * 100
    ents = extract_entities(text)
    amounts = [e for e in ents if e["kind"] == "amount"]
    assert len(amounts) == 1  # dedupe identischer Werte


def test_extract_empty():
    assert extract_entities("") == []
    assert extract_entities("Nur ganz normaler Text ohne alles.") == []


# --- API (Demo) ---


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    c = TestClient(create_app(root=tmp_path, demo=True))
    c.put("/api/settings", json={"undo_seconds": 0})
    return c


def test_detail_carries_invite_and_entities(client):
    # Demo-Einladung (uid 116) + Telekom-Rechnung (uid 109, Betrag)
    detail = client.get("/api/messages/demo/116", params={"folder": "INBOX"}).json()
    assert detail["invite"] is not None
    assert detail["invite"]["summary"]
    assert detail["invite"]["organizer_email"]

    rech = client.get("/api/messages/demo/109", params={"folder": "INBOX"}).json()
    assert rech["invite"] is None
    assert any(e["kind"] == "amount" for e in rech["entities"])


def test_invite_respond_sends_reply(client):
    r = client.post("/api/invite/respond",
                    json={"account": "demo", "folder": "INBOX", "uid": 116, "response": "accepted"})
    assert r.status_code == 200 and r.json()["ok"] is True
    sent = client.get("/api/messages", params={"account": "demo", "folder": "Gesendet"}).json()
    assert any("zusage" in m["subject"].lower() or "accepted" in m["subject"].lower()
               or "projektbesprechung" in m["subject"].lower() for m in sent)


def test_invite_respond_404_without_invite(client):
    r = client.post("/api/invite/respond",
                    json={"account": "demo", "folder": "INBOX", "uid": 109, "response": "accepted"})
    assert r.status_code == 404


def test_export_returns_markdown(client):
    r = client.get("/api/messages/demo/109/export", params={"folder": "INBOX"})
    data = r.json()
    assert data["filename"].endswith(".md")
    assert data["markdown"].startswith("---")  # YAML-Frontmatter
    assert "Telekom" in data["markdown"]
    assert "title:" in data["markdown"] and "from:" in data["markdown"]


# --- Review-Härtung (Batch-8-Review) ---


def test_export_yaml_valid_with_backslash():
    """Backslash im Betreff/Absender (angreiferkontrollierter Display-Name)
    darf das YAML-Frontmatter nicht zerbrechen."""
    import yaml as _yaml
    from dataclasses import replace

    from postfach.demo import _mail
    from postfach.mdexport import to_markdown

    for subject in ("Rechnung\\Ordner", "C:\\temp\\datei", "ends-with-bs\\", "foo\\z"):
        mail = replace(_mail(1, subject, "A\\B", "a@x.de", "Body"))
        _fn, md = to_markdown(mail)
        frontmatter = md.split("---")[1]
        _yaml.safe_load(frontmatter)  # wirft bei kaputtem YAML


def test_amount_regex_no_pathological_stall():
    """Lange Tausender-Kette ohne Währung darf nicht in O(n²) laufen."""
    import time

    from postfach.extract import extract_entities

    pathological = "1" + ".234" * 5000
    start = time.perf_counter()
    extract_entities(pathological)
    # Großzügige Schranke: die lineare Variante braucht Sekundenbruchteile (auch
    # auf lahmen CI-Runnern), katastrophales Backtracking dagegen viele Sekunden.
    # Kein Mikro-Benchmark — nur der O(n²)-Blowup soll auffliegen.
    assert time.perf_counter() - start < 2.0
    # Gültige Beträge weiterhin erkannt
    ents = extract_entities("Summe 1.234,56 € und 9,99 €")
    assert len([e for e in ents if e["kind"] == "amount"]) == 2


def test_calendar_attachment_stays_downloadable():
    """Ein echter .ics-ANHANG bleibt in der Anhangsliste (nur der inline-
    Einladungsteil wird ersetzt)."""
    from postfach.mail_imap import parse_full

    raw = (
        b"From: chef@example.org\r\n"
        b"Subject: Termin\r\n"
        b'Content-Type: multipart/mixed; boundary="B"\r\n\r\n'
        b"--B\r\nContent-Type: text/plain\r\n\r\nHallo\r\n"
        b"--B\r\nContent-Type: text/calendar; method=PUBLISH\r\n"
        b'Content-Disposition: attachment; filename="termin.ics"\r\n\r\n'
        b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
        b"--B\r\nContent-Type: application/pdf\r\n"
        b'Content-Disposition: attachment; filename="rechnung.pdf"\r\n\r\n'
        b"%PDF-1.4\r\n"
        b"--B--\r\n"
    )
    mail = parse_full(1, raw, seen=True)
    names = [a.filename for a in mail.attachments]
    assert "termin.ics" in names and "rechnung.pdf" in names


def test_invite_respond_rejects_multi_organizer(client):
    """ORGANIZER mit mehreren Adressen (untrusted) darf den RSVP nicht an
    fremde Ziele auffächern."""
    from dataclasses import replace

    from postfach import demo

    bad_ics = demo._DEMO_INVITE_ICS.replace(
        "ORGANIZER;CN=Petra Meyer:mailto:petra@sfcnahetal.example",
        "ORGANIZER:mailto:petra@sfcnahetal.example, attacker@evil.example",
    )
    # Die Einladung in der Demo-Mailbox durch die bösartige ersetzen.
    mb = client.app.state.open_mailbox
    with mb(client.app.state.accounts["demo"]) as b:
        for m in b._folders["INBOX"]:
            if m.uid == 116:
                idx = b._folders["INBOX"].index(m)
                b._folders["INBOX"][idx] = replace(m, calendar_raw=bad_ics)
                break
    r = client.post("/api/invite/respond",
                    json={"account": "demo", "folder": "INBOX", "uid": 116, "response": "accepted"})
    assert r.status_code == 422
