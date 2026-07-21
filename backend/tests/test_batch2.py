"""Batch 2 — Empfangen & Ordnung: Spam, Bulk-Triage, Klassifikations-Override,
Verbindungsstatus, Benachrichtigungs-Einstellungen."""

import pytest
from fastapi.testclient import TestClient

from postfach.app import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(root=tmp_path, demo=True))


def _inbox_uids(client) -> set[int]:
    msgs = client.get("/api/messages", params={"account": "demo", "folder": "INBOX"}).json()
    return {m["uid"] for m in msgs}


# --- Spam-Markierung ---


def test_spam_action_moves_to_junk_and_back(client):
    uid = sorted(_inbox_uids(client))[0]
    r = client.post(f"/api/messages/demo/{uid}/action", json={"action": "spam", "folder": "INBOX"})
    assert r.status_code == 200
    assert uid not in _inbox_uids(client)
    spam = client.get("/api/messages", params={"account": "demo", "folder": "Spam"}).json()
    assert uid in {m["uid"] for m in spam}

    r = client.post(f"/api/messages/demo/{uid}/action", json={"action": "unspam", "folder": "Spam"})
    assert r.status_code == 200
    assert uid in _inbox_uids(client)


def test_junk_names_include_gmx_spamverdacht():
    from postfach.mail_imap import _JUNK_NAMES

    assert "spamverdacht" in _JUNK_NAMES and "junk" in _JUNK_NAMES


# --- Bulk-Triage ---


def test_batch_action_trash_moves_all(client):
    uids = sorted(_inbox_uids(client))[:3]
    r = client.post("/api/batch-action", json={
        "account": "demo", "folder": "INBOX", "uids": uids, "action": "trash",
    })
    assert r.status_code == 200
    assert r.json() == {"ok": True, "done": 3}
    remaining = _inbox_uids(client)
    assert not remaining & set(uids)
    papierkorb = client.get("/api/messages", params={"account": "demo", "folder": "Papierkorb"}).json()
    assert set(uids) <= {m["uid"] for m in papierkorb}


def test_batch_action_read_marks_seen(client):
    msgs = client.get("/api/messages", params={"account": "demo", "folder": "INBOX"}).json()
    unread = [m["uid"] for m in msgs if not m["seen"]]
    assert unread
    r = client.post("/api/batch-action", json={
        "account": "demo", "folder": "INBOX", "uids": unread, "action": "read",
    })
    assert r.status_code == 200
    msgs = client.get("/api/messages", params={"account": "demo", "folder": "INBOX"}).json()
    assert all(m["seen"] for m in msgs if m["uid"] in set(unread))


def test_batch_action_archive_respects_category_mapping(client):
    # Zwei Mails klassifizieren (Demo-Regeln), dann bulk-archivieren:
    # jede landet im Zielordner IHRER Kategorie (nicht alle im selben).
    uids = sorted(_inbox_uids(client))[:2]
    client.post("/api/classify", json={"account": "demo", "folder": "INBOX", "uids": uids})
    r = client.post("/api/batch-action", json={
        "account": "demo", "folder": "INBOX", "uids": uids, "action": "archive",
    })
    assert r.status_code == 200
    assert not _inbox_uids(client) & set(uids)


def test_batch_action_rejects_unknown_action_and_send(client):
    for bad in ("explode", "send"):
        r = client.post("/api/batch-action", json={
            "account": "demo", "folder": "INBOX", "uids": [109], "action": bad,
        })
        assert r.status_code == 422


# --- Klassifikation korrigierbar ---


def test_classify_override_wins_and_survives_reclassify(client):
    uid = sorted(_inbox_uids(client))[0]
    categories = list(client.app.state.config.agent.taxonomy)
    target = categories[0]
    r = client.post("/api/classify/override", json={
        "account": "demo", "folder": "INBOX", "uid": uid, "category": target,
    })
    assert r.status_code == 200
    # erneutes classify darf den User-Override nicht überschreiben
    client.post("/api/classify", json={"account": "demo", "folder": "INBOX", "uids": [uid]})
    msgs = client.get("/api/messages", params={"account": "demo", "folder": "INBOX"}).json()
    [mail] = [m for m in msgs if m["uid"] == uid]
    assert mail["category"] == target


def test_classify_override_rejects_unknown_category(client):
    r = client.post("/api/classify/override", json={
        "account": "demo", "folder": "INBOX", "uid": 109, "category": "GibtEsNicht",
    })
    assert r.status_code == 422


# --- Verbindungsstatus ---


def test_livestate_tracks_connection_status():
    from postfach.watcher import LiveState

    state = LiveState()
    state.set_status("gmx", connected=True)
    snap = state.status_snapshot()
    assert snap["gmx"]["connected"] is True
    assert snap["gmx"]["since"]  # ISO-Zeitstempel
    assert snap["gmx"]["last_error"] is None

    state.set_status("gmx", connected=False, error="Verbindung verloren")
    snap = state.status_snapshot()
    assert snap["gmx"]["connected"] is False
    assert snap["gmx"]["last_error"] == "Verbindung verloren"


