"""Konversations-Threads: Wurzel-Ableitung, kontoweiter Faden, Zähler, Fallback."""

from dataclasses import replace

import pytest

from postfach.demo import _mail
from postfach.search import SearchIndex, thread_root_for


@pytest.fixture
def index(tmp_path):
    return SearchIndex(tmp_path / "search.db")


def _thread_mails():
    frage = replace(
        _mail(20, "Vereinsheim Schlüssel", "Martin Becker", "m.becker@web.example", "Hast du den Schlüssel?"),
        message_id="<vh-1@web.example>",
    )
    antwort = replace(
        _mail(21, "Re: Vereinsheim Schlüssel", "Alex", "alex@demo.example", "Klar, bringe ihn mit."),
        message_id="<vh-2@demo.example>",
        references="<vh-1@web.example>",
        date_iso="2026-07-19T10:00:00+02:00",
    )
    rueckfrage = replace(
        _mail(22, "Re: Vereinsheim Schlüssel", "Martin Becker", "m.becker@web.example", "Super, danke!"),
        message_id="<vh-3@web.example>",
        references="<vh-1@web.example> <vh-2@demo.example>",
        date_iso="2026-07-19T11:00:00+02:00",
    )
    solo = _mail(23, "Ganz was anderes", "Sabine", "s.krause@web.example", "Unabhängige Mail")
    return frage, antwort, rueckfrage, solo


# --- Wurzel-Ableitung (pure) ---


def test_thread_root_prefers_first_reference():
    frage, antwort, rueckfrage, solo = _thread_mails()
    assert thread_root_for(antwort) == "<vh-1@web.example>"
    assert thread_root_for(rueckfrage) == "<vh-1@web.example>"
    assert thread_root_for(frage) == "<vh-1@web.example>"  # eigene Message-ID
    assert thread_root_for(solo) == solo.message_id


def test_thread_root_without_message_id_is_unique_per_mail():
    a = replace(_mail(30, "X", "A", "a@x.de", "t"), message_id="")
    b = replace(_mail(31, "X", "B", "b@x.de", "t"), message_id="")
    # Leere Message-IDs dürfen NICHT alle im selben ""-Faden landen
    assert thread_root_for(a) != thread_root_for(b)
    assert thread_root_for(a) == thread_root_for(a)  # aber stabil


# --- Faden im Index (kontoweit) ---


def test_thread_spans_folders_chronologically(index):
    frage, antwort, rueckfrage, solo = _thread_mails()
    index.add_mails("demo", "INBOX", [frage, rueckfrage, solo])
    index.add_mails("demo", "Gesendet", [antwort])
    hits = index.thread("demo", "<vh-1@web.example>")
    assert [(h["folder"], h["uid"]) for h in hits] == [
        ("INBOX", 20), ("Gesendet", 21), ("INBOX", 22),
    ]


def test_thread_root_lookup_for_indexed_mail(index):
    frage, antwort, *_ = _thread_mails()
    index.add_mails("demo", "INBOX", [frage])
    index.add_mails("demo", "Gesendet", [antwort])
    assert index.thread_root_of("demo", "Gesendet", 21) == "<vh-1@web.example>"
    assert index.thread_root_of("demo", "INBOX", 999) is None


def test_thread_counts_bulk(index):
    frage, antwort, rueckfrage, solo = _thread_mails()
    index.add_mails("demo", "INBOX", [frage, rueckfrage, solo])
    index.add_mails("demo", "Gesendet", [antwort])
    counts = index.thread_counts("demo", ["<vh-1@web.example>", thread_root_for(solo)])
    assert counts["<vh-1@web.example>"] == 3
    assert counts[thread_root_for(solo)] == 1


# --- Betreff-Fallback (nur bei eindeutigem Kandidaten) ---


def test_subject_fallback_joins_unique_thread(index):
    frage, antwort, *_ = _thread_mails()
    index.add_mails("demo", "INBOX", [frage])
    index.add_mails("demo", "Gesendet", [antwort])
    # Kaputter Client: Antwort ohne jede Referenz, aber Re:-Betreff + Gegenseite passt
    broken = replace(
        _mail(25, "AW: Vereinsheim Schlüssel", "Martin Becker", "m.becker@web.example", "PS: Danke!"),
        message_id="<vh-broken@web.example>",
        references="",
    )
    index.add_mails("demo", "INBOX", [broken])
    assert len(index.thread("demo", "<vh-1@web.example>")) == 3


def test_subject_fallback_refuses_ambiguous_candidates(index):
    # ZWEI Fäden desselben Absenders mit Betreff „Termin" → kein Raten möglich
    a = replace(_mail(40, "Termin", "A", "a@x.de", "t1"), message_id="<t-a@x>")
    b = replace(_mail(41, "Termin", "A", "a@x.de", "t2"), message_id="<t-b@x>",
                date_iso="2026-07-20T09:00:00+02:00")
    index.add_mails("demo", "INBOX", [a, b])
    broken = replace(
        _mail(42, "Re: Termin", "A", "a@x.de", "welcher?"),
        message_id="<t-c@x>", references="",
    )
    index.add_mails("demo", "INBOX", [broken])
    assert len(index.thread("demo", "<t-c@x>")) == 1  # eigener Faden statt raten


# --- API ---


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    return TestClient(create_app(root=tmp_path, demo=True))


