"""Zeit-Warteschlange: Store, Scheduler-Kern (synchron), Outbox-Payloads."""

import pytest

from postfach.schedule import OutboxStore, Scheduler, ScheduleStore


@pytest.fixture
def store(tmp_path):
    return ScheduleStore(tmp_path / "schedule.json")


@pytest.fixture
def outbox(tmp_path):
    return OutboxStore(tmp_path / "outbox")


def test_store_add_list_remove(store):
    job_id = store.add("send", "gmx", due="2026-07-22T08:00:00", payload={"subject": "Hi"})
    [job] = store.list("gmx")
    assert job["id"] == job_id and job["kind"] == "send" and job["due"] == "2026-07-22T08:00:00"
    assert store.remove(job_id) is True
    assert store.list("gmx") == [] and store.remove(job_id) is False


def test_store_due_returns_only_ripe_jobs(store):
    store.add("send", "gmx", due="2026-07-22T08:00:00", payload={})
    ripe_id = store.add("snooze", "gmx", due="2026-07-21T09:00:00", payload={})
    ripe = store.due("2026-07-21T10:00:00")
    assert [j["id"] for j in ripe] == [ripe_id]


def test_outbox_payload_roundtrip_with_attachments(outbox):
    outbox.save("job1", {"account": "gmx", "subject": "Hi"}, [("a.txt", "text/plain", b"inhalt")])
    body, attachments = outbox.load("job1")
    assert body["subject"] == "Hi"
    assert attachments == [("a.txt", "text/plain", b"inhalt")]
    outbox.delete("job1")
    assert outbox.load("job1") is None


def test_scheduler_executes_due_send_and_removes_job(store, outbox):
    sent = []
    scheduler = Scheduler(store, outbox, send_fn=lambda job: sent.append(job["id"]),
                          wake_fn=None, followup_fn=None, notify_fn=lambda *a: None)
    job_id = store.add("send", "gmx", due="2026-07-21T09:00:00", payload={})
    scheduler.process_due("2026-07-21T09:00:30")
    assert sent == [job_id]
    assert store.list("gmx") == []


def test_scheduler_retries_failed_send_then_gives_up(store, outbox):
    notes = []

    def failing(job):
        raise RuntimeError("SMTP down")

    scheduler = Scheduler(store, outbox, send_fn=failing, wake_fn=None,
                          followup_fn=None, notify_fn=lambda title, text: notes.append(title))
    store.add("send", "gmx", due="2026-07-21T09:00:00", payload={})
    for _ in range(3):
        scheduler.process_due("2026-07-21T09:01:00")
    [job] = store.list("gmx")
    assert job["attempts"] == 3 and job["kind"] == "send_failed"
    assert notes  # Nutzer wurde informiert — nie still scheitern
    # Fehlgeschlagene Jobs werden nicht erneut versucht
    scheduler.process_due("2026-07-21T09:02:00")
    assert store.list("gmx")[0]["attempts"] == 3


def test_scheduler_wakes_due_snooze(store, outbox):
    woken = []
    scheduler = Scheduler(store, outbox, send_fn=None,
                          wake_fn=lambda job: woken.append(job["payload"]["message_id"]),
                          followup_fn=None, notify_fn=lambda *a: None)
    store.add("snooze", "gmx", due="2026-07-21T09:00:00", payload={"message_id": "<m@x>"})
    scheduler.process_due("2026-07-21T09:00:01")
    assert woken == ["<m@x>"]
    assert store.list("gmx") == []


def test_scheduler_followup_resolves_or_flags(store, outbox):
    # Antwort vorhanden → Job löst sich still; keine Antwort → wird "fällig" und bleibt
    answered = {"a": True, "b": False}
    scheduler = Scheduler(store, outbox, send_fn=None, wake_fn=None,
                          followup_fn=lambda job: answered[job["payload"]["key"]],
                          notify_fn=lambda *a: None)
    store.add("followup", "gmx", due="2026-07-21T09:00:00", payload={"key": "a"})
    flagged_id = store.add("followup", "gmx", due="2026-07-21T09:00:00", payload={"key": "b"})
    scheduler.process_due("2026-07-21T09:00:01")
    [job] = store.list("gmx")
    assert job["id"] == flagged_id and job["kind"] == "followup_due"
    # Fällige Follow-ups bleiben, bis der Nutzer sie erledigt
    scheduler.process_due("2026-07-21T09:10:00")
    assert len(store.list("gmx")) == 1


# --- API-Integration (Demo) ---


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    return TestClient(create_app(root=tmp_path, demo=True))


def _send_body(**extra):
    return {"account": "demo", "to": ["a@b.de"], "subject": "Hi", "body": "T", **extra}


