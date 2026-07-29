"""Sicherheits-Invarianten von Postfach.

Anders als der email-agent DARF Postfach senden und in den Papierkorb
verschieben — aber ausschließlich als Folge expliziter UI-Aktionen über die
API. Die AI-Schicht bleibt davon vollständig getrennt.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from postfach.app import HOST, create_app

SRC = Path(__file__).resolve().parents[1] / "src" / "postfach"


def test_ai_layer_cannot_reach_send_or_destructive_paths():
    # Gilt für die klassische AI-Schicht UND für Emilia (Chat/Gedächtnis/Verbessern):
    # lesen und formulieren ja — senden/verschieben/löschen nie.
    # Methodenaufruf-Formen, nicht bloße Wörter — "trash" darf als Ordnername
    # in einer Skip-Liste vorkommen, ".trash(" als Aufruf nie.
    for name in ("ai.py", "emilia.py", "memory.py"):
        source = (SRC / name).read_text(encoding="utf-8")
        for token in ("mail_send", "smtplib", ".trash(", ".move(", "append_sent", "set_seen"):
            assert token not in source, f"{name} referenziert {token}"


def test_send_mail_only_called_from_api_route():
    # app.py verdrahtet den Sender lediglich in den App-State (Closure);
    # ausgelöst wird er ausschließlich von der /api/send-Route.
    for path in SRC.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        if path.name in {"api.py", "mail_send.py", "app.py"}:
            continue
        assert "send_mail(" not in content, f"{path.name} ruft send_mail auf"


def test_no_expunge_anywhere():
    for path in SRC.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert "expunge" not in content, f"{path.name} nutzt expunge"
        assert "delete_messages" not in content, f"{path.name} löscht"


def test_app_binds_localhost_only():
    assert HOST == "127.0.0.1"


# --- Schutz gegen DNS-Rebinding / fremde Webseiten -------------------------
# Nur an 127.0.0.1 zu lauschen genügt NICHT: löst eine bösartige Domain auf
# 127.0.0.1 auf, spricht der Browser die lokale API als „same origin" an —
# CORS schützt dann gar nicht. Deshalb muss der Host-Header geprüft werden.


def test_foreign_host_header_is_rejected(tmp_path):
    client = TestClient(create_app(root=tmp_path, demo=True))
    r = client.get("/api/accounts", headers={"Host": "evil.example.com"})
    assert r.status_code == 400, "fremder Host muss abgelehnt werden (DNS-Rebinding)"


def test_localhost_hosts_still_work(tmp_path):
    client = TestClient(create_app(root=tmp_path, demo=True))
    for host in ("127.0.0.1", "127.0.0.1:8722", "localhost", "localhost:8722"):
        assert client.get("/api/accounts", headers={"Host": host}).status_code == 200, host


def test_foreign_origin_is_rejected(tmp_path):
    """Eine fremde Seite darf die API auch nicht schreibend erreichen (CSRF)."""
    client = TestClient(create_app(root=tmp_path, demo=True))
    r = client.get("/api/accounts", headers={"Origin": "https://evil.example.com"})
    assert r.status_code == 403


def test_own_origin_is_allowed(tmp_path):
    client = TestClient(create_app(root=tmp_path, demo=True))
    r = client.get("/api/accounts", headers={"Origin": "http://127.0.0.1:8722"})
    assert r.status_code == 200


def test_classify_and_draft_have_no_mailbox_side_effects(tmp_path):
    app = create_app(root=tmp_path, demo=True)
    client = TestClient(app)
    box = app.state.demo_mailbox
    mutations = []
    for name in ("move", "set_seen", "trash", "append_sent"):
        original = getattr(box, name)

        def spy(*a, _n=name, _o=original, **k):
            mutations.append(_n)
            return _o(*a, **k)

        setattr(box, name, spy)

    client.post("/api/classify", json={"account": "demo", "folder": "INBOX", "uids": [112, 110]})
    client.post("/api/draft", json={"account": "demo", "folder": "INBOX", "uid": 110})
    assert mutations == []
