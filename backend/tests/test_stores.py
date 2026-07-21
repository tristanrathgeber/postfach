"""Lokale Stores: Einstellungen (Signaturen), Entwürfe (Upsert), Snippets."""

from postfach.stores import DraftStore, SettingsStore, SnippetStore


def test_settings_roundtrip_and_default(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    assert store.get() == {"signatures": {}}
    store.put({"signatures": {"gmx": "Viele Grüße\nTristan"}})
    assert store.get()["signatures"]["gmx"].startswith("Viele Grüße")


def test_draft_create_upsert_list_delete(tmp_path):
    store = DraftStore(tmp_path / "drafts.json")
    draft_id = store.upsert({
        "account": "gmx", "to": ["a@b.de"], "cc": [], "bcc": [],
        "subject": "Hi", "body": "Text", "mode": "new",
    })
    assert draft_id
    # Upsert mit id ändert statt zu duplizieren (Auto-Save)
    store.upsert({"id": draft_id, "account": "gmx", "to": ["a@b.de"], "cc": [], "bcc": [],
                  "subject": "Hi v2", "body": "Mehr Text", "mode": "new"})
    drafts = store.list("gmx")
    assert len(drafts) == 1
    assert drafts[0]["subject"] == "Hi v2"
    assert drafts[0]["updated"]  # ISO-Zeitstempel
    assert store.delete(draft_id) is True
    assert store.list("gmx") == []
    assert store.delete("gibtsnicht") is False


def test_drafts_scoped_per_account(tmp_path):
    store = DraftStore(tmp_path / "drafts.json")
    store.upsert({"account": "a", "to": [], "cc": [], "bcc": [], "subject": "x", "body": "", "mode": "new"})
    assert store.list("b") == []


def test_snippets_roundtrip(tmp_path):
    store = SnippetStore(tmp_path / "snippets.json")
    assert store.get() == []
    store.put([{"abbrev": "gruss", "title": "Grußformel", "text": "Viele Grüße\n{vorname}"}])
    [snippet] = store.get()
    assert snippet["abbrev"] == "gruss"


def test_demo_stores_isoliert_vom_echtbetrieb(tmp_path):
    """Demo und Echtbetrieb teilen data/ — Demo-Testdaten (Signaturen,
    Entwürfe, Snippets) dürfen die echten Store-Dateien nie berühren."""
    from postfach.app import create_app

    demo = create_app(root=tmp_path, demo=True)
    real = create_app(root=tmp_path, demo=False, mailbox_factory=lambda a: None)
    for name in ("settings", "drafts", "snippets"):
        demo_path = getattr(demo.state, name)._path
        real_path = getattr(real.state, name)._path
        assert demo_path != real_path
        assert "demo" in str(demo_path.parent)


def test_corrupt_store_file_returns_default_and_backs_up(tmp_path):
    path = tmp_path / "drafts.json"
    path.write_text("{kaputt", encoding="utf-8")
    store = DraftStore(path)
    assert store.list("gmx") == []  # Default statt 500
    assert path.with_suffix(".json.broken").exists()  # nichts still verwerfen


def test_draft_upsert_preserves_extra_fields(tmp_path):
    # Neue Draft-Felder (z. B. include_attachments) dürfen nicht still
    # verschluckt werden — der Store persistiert das validierte Modell 1:1.
    store = DraftStore(tmp_path / "drafts.json")
    store.upsert({"account": "gmx", "to": [], "cc": [], "bcc": [], "subject": "x",
                  "body": "", "mode": "forward", "include_attachments": False})
    [draft] = store.list("gmx")
    assert draft["include_attachments"] is False