def test_send_with_undo_delay_schedules_instead_of_sending(client):
    client.put("/api/settings", json={"undo_seconds": 15})
    r = client.post("/api/send", json=_send_body())
    data = r.json()
    assert data["ok"] is True and data["scheduled"]["kind"] == "undo"
    # Noch nichts in Gesendet — der Job wartet
    sent = client.get("/api/messages", params={"account": "demo", "folder": "Gesendet"}).json()
    assert all(m["subject"] != "Hi" for m in sent)
    [entry] = client.get("/api/outbox", params={"account": "demo"}).json()
    assert entry["subject"] == "Hi" and entry["kind"] == "undo"
    # Storno: Job weg
    assert client.delete(f"/api/outbox/{entry['id']}").json() == {"ok": True}
    assert client.get("/api/outbox", params={"account": "demo"}).json() == []


def test_send_with_send_at_schedules_later(client):
    client.put("/api/settings", json={"undo_seconds": 0})
    r = client.post("/api/send", json=_send_body(send_at="2030-01-01T08:00:00"))
    assert r.json()["scheduled"]["kind"] == "later"
    [entry] = client.get("/api/outbox", params={"account": "demo"}).json()
    assert entry["due"].startswith("2030-01-01")


def test_send_without_delay_sends_immediately(client):
    client.put("/api/settings", json={"undo_seconds": 0})
    r = client.post("/api/send", json=_send_body())
    assert r.json() == {"ok": True}
    sent = client.get("/api/messages", params={"account": "demo", "folder": "Gesendet"}).json()
    assert any(m["subject"] == "Hi" for m in sent)


def test_scheduled_send_executes_and_lands_in_sent(client):
    client.put("/api/settings", json={"undo_seconds": 10})
    client.post("/api/send", json=_send_body())
    # Fälligkeit erzwingen: Scheduler-Kern direkt mit ferner Zukunft ticken
    client.app.state.scheduler.process_due("2099-01-01T00:00:00")
    sent = client.get("/api/messages", params={"account": "demo", "folder": "Gesendet"}).json()
    assert any(m["subject"] == "Hi" for m in sent)
    assert client.get("/api/outbox", params={"account": "demo"}).json() == []


def test_snooze_moves_mail_and_wakes_it(client):
    r = client.post("/api/messages/demo/109/snooze", json={"folder": "INBOX", "until": "2030-01-01T08:00:00"})
    assert r.json()["ok"] is True
    inbox = {m["uid"] for m in client.get("/api/messages", params={"account": "demo", "folder": "INBOX"}).json()}
    assert 109 not in inbox
    later = client.get("/api/messages", params={"account": "demo", "folder": "Später"}).json()
    assert any(m["subject"].startswith("Ihre Telekom") for m in later)
    [reminder] = client.get("/api/reminders", params={"account": "demo"}).json()
    assert reminder["kind"] == "snooze"
    # Aufwachen: zurück in die INBOX, ungelesen
    client.app.state.scheduler.process_due("2099-01-01T00:00:00")
    inbox = client.get("/api/messages", params={"account": "demo", "folder": "INBOX"}).json()
    [back] = [m for m in inbox if m["subject"].startswith("Ihre Telekom")]
    assert back["seen"] is False
    assert client.get("/api/reminders", params={"account": "demo"}).json() == []


def test_followup_flags_unanswered_and_done_clears(client):
    client.put("/api/settings", json={"undo_seconds": 0})
    client.post("/api/emilia/index", json={"account": "demo"})
    client.post("/api/send", json=_send_body(subject="Frage ohne Antwort", followup_days=3))
    client.app.state.scheduler.process_due("2099-01-01T00:00:00")
    [reminder] = [r for r in client.get("/api/reminders", params={"account": "demo"}).json() if r["kind"] == "followup_due"]
    assert "Frage ohne Antwort" in reminder["subject"]
    assert client.post(f"/api/reminders/{reminder['id']}/done").json() == {"ok": True}
    assert [r for r in client.get("/api/reminders", params={"account": "demo"}).json() if r["kind"] == "followup_due"] == []


def test_no_ai_path_reaches_scheduler():
    # Send-Jobs entstehen nur aus expliziten Senden-Klicks — kein KI-Modul
    # importiert die Warteschlange.
    from pathlib import Path

    src = Path(__file__).parent.parent / "src" / "postfach"
    for name in ("ai.py", "emilia.py", "memory.py"):
        assert "schedule" not in (src / name).read_text(encoding="utf-8")


# --- Review-Funde Batch 5 ---


def test_send_job_is_claimed_before_execution(store, outbox):
    # Storno WÄHREND des Versands darf nicht "gelingen": der Scheduler claimt
    # den Job (entfernt ihn) BEVOR gesendet wird — ein paralleles DELETE sieht 404.
    seen_during_send = []

    def send_fn(job):
        seen_during_send.append(store.remove(job["id"]))  # simuliert Storno mitten im Versand

    scheduler = Scheduler(store, outbox, send_fn=send_fn, wake_fn=None,
                          followup_fn=None, notify_fn=lambda *a: None)
    store.add("send", "gmx", due="2026-07-21T09:00:00", payload={})
    scheduler.process_due("2026-07-21T09:00:30")
    assert seen_during_send == [False]  # Job war schon geclaimt → Storno scheitert ehrlich