def test_thread_route_spans_folders(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    # Demo-Faden: Martins Frage (INBOX) + Alex' Antwort (Gesendet)
    hits = client.get("/api/messages/demo/114/thread", params={"folder": "INBOX"}).json()
    assert len(hits) >= 2
    assert {h["folder"] for h in hits} >= {"INBOX", "Gesendet"}
    dates = [h["date"] for h in hits]
    assert dates == sorted(dates)


def test_thread_route_without_index_returns_empty(client):
    # Ohne Index: [] — die UI zeigt die Leiste erst ab 2 Mails, ein
    # IMAP-Roundtrip für einen unsichtbaren Ein-Mail-Faden wäre Verschwendung.
    assert client.get("/api/messages/demo/109/thread", params={"folder": "INBOX"}).json() == []


def test_thread_route_marks_sent_copies(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    hits = client.get("/api/messages/demo/114/thread", params={"folder": "INBOX"}).json()
    by_folder = {h["folder"]: h["is_sent"] for h in hits}
    assert by_folder["Gesendet"] is True and by_folder["INBOX"] is False


def test_messages_carry_thread_count(client):
    msgs = client.get("/api/messages", params={"account": "demo", "folder": "INBOX"}).json()
    assert all(m["thread_count"] == 1 for m in msgs)  # ohne Index: immer 1
    client.post("/api/emilia/index", json={"account": "demo"})
    msgs = client.get("/api/messages", params={"account": "demo", "folder": "INBOX"}).json()
    [vereinsheim] = [m for m in msgs if m["uid"] == 114]
    assert vereinsheim["thread_count"] >= 2
    [telekom] = [m for m in msgs if m["uid"] == 109]
    assert telekom["thread_count"] == 1


# --- Review-Funde Batch 4 ---


def test_subject_fallback_works_within_single_add(index):
    # Voll-Index: EIN add_mails-Aufruf, UID-absteigend (wie list_messages liefert) —
    # die kaputte Antwort muss ihre Wurzel trotzdem finden.
    frage, antwort, *_ = _thread_mails()
    broken = replace(
        _mail(25, "AW: Vereinsheim Schlüssel", "Martin Becker", "m.becker@web.example", "PS!"),
        message_id="<vh-broken@web.example>", references="",
    )
    index.add_mails("demo", "INBOX", [broken, frage])  # absteigende UIDs
    assert len(index.thread("demo", "<vh-1@web.example>")) == 2


def test_reindex_keeps_fallback_root(index):
    # Ein späterer Re-Index (Watcher-Upsert) darf einen per Fallback
    # zugeordneten Faden nicht wieder zerreißen — auch wenn inzwischen ein
    # zweiter Kandidat existiert.
    frage, *_ = _thread_mails()
    broken = replace(
        _mail(25, "AW: Vereinsheim Schlüssel", "Martin Becker", "m.becker@web.example", "PS!"),
        message_id="<vh-broken@web.example>", references="",
    )
    index.add_mails("demo", "INBOX", [frage])
    index.add_mails("demo", "INBOX", [broken])
    assert len(index.thread("demo", "<vh-1@web.example>")) == 2
    konkurrent = replace(
        _mail(26, "Vereinsheim Schlüssel", "Martin Becker", "m.becker@web.example", "Neues Thema"),
        message_id="<vh-neu@web.example>",
    )
    index.add_mails("demo", "INBOX", [konkurrent, broken, frage])  # Re-Index
    assert len(index.thread("demo", "<vh-1@web.example>")) == 2


def test_fallback_counterparty_is_token_matched(index):
    # a@x.de ist SUBSTRING von petra@x.de — darf aber nicht andocken.
    from postfach.mail_imap import ParsedMail
    from dataclasses import replace as rep

    an_petra = replace(
        _mail(50, "Angebot", "Alex", "alex@demo.example", "Unser Angebot"),
        message_id="<p1@x>",
    )
    an_petra = rep(an_petra, to=("petra@x.de",))
    index.add_mails("demo", "Gesendet", [an_petra])
    fremd = replace(
        _mail(51, "Re: Angebot", "Anna", "a@x.de", "Welches Angebot?"),
        message_id="<f1@x>", references="",
    )
    index.add_mails("demo", "INBOX", [fremd])
    assert len(index.thread("demo", "<p1@x>")) == 1  # kein Fremd-Andocken
    assert len(index.thread("demo", "<f1@x>")) == 1


def test_references_with_rfc_comment(index):
    from postfach.search import thread_root_for

    weird = replace(
        _mail(60, "X", "A", "a@x.de", "t"),
        message_id="<w2@x>", references="(added by gateway) <w1@x> <w1b@x>",
    )
    assert thread_root_for(weird) == "<w1@x>"


def test_in_reply_to_fallback_in_parser():
    # Viele Clients setzen nur In-Reply-To — der Parser nutzt ihn als References-Ersatz.
    from postfach.mail_imap import parse_full

    raw = (
        b"Message-ID: <child@x>\r\nIn-Reply-To: <parent@x>\r\n"
        b"From: A <a@x.de>\r\nTo: b@x.de\r\nSubject: Re: Hallo\r\n"
        b"Date: Mon, 20 Jul 2026 10:00:00 +0200\r\n\r\nText"
    )
    mail = parse_full(1, raw, seen=True)
    assert "<parent@x>" in mail.references
