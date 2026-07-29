"""Eine gesendete Mail darf NIE ein zweites Mal rausgehen.

Der Versand läuft (wegen Undo-Send) über die Zeit-Warteschlange: der Scheduler
reiht einen Job bei jeder Ausnahme erneut ein. Schlug also irgendein Schritt
NACH dem erfolgreichen SMTP-Versand fehl — Entwurf löschen, Wiedervorlage
anlegen, Ablage im Gesendet-Ordner, oder schon das `logout` beim Verlassen der
IMAP-Verbindung — bekam der Empfänger die Mail bis zu dreimal.
"""

from __future__ import annotations

import pytest

CONFIG = (
    "accounts:\n  - name: k\n    provider: imap\n    address: x@example.org\n"
    "    imap_host: imap.example.org\n    password_env: K_PW\n"
)


def _app(tmp_path, box):
    from postfach.app import create_app

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    app = create_app(root=tmp_path, demo=False, mailbox_factory=lambda account: box)
    return app


class Box:
    """Minimales Mailbox-Double; einzelne Schritte können gezielt scheitern."""

    def __init__(self, fail_on: str | None = None):
        self.fail_on = fail_on
        self.appended: list[bytes] = []

    def get_message(self, folder, uid):
        return None

    def append_sent(self, mime_bytes):
        if self.fail_on == "append_sent":
            raise OSError("Ablage kaputt")
        self.appended.append(mime_bytes)

    def logout(self):
        if self.fail_on == "logout":
            raise OSError("Verbindung weg")


def _send(app, **extra):
    from postfach.api import SendBody, perform_send

    body = SendBody(account="k", to=["a@b.de"], cc=[], subject="Hi", body="Text", **extra)
    return perform_send(app.state, body, [])


@pytest.mark.parametrize("failing_step", ["append_sent", "logout"])
def test_post_transport_failure_does_not_raise(tmp_path, failing_step):
    """Nach erfolgreichem SMTP darf keine Ausnahme mehr nach oben — sonst
    reiht der Scheduler den Job neu ein und die Mail geht doppelt raus."""
    box = Box(fail_on=failing_step)
    app = _app(tmp_path, box)
    sent: list[bytes] = []
    app.state.smtp_send = lambda account, mime: sent.append(mime)

    result = _send(app)

    assert len(sent) == 1, "genau ein SMTP-Versand"
    assert result["ok"] is True
    assert "warning" in result, "der Nutzer soll erfahren, dass die Nacharbeit hakte"


def test_transport_failure_still_raises(tmp_path):
    """Scheitert der Versand selbst, MUSS die Ausnahme durch — nur dann darf
    der Scheduler es erneut versuchen."""
    app = _app(tmp_path, Box())

    def boom(account, mime):
        raise OSError("SMTP unerreichbar")

    app.state.smtp_send = boom
    with pytest.raises(OSError):
        _send(app)


def test_retry_endpoint_rearms_a_failed_send(tmp_path):
    """POST /outbox/{id}/retry stellt einen gescheiterten Versand zurück in die
    Schlange; unbekannte Kennungen sind ehrlich 404."""
    from starlette.testclient import TestClient

    app = _app(tmp_path, Box())
    client = TestClient(app)
    job_id = app.state.schedule.add("send_failed", "k", due="2026-07-21T09:00:00",
                                    payload={"subject": "Hi", "to": ["a@b.de"]})

    assert client.post("/api/outbox/gibtsnicht/retry").status_code == 404
    assert client.post(f"/api/outbox/{job_id}/retry").status_code == 200
    assert app.state.schedule.list("k")[0]["kind"] == "send"


def test_draft_is_deleted_even_if_later_step_fails(tmp_path):
    """Die Mail ist raus — der Entwurf muss weg, auch wenn die Ablage scheitert."""
    box = Box(fail_on="append_sent")
    app = _app(tmp_path, box)
    app.state.smtp_send = lambda account, mime: None
    draft_id = app.state.drafts.upsert({"account": "k", "to": ["a@b.de"], "subject": "Hi", "body": "T"})

    _send(app, draft_id=draft_id)

    assert all(d["id"] != draft_id for d in app.state.drafts.list("k"))