def test_failed_claimed_send_returns_to_queue_with_attempt(store, outbox):
    def failing(job):
        raise RuntimeError("SMTP down")

    scheduler = Scheduler(store, outbox, send_fn=failing, wake_fn=None,
                          followup_fn=None, notify_fn=lambda *a: None)
    store.add("send", "gmx", due="2026-07-21T09:00:00", payload={})
    scheduler.process_due("2026-07-21T09:00:30")
    [job] = store.list("gmx")
    assert job["kind"] == "send" and job["attempts"] == 1  # zurück in die Schlange


def test_all_kinds_stop_retrying_after_max_attempts(store, outbox):
    notes = []

    def failing(job):
        raise RuntimeError("Konto weg")

    scheduler = Scheduler(store, outbox, send_fn=None, wake_fn=failing,
                          followup_fn=None, notify_fn=lambda t, x: notes.append(t))
    store.add("snooze", "gmx", due="2026-07-21T09:00:00", payload={"subject": "S"})
    for _ in range(5):
        scheduler.process_due("2026-07-21T09:01:00")
    [job] = store.list("gmx")
    assert job["kind"] == "snooze_failed" and job["attempts"] == 3  # kein Endlos-Retry
    assert notes


def test_store_rejects_invalid_due():
    import pytest as _pytest

    from postfach.schedule import ScheduleStore
    import tempfile, pathlib

    store = ScheduleStore(pathlib.Path(tempfile.mkdtemp()) / "s.json")
    with _pytest.raises(ValueError):
        store.add("send", "gmx", due="morgen frueh", payload={})


def test_cancel_outbox_restores_draft(client):
    client.put("/api/settings", json={"undo_seconds": 15})
    r = client.post("/api/send", json={
        "account": "demo", "to": ["a@b.de"], "subject": "Nur im Outbox-Payload",
        "body": "Wichtiger Text", "draft_id": "undo-draft-1",
    })
    job_id = r.json()["scheduled"]["id"]
    # Kein Entwurf gespeichert (schneller Doppelklick) — Storno stellt ihn her
    client.delete(f"/api/outbox/{job_id}")
    drafts = client.get("/api/drafts", params={"account": "demo"}).json()
    [d] = [d for d in drafts if d["id"] == "undo-draft-1"]
    assert d["body"] == "Wichtiger Text"


def test_scheduled_send_keeps_draft_edited_after_scheduling(client):
    # "Später senden", dann den Entwurf weiterbearbeiten: der Versand nimmt den
    # eingefrorenen Stand, aber der NEUE Entwurf darf nicht gelöscht werden.
    client.put("/api/settings", json={"undo_seconds": 0})
    client.post("/api/send", json={
        "account": "demo", "to": ["a@b.de"], "subject": "V1", "body": "V1",
        "draft_id": "later-draft-1", "send_at": "2030-01-01T08:00:00",
    })
    client.post("/api/drafts", json={
        "id": "later-draft-1", "account": "demo", "to": ["a@b.de"],
        "subject": "V2 weiterbearbeitet", "body": "V2",
    })
    client.app.state.scheduler.process_due("2099-01-01T00:00:00")
    drafts = client.get("/api/drafts", params={"account": "demo"}).json()
    assert any(d["id"] == "later-draft-1" and d["subject"].startswith("V2") for d in drafts)


def test_snooze_from_snooze_folder_updates_job_without_move(client):
    client.post("/api/messages/demo/109/snooze", json={"folder": "INBOX", "until": "2030-01-01T08:00:00"})
    later = client.get("/api/messages", params={"account": "demo", "folder": "Später"}).json()
    [mail] = [m for m in later if m["subject"].startswith("Ihre Telekom")]
    r = client.post(f"/api/messages/demo/{mail['uid']}/snooze",
                    json={"folder": "Später", "until": "2031-01-01T08:00:00"})
    assert r.status_code == 200
    reminders = [x for x in client.get("/api/reminders", params={"account": "demo"}).json() if x["kind"] == "snooze"]
    assert len(reminders) == 1 and reminders[0]["due"].startswith("2031")


def test_followup_check_handles_timezone_offsets():
    # Antwort mit UTC-Header (12:30+00:00) NACH lokalem Versand (14:00 naive/+02:00)
    from postfach.schedule import is_later

    assert is_later("2026-07-19T12:30:00+00:00", "2026-07-19T14:00:00")
    assert not is_later("2026-07-19T11:00:00+00:00", "2026-07-19T14:00:00")
