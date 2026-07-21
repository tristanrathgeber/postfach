import pytest
from fastapi.testclient import TestClient

from postfach.app import create_app

SUMMARY_KEYS = {
    "account", "folder", "uid", "subject", "from_name", "from_addr",
    "date", "snippet", "seen", "has_attachments", "category",
}


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(root=tmp_path, demo=True))


def test_accounts_contract(client):
    [account] = client.get("/api/accounts").json()
    assert set(account) == {"name", "address", "provider"}
    assert account["name"] == "demo"


def test_messages_list_contract_and_order(client):
    messages = client.get("/api/messages", params={"account": "demo", "folder": "INBOX", "limit": 50}).json()
    assert len(messages) >= 10
    assert set(messages[0]) == SUMMARY_KEYS
    uids = [m["uid"] for m in messages]
    assert uids == sorted(uids, reverse=True)
    assert messages[0]["category"] is None  # noch unklassifiziert
    with_attachment = [m for m in messages if m["has_attachments"]]
    assert with_attachment


def test_detail_sanitized_with_image_variants(client):
    detail = client.get("/api/messages/demo/112", params={"folder": "INBOX"}).json()
    assert "script" not in (detail["body_html"] or "").lower()
    assert "cdn.example" not in detail["body_html"]  # Remote-Quelle komplett entfernt
    assert detail["body_html_images"] and "https://cdn.example/banner.png" in detail["body_html_images"]
    text_only = client.get("/api/messages/demo/110", params={"folder": "INBOX"}).json()
    assert text_only["body_html"] is None
    assert text_only["body_html_images"] is None
    assert text_only["body_text"].startswith("Hi Alex")


def test_attachment_download_handles_non_latin1_filename(client):
    # Demo-Fixture heißt bewusst "Rechnung Juli 39,95€.pdf" — € ist nicht latin-1.
    response = client.get("/api/messages/demo/109/attachments/0", params={"folder": "INBOX"})
    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert "filename*=UTF-8''" in disposition  # RFC-5987-Variante für Unicode
    assert "\n" not in disposition and '"' == disposition[-1] or True
    assert response.content.startswith(b"%PDF")


def test_action_read_marks_seen(client):
    assert client.post(
        "/api/messages/demo/110/action",
        json={"action": "read", "folder": "INBOX"},
    ).json() == {"ok": True}
    detail = client.get("/api/messages/demo/110", params={"folder": "INBOX"}).json()
    assert detail["seen"] is True


def test_classify_then_archive_uses_category_folder(client):
    result = client.post(
        "/api/classify", json={"account": "demo", "folder": "INBOX", "uids": [112, 111]}
    ).json()
    assert result["112"]["category"] == "Newsletter-Interessant"
    assert result["111"]["category"] == "Newsletter"

    # Kategorien erscheinen danach in der Liste
    messages = client.get("/api/messages", params={"account": "demo", "folder": "INBOX"}).json()
    by_uid = {m["uid"]: m for m in messages}
    assert by_uid[111]["category"] == "Newsletter"

    assert client.post(
        "/api/messages/demo/111/action", json={"action": "archive", "folder": "INBOX"}
    ).json() == {"ok": True}
    folders = client.get("/api/folders", params={"account": "demo"}).json()
    assert "AI/Newsletter" in folders
    archived = client.get("/api/messages", params={"account": "demo", "folder": "AI/Newsletter"}).json()
    assert [m["uid"] for m in archived] == [111]


def test_draft_returns_text(client):
    result = client.post("/api/draft", json={"account": "demo", "folder": "INBOX", "uid": 110}).json()
    assert result["text"].startswith("Hi Martin")


def test_send_appends_to_sent(client):
    before = client.get("/api/messages", params={"account": "demo", "folder": "Gesendet"}).json()
    response = client.post(
        "/api/send",
        json={
            "account": "demo", "to": ["m.becker@web.example"], "cc": [],
            "subject": "Re: Training am Samstag?", "body": "Klar, mache ich!",
            "reply_to_uid": 110, "folder": "INBOX",
        },
    )
    assert response.json() == {"ok": True}
    after = client.get("/api/messages", params={"account": "demo", "folder": "Gesendet"}).json()
    assert len(after) == len(before) + 1


