"""Lokale Volltextsuche (SQLite-FTS5): Index, Operatoren, Injection, Tempo."""

import time
from dataclasses import replace

import pytest

from postfach.demo import _mail
from postfach.search import SearchIndex, parse_query


@pytest.fixture
def index(tmp_path):
    return SearchIndex(tmp_path / "search.db")


def _mails():
    m1 = _mail(1, "Rechnung Juli", "Telekom", "rechnung@telekom.example",
               "Ihre Rechnung über 39,95 € finden Sie im Anhang.")
    m1 = replace(m1, attachments=(("dummy",),))  # has_attachments = truthy
    m2 = _mail(2, "Training am Samstag", "Martin Becker", "m.becker@web.example",
               "Kannst du die Trainingsgruppe übernehmen? Grüße Martin")
    m3 = _mail(3, "Angebot Müller GmbH", "Petra Müller", "petra@mueller.example",
               "Unser Angebot für die Webseite liegt bei.")
    return [m1, m2, m3]


# --- parse_query (pure) ---


def test_parse_query_extracts_operators_and_text():
    q = parse_query('von:martin betreff:training vor:2026-08-01 nach:2026-01-01 hat:anhang "am samstag" gruppe')
    assert q.from_ == "martin"
    assert q.subject == "training"
    assert q.before == "2026-08-01"
    assert q.after == "2026-01-01"
    assert q.has_attachment is True
    assert q.phrases == ["am samstag"]
    assert q.text == ["gruppe"]


def test_parse_query_plain_text_only():
    q = parse_query("rechnung telekom")
    assert q.text == ["rechnung", "telekom"]
    assert q.from_ is None and q.subject is None and q.has_attachment is None


# --- Index & Suche ---


def test_fulltext_finds_body_and_subject(index):
    index.add_mails("demo", "INBOX", _mails())
    assert [m["uid"] for m in index.search("demo", "trainingsgruppe")] == [2]
    assert [m["uid"] for m in index.search("demo", "rechnung")] == [1]


def test_umlauts_and_diacritics(index):
    index.add_mails("demo", "INBOX", _mails())
    assert [m["uid"] for m in index.search("demo", "müller")] == [3]
    assert [m["uid"] for m in index.search("demo", "muller")] == [3]  # remove_diacritics


def test_operators_filter(index):
    index.add_mails("demo", "INBOX", _mails())
    assert [m["uid"] for m in index.search("demo", "von:becker")] == [2]
    assert [m["uid"] for m in index.search("demo", "betreff:rechnung")] == [1]
    assert [m["uid"] for m in index.search("demo", "hat:anhang")] == [1]
    assert index.search("demo", "an:alex@demo.example")  # Demo-Mails gehen an Alex


def test_phrase_search(index):
    index.add_mails("demo", "INBOX", _mails())
    assert [m["uid"] for m in index.search("demo", '"trainingsgruppe übernehmen"')] == [2]
    assert index.search("demo", '"übernehmen trainingsgruppe"') == []


def test_date_filters(index):
    old = replace(_mail(9, "Alt", "A", "a@x.de", "alter Inhalt"), date_iso="2025-01-01T10:00:00")
    index.add_mails("demo", "INBOX", [*_mails(), old])
    hits = index.search("demo", "vor:2026-01-01")
    assert [m["uid"] for m in hits] == [9]
    hits = index.search("demo", "nach:2026-01-01 rechnung")
    assert [m["uid"] for m in hits] == [1]


def test_fts_syntax_from_user_is_treated_as_literal(index):
    index.add_mails("demo", "INBOX", _mails())
    # FTS-Metazeichen dürfen weder crashen noch als Syntax wirken
    for evil in ('rechnung"', 'a AND b OR c*', 'NEAR(x y)', '"unclosed', "col:val"):
        index.search("demo", evil)  # darf nicht raisen


def test_search_spans_all_folders_and_filters_optionally(index):
    index.add_mails("demo", "INBOX", _mails()[:2])
    index.add_mails("demo", "Archiv/2026", [_mails()[2]])
    all_hits = index.search("demo", "angebot")
    assert [(m["folder"], m["uid"]) for m in all_hits] == [("Archiv/2026", 3)]
    assert index.search("demo", "angebot", folder="INBOX") == []


def test_reindex_is_upsert(index):
    index.add_mails("demo", "INBOX", _mails())
    index.add_mails("demo", "INBOX", _mails())  # zweiter Lauf: keine Duplikate
    assert index.count("demo") == 3
    assert len(index.search("demo", "rechnung")) == 1


def test_moved_mails_leave_the_index(index):
    # IMAP-MOVE vergibt im Zielordner NEUE UIDs — ein "Umzug" im Index wäre
    # ein toter 404-Treffer. Der Eintrag fliegt raus, Re-Index füllt nach.
    index.add_mails("demo", "INBOX", _mails())
    index.remove_mails("demo", "INBOX", [1])
    assert index.search("demo", "rechnung") == []
    assert index.count("demo") == 2
    index.remove_mails("demo", "INBOX", [999])  # unbekannte UID: no-op


