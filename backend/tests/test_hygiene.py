"""Posteingangs-Hygiene: Abo-Manager (List-Unsubscribe) + Screener."""

from dataclasses import replace

import pytest

from postfach.demo import _mail
from postfach.unsubscribe import parse_list_unsubscribe


# --- List-Unsubscribe-Parsing (pure) ---


def test_parse_both_mailto_and_https():
    parsed = parse_list_unsubscribe(
        "<mailto:unsub@news.example?subject=stop>, <https://news.example/u/123>"
    )
    assert parsed.mailto == "unsub@news.example"
    assert parsed.mailto_subject == "stop"
    assert parsed.https == "https://news.example/u/123"


def test_parse_rejects_http_and_garbage():
    parsed = parse_list_unsubscribe("<http://insecure.example/u>, <javascript:alert(1)>")
    assert parsed.https is None and parsed.mailto is None


def test_parse_empty():
    parsed = parse_list_unsubscribe("")
    assert parsed.https is None and parsed.mailto is None


# --- Index: Abos + is_sent ---


@pytest.fixture
def index(tmp_path):
    from postfach.search import SearchIndex

    return SearchIndex(tmp_path / "search.db")


def _newsletter(uid, date="2026-07-01T10:00:00"):
    return replace(
        _mail(uid, f"Deals #{uid}", "TechDeals", "sale@techdeals.example", "Rabatt!"),
        date_iso=date,
        headers={"list-unsubscribe": "<https://techdeals.example/u/1>",
                 "list-unsubscribe-post": "List-Unsubscribe=One-Click"},
    )


def test_subscriptions_grouped_with_frequency(index):
    index.add_mails("demo", "INBOX", [
        _newsletter(1, "2026-06-21T10:00:00"),
        _newsletter(2, "2026-07-01T10:00:00"),
        _newsletter(3, "2026-07-21T10:00:00"),
        _mail(4, "Privat", "Martin", "m@web.example", "Hi"),  # kein Abo
    ])
    [sub] = index.subscriptions("demo")
    assert sub["addr"] == "sale@techdeals.example"
    assert sub["count"] == 3
    assert sub["method"] == "oneclick"
    assert sub["per_month"] == pytest.approx(3.0, rel=0.2)  # 3 Mails in 30 Tagen


def test_subscription_method_detection(index):
    mailto_only = replace(
        _mail(10, "News", "Mailer", "m@list.example", "x"),
        headers={"list-unsubscribe": "<mailto:stop@list.example>"},
    )
    link_only = replace(
        _mail(11, "News", "Linker", "l@link.example", "x"),
        headers={"list-unsubscribe": "<https://link.example/u>"},
    )
    index.add_mails("demo", "INBOX", [mailto_only, link_only])
    methods = {s["addr"]: s["method"] for s in index.subscriptions("demo")}
    assert methods["m@list.example"] == "mailto"
    assert methods["l@link.example"] == "link"


def test_first_contacts_excludes_known_and_old(index):
    from datetime import datetime, timedelta

    now = datetime.now()
    fresh = (now - timedelta(days=3)).isoformat(timespec="seconds")
    old = (now - timedelta(days=90)).isoformat(timespec="seconds")
    # Neuer Erstkontakt
    index.add_mails("demo", "INBOX", [replace(_mail(20, "Anfrage", "Neu", "neu@x.de", "Hallo"), date_iso=fresh)])
    # Alter Bekannter (erste Mail vor 90 Tagen)
    index.add_mails("demo", "INBOX", [replace(_mail(21, "Alt", "Alt", "alt@x.de", "Hi"), date_iso=old)])
    # Jemand, dem ICH geschrieben habe (Gesendet-Mail an ihn)
    sent = replace(_mail(22, "Re: Los", "Alex", "alex@demo.example", "Antwort"), date_iso=fresh)
    sent = replace(sent, to=("beantwortet@x.de",))
    index.add_mails("demo", "Gesendet", [sent])
    index.add_mails("demo", "INBOX", [replace(_mail(23, "Los", "B", "beantwortet@x.de", "?"), date_iso=fresh)])

    pending = index.first_contacts("demo", days=30, exclude=["alex@demo.example"])
    addrs = {p["addr"] for p in pending}
    assert "neu@x.de" in addrs
    assert "alt@x.de" not in addrs  # zu alt = etabliert
    assert "beantwortet@x.de" not in addrs  # dem habe ich geschrieben