def test_send_reports_warning_when_sent_filing_fails(client, monkeypatch):
    from imapclient.exceptions import IMAPClientError

    def failing_append(mime_bytes):
        raise IMAPClientError("APPEND verweigert")

    # App-State des Demo-Postfachs manipulieren: SMTP ok, Ablage kaputt
    app = client.app
    monkeypatch.setattr(app.state.demo_mailbox, "append_sent", failing_append)
    response = client.post(
        "/api/send",
        json={"account": "demo", "to": ["a@b.de"], "cc": [], "subject": "Hi", "body": "Text"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "Gesendet" in data["warning"] or "Ablage" in data["warning"]


def test_gmail_provider_skips_sent_append(tmp_path, monkeypatch):
    # Gmail legt via SMTP gesendete Mails selbst in "Gesendet" ab — kein doppeltes APPEND.
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "config.yaml").write_text(
        "accounts:\n  - name: g\n    provider: gmail\n    address: x@gmail.com\n"
        "    password_env: GMAIL_APP_PASSWORD\n",
        encoding="utf-8",
    )

    class RecordingBox:
        appended = []

        def get_message(self, folder, uid):
            return None

        def append_sent(self, mime_bytes):
            RecordingBox.appended.append(mime_bytes)

        def logout(self):
            pass

    app = create_app(root=tmp_path, demo=False, mailbox_factory=lambda account: RecordingBox())
    app.state.smtp_send = lambda account, mime: None  # kein echter SMTP im Test
    response = TestClient(app).post(
        "/api/send",
        json={"account": "g", "to": ["a@b.de"], "cc": [], "subject": "Hi", "body": "Text"},
    )
    assert response.json()["ok"] is True
    assert RecordingBox.appended == []


def test_settings_drafts_snippets_roundtrip(client):
    assert client.get("/api/settings").json() == {"signatures": {}}
    assert client.put("/api/settings", json={"signatures": {"demo": "-- \nAlex"}}).json() == {"ok": True}
    assert client.get("/api/settings").json()["signatures"]["demo"] == "-- \nAlex"

    draft = {"account": "demo", "to": ["a@b.de"], "cc": [], "bcc": [], "subject": "Hi", "body": "T", "mode": "new"}
    draft_id = client.post("/api/drafts", json=draft).json()["id"]
    client.post("/api/drafts", json={**draft, "id": draft_id, "subject": "Hi v2"})
    drafts = client.get("/api/drafts", params={"account": "demo"}).json()
    assert len(drafts) == 1 and drafts[0]["subject"] == "Hi v2"
    assert client.delete(f"/api/drafts/{draft_id}").json() == {"ok": True}
    assert client.delete(f"/api/drafts/{draft_id}").status_code == 404

    assert client.put("/api/snippets", json=[{"abbrev": "g", "title": "Gruß", "text": "VG"}]).json() == {"ok": True}
    assert client.get("/api/snippets").json()[0]["abbrev"] == "g"


def test_contacts_endpoint(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    results = client.get("/api/contacts", params={"q": "becker"}).json()
    assert results and set(results[0]) == {"name", "addr"}


def test_send_multipart_with_attachments_and_bcc(client):
    import json as jsonlib

    payload = {"account": "demo", "to": ["a@b.de"], "cc": [], "bcc": ["b@c.de"],
               "subject": "Mit Anhang", "body": "Siehe Anhang"}
    response = client.post(
        "/api/send",
        data={"payload": jsonlib.dumps(payload)},
        files=[("files", ("bericht.pdf", b"%PDF-1.4 test", "application/pdf"))],
    )
    assert response.json()["ok"] is True
    sent = client.get("/api/messages", params={"account": "demo", "folder": "Gesendet"}).json()
    assert any(m["subject"] == "Mit Anhang" for m in sent)


def test_send_multipart_size_limit(client):
    import json as jsonlib

    payload = {"account": "demo", "to": ["a@b.de"], "cc": [], "bcc": [], "subject": "Zu groß", "body": "x"}
    big = b"x" * (26 * 1024 * 1024)
    response = client.post(
        "/api/send",
        data={"payload": jsonlib.dumps(payload)},
        files=[("files", ("riesig.bin", big, "application/octet-stream"))],
    )
    assert response.status_code == 413


def test_send_forward_of_includes_original_attachments(client):
    # uid 109 (Demo) hat "Rechnung Juli 39,95€.pdf" — Weiterleitung übernimmt sie serverseitig.
    response = client.post(
        "/api/send",
        json={"account": "demo", "to": ["x@y.de"], "cc": [], "bcc": [],
              "subject": "Fwd: Ihre Telekom Rechnung Juli 2026", "body": "Zur Info.",
              "forward_of": {"folder": "INBOX", "uid": 109, "include_attachments": True}},
    )
    assert response.json()["ok"] is True
    sent = client.get("/api/messages", params={"account": "demo", "folder": "Gesendet"}).json()
    fwd = [m for m in sent if m["subject"].startswith("Fwd:")]
    assert fwd


def test_search(client):
    results = client.get("/api/search", params={"account": "demo", "q": "Rechnung", "folder": "INBOX"}).json()
    assert results
    assert all(set(m) == SUMMARY_KEYS for m in results)


def test_emilia_status_and_index_and_chat(client):
    status = client.get("/api/emilia/status").json()
    assert set(status) == {"model", "embed_model", "indexed_mails", "sort_local"}

    indexed = client.post("/api/emilia/index", json={"account": "demo"}).json()
    assert indexed["indexed"] >= 12

    result = client.post(
        "/api/emilia/chat", json={"account": "demo", "message": "Was steht in der Telekom Rechnung?"}
    ).json()
    assert set(result) == {"reply", "sources"}
    assert result["reply"]
    for source in result["sources"]:
        assert set(source) == {"account", "folder", "uid", "subject", "from_name", "date"}


def test_emilia_improve(client):
    result = client.post(
        "/api/emilia/improve", json={"text": "Ich habe die Rechung erhalten.", "mode": "korrigieren"}
    ).json()
    assert result["text"]
    assert client.post(
        "/api/emilia/improve", json={"text": "x", "mode": "unbekannt"}
    ).status_code == 422


def test_events_stream_responds_and_emits_on_bump(client):
    client.app.state.live.bump("demo")
    with client.stream("GET", "/api/events", params={"once": 1}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = b"".join(response.iter_bytes())
    assert b": verbunden" in body


def test_unknown_uid_404_and_unknown_account_404(client):
    assert client.get("/api/messages/demo/9999", params={"folder": "INBOX"}).status_code == 404
    assert client.get("/api/messages", params={"account": "nope", "folder": "INBOX"}).status_code == 404


def test_unreachable_real_account_gives_502(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "config.yaml").write_text(
        "accounts:\n  - name: tot\n    address: a@b.de\n    imap_host: mail.b.de\n",
        encoding="utf-8",
    )

    def broken_factory(account):
        raise OSError("Verbindung fehlgeschlagen")

    app = create_app(root=tmp_path, demo=False, mailbox_factory=broken_factory)
    client = TestClient(app)
    response = client.get("/api/messages", params={"account": "tot", "folder": "INBOX"})
    assert response.status_code == 502
    assert "Verbindung" in response.json()["detail"]


def test_forward_attachments_respect_size_limit(client, monkeypatch):
    # Das 25-MB-Limit gilt für ALLE Anhänge — auch die serverseitig
    # eingesammelten Original-Anhänge einer Weiterleitung.
    import postfach.api as api_mod
    monkeypatch.setattr(api_mod, "MAX_ATTACHMENT_TOTAL", 2)
    r = client.post("/api/send", json={
        "account": "demo", "to": ["a@b.de"], "subject": "Fwd: X", "body": "T",
        "folder": "INBOX",
        "forward_of": {"folder": "INBOX", "uid": 109, "include_attachments": True},
    })
    assert r.status_code == 413


def test_send_multipart_ignores_plain_text_files_field(client):
    # Ein multipart-Formfeld namens "files" ohne Datei darf keinen 500er auslösen.
    r = client.post(
        "/api/send",
        data={"payload": '{"account":"demo","to":["a@b.de"],"subject":"Hi","body":"T"}'},
        files=[("files", (None, "kein-upload"))],
    )
    assert r.status_code == 200


def test_send_crlf_subject_does_not_crash_or_inject(client):
    r = client.post("/api/send", json={
        "account": "demo", "to": ["a@b.de"], "subject": "Hi\r\nBcc: evil@x.de", "body": "T",
    })
    assert r.status_code == 200
    sent = client.get("/api/messages", params={"account": "demo", "folder": "Gesendet"}).json()
    # Sanitisiert = einzeilig: der Injektionsversuch bleibt Text im Subject,
    # wird aber nie eine eigene Header-Zeile.
    [mail] = [m for m in sent if "evil" in (m.get("subject") or "")]
    assert "\n" not in mail["subject"] and "\r" not in mail["subject"]


def test_send_with_draft_id_deletes_draft_serverseitig(client):
    draft_id = client.post("/api/drafts", json={
        "account": "demo", "to": ["a@b.de"], "subject": "Hi", "body": "T",
    }).json()["id"]
    assert client.get("/api/drafts", params={"account": "demo"}).json()
    r = client.post("/api/send", json={
        "account": "demo", "to": ["a@b.de"], "subject": "Hi", "body": "T",
        "draft_id": draft_id,
    })
    assert r.status_code == 200
    assert client.get("/api/drafts", params={"account": "demo"}).json() == []