def test_ranking_prefers_subject_hits(index):
    a = _mail(11, "Projekt Bericht", "A", "a@x.de", "nichts weiter")
    b = _mail(12, "Notiz", "B", "b@x.de", "im bericht steht projekt und projekt und bericht")
    index.add_mails("demo", "INBOX", [a, b])
    assert index.search("demo", "projekt bericht")[0]["uid"] == 11


def test_summary_shape(index):
    index.add_mails("demo", "INBOX", _mails())
    [hit] = index.search("demo", "trainingsgruppe")
    for key in ("account", "folder", "uid", "subject", "from_name", "from_addr",
                "date", "snippet", "seen", "has_attachments", "category"):
        assert key in hit


def test_speed_on_5k_mails(tmp_path):
    index = SearchIndex(tmp_path / "big.db")
    batch = [
        _mail(i, f"Betreff {i} Lorem", f"Absender{i % 40}", f"a{i % 40}@x.de",
              f"Inhalt {i} mit Wörtern wie Vertrag Rechnung Termin Projekt Nummer{i}")
        for i in range(1, 5001)
    ]
    index.add_mails("demo", "INBOX", batch)
    start = time.perf_counter()
    hits = index.search("demo", "vertrag rechnung")
    elapsed = (time.perf_counter() - start) * 1000
    assert hits
    assert elapsed < 200, f"Suche dauerte {elapsed:.0f} ms"


# --- API-Integration ---


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    return TestClient(create_app(root=tmp_path, demo=True))


def test_api_search_uses_index_after_emilia_index(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    hits = client.get("/api/search", params={"account": "demo", "q": "trainingsgruppe"}).json()
    assert hits and hits[0]["subject"].startswith("Training")
    # Treffer aus ALLEN Ordnern: Gesendet-Mail wird ohne folder-Scope gefunden
    hits = client.get("/api/search", params={"account": "demo", "q": "vereinsheim"}).json()
    assert any(m["folder"] == "Gesendet" for m in hits)


def test_api_search_falls_back_to_imap_without_index(client):
    hits = client.get("/api/search", params={"account": "demo", "q": "Trainingsgruppe"}).json()
    assert hits and hits[0]["folder"] == "INBOX"  # DemoMailbox.search-Fallback


def test_api_search_status(client):
    assert client.get("/api/search/status", params={"account": "demo"}).json()["indexed"] == 0
    client.post("/api/emilia/index", json={"account": "demo"})
    assert client.get("/api/search/status", params={"account": "demo"}).json()["indexed"] > 0


def test_move_action_removes_stale_index_entry(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    [hit] = client.get("/api/search", params={"account": "demo", "q": "trainingsgruppe"}).json()
    client.post(f"/api/messages/demo/{hit['uid']}/action", json={"action": "archive", "folder": hit["folder"]})
    # Kein toter Treffer mit alter UID; der nächste Index-Lauf nimmt sie neu auf.
    assert client.get("/api/search", params={"account": "demo", "q": "trainingsgruppe"}).json() == []



# --- Review-Funde Batch 3 ---


def test_fast_path_requires_full_index_not_just_rows(client):
    # Der Live-Watcher schreibt einzelne Mails in den Index — das darf den
    # IMAP-Fallback nicht verschatten (10 Mails sind kein Suchbestand).
    client.app.state.search.add_mails("demo", "INBOX", [
        __import__("postfach.demo", fromlist=["_mail"])._mail(999, "Zufall", "X", "x@y.z", "inhalt")
    ])
    hits = client.get("/api/search", params={"account": "demo", "q": "Trainingsgruppe"}).json()
    assert hits and hits[0]["folder"] == "INBOX"  # IMAP-Fallback griff trotz Teil-Index


def test_search_status_reports_ready_flag(client):
    status = client.get("/api/search/status", params={"account": "demo"}).json()
    assert status == {"indexed": 0, "ready": False}
    client.post("/api/emilia/index", json={"account": "demo"})
    status = client.get("/api/search/status", params={"account": "demo"}).json()
    assert status["ready"] is True and status["indexed"] > 0


def test_hat_with_unknown_value_is_plain_text(index):
    index.add_mails("demo", "INBOX", _mails())
    # Tippfehler wie 'hat:anhänge' darf nicht still "ohne Anhang" filtern —
    # unbekannter Wert wird zur Volltextsuche nach dem Wert.
    assert [m["uid"] for m in index.search("demo", "hat:rechnung")] == [1]


def test_set_seen_updates_index(index):
    index.add_mails("demo", "INBOX", _mails())
    index.set_seen("demo", "INBOX", [2], False)
    [hit] = index.search("demo", "trainingsgruppe")
    assert hit["seen"] is False


def test_full_index_prunes_vanished_mails(index):
    index.add_mails("demo", "INBOX", _mails())
    # Voll-Lauf sieht Mail 1 nicht mehr (extern verschoben/gelöscht) → raus
    index.prune_folder("demo", "INBOX", keep_uids=[2, 3])
    assert index.search("demo", "rechnung") == []
    # Ordner, die der Voll-Lauf gar nicht mehr scannt (z. B. Papierkorb): leeren
    index.add_mails("demo", "Papierkorb", [_mails()[0]])
    index.prune_missing_folders("demo", scanned=["INBOX"])
    assert index.count("demo") == 2