# --- API (Demo) ---


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    c = TestClient(create_app(root=tmp_path, demo=True))
    c.put("/api/settings", json={"undo_seconds": 0})
    return c


def test_subscriptions_route_lists_demo_newsletters(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    subs = client.get("/api/subscriptions", params={"account": "demo"}).json()
    assert any(s["addr"] == "newsletter@3dprintweekly.example" for s in subs)


def test_unsubscribe_mailto_sends_mail(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    r = client.post("/api/subscriptions/unsubscribe",
                    json={"account": "demo", "addr": "sale@techdeals.example"})
    assert r.json()["ok"] is True and r.json()["method"] == "mailto"
    sent = client.get("/api/messages", params={"account": "demo", "folder": "Gesendet"}).json()
    assert any("unsubscribe" in m["subject"].lower() for m in sent)
    # Status gemerkt + Doppel-Abmeldung verhindert
    subs = client.get("/api/subscriptions", params={"account": "demo"}).json()
    [deals] = [s for s in subs if s["addr"] == "sale@techdeals.example"]
    assert deals["unsubscribed_at"]
    assert client.post("/api/subscriptions/unsubscribe",
                       json={"account": "demo", "addr": "sale@techdeals.example"}).status_code == 409


def test_unsubscribe_link_only_returns_url(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    r = client.post("/api/subscriptions/unsubscribe",
                    json={"account": "demo", "addr": "news@modehaus.example"})
    assert r.json() == {"ok": False, "method": "link", "link": "https://modehaus.example/abmelden"}


def test_screener_lists_first_contacts_with_suggestion(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    pending = client.get("/api/screener", params={"account": "demo"}).json()
    addrs = {p["addr"]: p for p in pending}
    assert "s.krause@mail.example" in addrs  # Erstkontakt, persönlich
    assert addrs["s.krause@mail.example"]["suggestion"] == "allow"
    # Newsletter mit Unsubscribe-Header → eher ablehnen
    newsletter = next((p for p in pending if p["addr"] == "newsletter@3dprintweekly.example"), None)
    assert newsletter and newsletter["suggestion"] == "block"


def test_screener_decision_persists_and_blocks_future_mail(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    r = client.post("/api/screener/decide",
                    json={"account": "demo", "addr": "s.krause@mail.example", "decision": "allow"})
    assert r.json() == {"ok": True}
    pending = client.get("/api/screener", params={"account": "demo"}).json()
    assert all(p["addr"] != "s.krause@mail.example" for p in pending)
    # Block-Entscheidung → der Zustell-Hook sortiert künftige Mails aus
    client.post("/api/screener/decide",
                json={"account": "demo", "addr": "sale@techdeals.example", "decision": "block"})
    assert client.app.state.screener.status("demo", "sale@techdeals.example") == "block"


def test_split_blocked_partitions_case_insensitive():
    from postfach.notify import split_blocked

    mails = [_mail(1, "Deals", "TechDeals", "Sale@TechDeals.example", "x"),
             _mail(2, "Hi", "Freund", "friend@x.de", "y")]
    kept, sorted_out = split_blocked(mails, {"sale@techdeals.example"})
    assert [m.uid for m in kept] == [2]
    assert [m.uid for m in sorted_out] == [1]


def test_split_blocked_empty_rules_is_noop():
    from postfach.notify import split_blocked

    mails = [_mail(1, "A", "X", "a@x.de", "x")]
    kept, sorted_out = split_blocked(mails, set())
    assert kept == mails and sorted_out == []


# --- Review-Härtung (Batch-6-Review) ---


def test_one_click_post_body_is_rfc8058_exact(monkeypatch):
    """RFC 8058 §3.2: Body ist exakt 'List-Unsubscribe=One-Click'."""
    from postfach import unsubscribe

    seen = {}

    def fake_post(url, content=None, headers=None, timeout=None, follow_redirects=None):
        seen["content"] = content

        class R:
            status_code = 200
        return R()

    monkeypatch.setattr(unsubscribe.httpx, "post", fake_post)
    monkeypatch.setattr(unsubscribe, "_host_is_public", lambda host: True)
    unsubscribe.one_click_post("https://news.example/u/1")
    assert seen["content"] == "List-Unsubscribe=One-Click"


def test_one_click_post_rejects_internal_hosts(monkeypatch):
    """SSRF-Schutz: private/Loopback/Link-Local-Ziele werden NIE angePOSTet."""
    from postfach import unsubscribe

    def explode(*a, **k):
        raise AssertionError("HTTP-Request an internes Ziel!")

    monkeypatch.setattr(unsubscribe.httpx, "post", explode)
    for url in ("https://localhost/admin", "https://127.0.0.1/x",
                "https://169.254.169.254/latest/meta-data/", "https://192.168.1.1/api"):
        with pytest.raises(ValueError):
            unsubscribe.one_click_post(url)


def test_migration_backfills_is_sent(tmp_path):
    """Bestands-DB (v0.7, ohne is_sent): Gesendet-Zeilen müssen beim Update
    sofort is_sent=1 bekommen — sonst flutet der Screener mit Bekannten."""
    import sqlite3

    from postfach.search import SearchIndex

    db = tmp_path / "search.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE mails (id INTEGER PRIMARY KEY, account TEXT NOT NULL,"
        " folder TEXT NOT NULL, uid INTEGER NOT NULL, subject TEXT NOT NULL DEFAULT '',"
        " from_name TEXT NOT NULL DEFAULT '', from_addr TEXT NOT NULL DEFAULT '',"
        " from_text TEXT NOT NULL DEFAULT '', recipients TEXT NOT NULL DEFAULT '',"
        " date_iso TEXT NOT NULL DEFAULT '', has_attachments INTEGER NOT NULL DEFAULT 0,"
        " seen INTEGER NOT NULL DEFAULT 1, snippet TEXT NOT NULL DEFAULT '',"
        " body TEXT NOT NULL DEFAULT '', message_id TEXT NOT NULL DEFAULT '',"
        " thread_root TEXT NOT NULL DEFAULT '', subject_norm TEXT NOT NULL DEFAULT '',"
        " UNIQUE(account, folder, uid))"
    )
    conn.execute("CREATE TABLE meta (account TEXT PRIMARY KEY, full_index_at TEXT NOT NULL)")
    conn.execute("INSERT INTO meta VALUES ('real', '2026-07-01T00:00:00')")
    conn.execute(
        "INSERT INTO mails (account, folder, uid, from_addr, recipients, date_iso)"
        " VALUES ('real', 'Gesendet', 1, 'ich@gmx.example', 'freund@x.de', '2026-07-18T10:00:00')"
    )
    conn.execute(
        "INSERT INTO mails (account, folder, uid, from_addr, date_iso)"
        " VALUES ('real', 'INBOX', 2, 'freund@x.de', '2026-07-18T11:00:00')"
    )
    conn.commit()
    conn.close()

    index = SearchIndex(db)
    pending = index.first_contacts("real", days=30, exclude=["ich@gmx.example"])
    assert all(p["addr"] != "freund@x.de" for p in pending)  # dem habe ich geschrieben


def test_subscriptions_method_matches_newest_header_pair(index):
    """Liste und Aktion dürfen nicht auseinanderlaufen: method kommt vom
    Header-PAAR der neuesten Mail — nie aus MAX() über verschiedene Mails."""
    old = replace(
        _mail(30, "News #1", "Mixer", "mix@list.example", "x"),
        date_iso="2026-06-01T10:00:00",
        headers={"list-unsubscribe": "<https://list.example/u/alt>",
                 "list-unsubscribe-post": "List-Unsubscribe=One-Click"},
    )
    new = replace(
        _mail(31, "News #2", "Mixer", "mix@list.example", "x"),
        date_iso="2026-07-20T10:00:00",
        headers={"list-unsubscribe": "<aaaa-kaputt>"},  # kaputter Header, KEIN post
    )
    index.add_mails("demo", "INBOX", [old, new])
    [sub] = index.subscriptions("demo")
    assert sub["method"] == "none"  # neueste Mail hat nichts Verwertbares


def test_unsubscribe_smtp_failure_returns_502(client, monkeypatch):
    from postfach import api as api_mod

    def boom(state, body, attachments):
        raise OSError("SMTP kaputt")

    monkeypatch.setattr(api_mod, "perform_send", boom)
    client.post("/api/emilia/index", json={"account": "demo"})
    r = client.post("/api/subscriptions/unsubscribe",
                    json={"account": "demo", "addr": "sale@techdeals.example"})
    assert r.status_code == 502
    # Fehlversand darf NICHT als abgemeldet markiert werden
    subs = client.get("/api/subscriptions", params={"account": "demo"}).json()
    [deals] = [s for s in subs if s["addr"] == "sale@techdeals.example"]
    assert deals["unsubscribed_at"] is None