def test_status_endpoint_shape(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    assert "accounts" in r.json()


# --- Benachrichtigungs-Einstellungen ---


def test_settings_roundtrip_notifications(client):
    r = client.put("/api/settings", json={
        "signatures": {}, "notifications": {"demo": False},
    })
    assert r.status_code == 200
    data = client.get("/api/settings").json()
    assert data["notifications"] == {"demo": False}
    assert "signatures" in data


def test_notify_macos_passes_untrusted_text_as_argv(monkeypatch):
    # Mail-Inhalte sind untrusted: Titel/Text dürfen NIE in den
    # AppleScript-String interpoliert werden (Injection), sondern nur via argv.
    import postfach.notify as notify

    calls = []
    monkeypatch.setattr(notify.subprocess, "run", lambda *a, **k: calls.append(a[0]))
    notify.notify_macos('Böser" & do shell script "…', 'Betreff mit "Quotes"')
    [argv] = calls
    script = argv[argv.index("-e") + 1]
    assert "Böser" not in script  # Inhalte stecken in argv, nicht im Skript
    assert 'Böser" & do shell script "…' in argv


def test_categories_endpoint_lists_taxonomy(client):
    cats = client.get("/api/categories").json()
    assert cats == sorted(client.app.state.config.agent.taxonomy)
    assert len(cats) > 0


# --- Review-Funde Batch 2 ---


def test_classify_never_overwrites_user_override_set_mid_run(tmp_path):
    # Race: Override kommt WÄHREND ein classify-Lauf rechnet — der Write-back
    # darf den User-Eintrag nicht überschreiben.
    from postfach.ai import DemoAiService
    from postfach.config import load_postfach_config

    cfg = load_postfach_config(tmp_path / "nope.yaml")
    ai = DemoAiService(cfg.agent, tmp_path / "cache.json", tmp_path / "style.md")

    from postfach.demo import _mail

    mail = _mail(7, "Newsletter der Woche", "Shop", "news@shop.example", "Rabatt")

    original_fresh = ai._classify_fresh

    def fresh_with_race(missing):
        # Simuliert den Override, der während des LLM-Laufs eintrifft
        ai.override_category("demo", "INBOX", 7, "Verein")
        return original_fresh(missing)

    ai._classify_fresh = fresh_with_race
    ai.classify("demo", "INBOX", [mail])
    assert ai.cached_categories("demo", "INBOX", [7]) == {7: "Verein"}


def test_override_without_prior_entry_writes_complete_shape(tmp_path):
    from postfach.ai import DemoAiService
    from postfach.config import load_postfach_config

    cfg = load_postfach_config(tmp_path / "nope.yaml")
    ai = DemoAiService(cfg.agent, tmp_path / "cache.json", tmp_path / "style.md")
    ai.override_category("demo", "INBOX", 9, "Finanzen")
    entry = ai._load_cache()["demo:INBOX:9"]
    assert entry["category"] == "Finanzen" and entry["source"] == "user"
    for field in ("is_newsletter", "interesting", "needs_reply", "reason"):
        assert field in entry


def test_put_settings_without_notifications_keeps_existing_toggles(client):
    client.put("/api/settings", json={"signatures": {}, "notifications": {"demo": False}})
    # Alter Client (Batch-1-Contract) schickt nur signatures — Toggles bleiben.
    client.put("/api/settings", json={"signatures": {"demo": "Gruß"}})
    data = client.get("/api/settings").json()
    assert data["notifications"] == {"demo": False}
    assert data["signatures"] == {"demo": "Gruß"}


def test_spam_on_spam_folder_is_a_noop(client):
    uid = sorted(_inbox_uids(client))[0]
    client.post(f"/api/messages/demo/{uid}/action", json={"action": "spam", "folder": "INBOX"})
    # Spam auf bereits-Spam: Quelle == Ziel → kein Self-Move (serverabhängig NO/UID-Wechsel)
    r = client.post(f"/api/messages/demo/{uid}/action", json={"action": "spam", "folder": "Spam"})
    assert r.status_code == 200
    spam = client.get("/api/messages", params={"account": "demo", "folder": "Spam"}).json()
    assert [m["uid"] for m in spam].count(uid) == 1


def test_pick_new_unseen_dedupes_notifications():
    from postfach.demo import _mail
    from dataclasses import replace
    from postfach.notify import pick_new_unseen

    m1 = _mail(101, "Alt", "A", "a@x.de", "t")
    m2 = replace(_mail(102, "Neu 1", "B", "b@x.de", "t"), seen=False)
    m3 = replace(_mail(103, "Neu 2", "C", "c@x.de", "t"), seen=False)
    fresh = pick_new_unseen([m3, m2, m1], last_uid=101)
    assert [m.uid for m in fresh] == [102, 103]  # nur neue Ungelesene, aufsteigend
    # Zweiter Aufruf mit fortgeschriebenem Wasserstand: nichts mehr zu melden
    assert pick_new_unseen([m3, m2, m1], last_uid=103) == []


def test_move_many_chunks_large_uid_lists(tmp_path):
    # Riesige UID-Listen sprengen die IMAP-Kommandozeile — in Blöcken senden.
    from postfach.mail_imap import Mailbox

    class FakeClient:
        def __init__(self):
            self.moves = []
        def select_folder(self, *a, **k):
            pass
        def move(self, uids, target):
            self.moves.append(list(uids))
        def list_folders(self):
            return []

    box = Mailbox.__new__(Mailbox)
    box._client = FakeClient()
    box.move_many("INBOX", list(range(1, 1201)), "Ziel")
    assert len(box._client.moves) == 3  # 500er-Chunks
    assert sum(len(c) for c in box._client.moves) == 1200


def test_watcher_reidle_checks_pending_responses():
    from postfach.watcher import _has_new_mail

    assert _has_new_mail([(5, b"EXISTS")])
    assert not _has_new_mail([(2, b"EXPUNGE")])
    assert not _has_new_mail(None)
