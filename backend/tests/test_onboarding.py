"""Batch 9: Provider-Presets, Konto-Einrichtung (Schlüsselbund), Ordner-Mapping."""

import pytest


# --- Provider-Presets ---


def test_providers_include_german_and_custom():
    from postfach.providers import PRESETS, preset_list

    ids = {p["id"] for p in preset_list()}
    assert {"gmx", "web.de", "t-online", "posteo", "mailbox.org", "gmail", "custom"} <= ids
    gmx = PRESETS["gmx"]
    assert gmx["imap_host"] == "imap.gmx.net"
    assert gmx["smtp_host"] == "mail.gmx.net"  # SMTP-Host ≠ IMAP-Host bei GMX!


# --- Passwort-Auflösung (Env → Schlüsselbund) ---


def test_resolve_password_prefers_env(monkeypatch):
    from postfach.config import MailAccount
    from postfach.credentials import resolve_password

    monkeypatch.setenv("MY_ENV_PW", "aus-env")
    acc = MailAccount(name="k", provider="imap", address="a@x.de", password_env="MY_ENV_PW")
    assert resolve_password(acc) == "aus-env"


def test_resolve_password_falls_back_to_keychain(monkeypatch):
    from postfach import credentials
    from postfach.config import MailAccount

    store: dict = {}
    monkeypatch.setattr(credentials, "_kr_get", lambda name: store.get(name))
    monkeypatch.setattr(credentials, "_kr_set", lambda name, pw: store.__setitem__(name, pw))
    monkeypatch.setattr(credentials, "_kr_delete", lambda name: store.pop(name, None))

    acc = MailAccount(name="neu", provider="imap", address="a@x.de", password_env="")
    assert credentials.resolve_password(acc) == ""  # noch nichts gesetzt → leer
    credentials.set_password("neu", "geheim")
    assert credentials.resolve_password(acc) == "geheim"
    credentials.delete_password("neu")
    assert credentials.resolve_password(acc) == ""


# --- Verwaltete Konten (accounts.json) ---


def test_account_store_roundtrip(tmp_path):
    from postfach.accounts_store import AccountStore

    store = AccountStore(tmp_path / "accounts.json")
    store.add({
        "name": "gmxneu", "provider": "imap", "address": "neu@gmx.de",
        "imap_host": "imap.gmx.net", "imap_port": 993,
        "smtp_host": "mail.gmx.net", "smtp_port": 587,
    })
    accounts = store.list()
    assert accounts[0]["name"] == "gmxneu"
    # Persistenz
    assert AccountStore(tmp_path / "accounts.json").list()[0]["address"] == "neu@gmx.de"
    store.remove("gmxneu")
    assert store.list() == []


# --- API (Demo) ---


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from postfach import credentials
    from postfach.app import create_app

    # Schlüsselbund im Test isolieren (kein echter macOS-Zugriff)
    store: dict = {}
    monkeypatch.setattr(credentials, "_kr_get", lambda name: store.get(name))
    monkeypatch.setattr(credentials, "_kr_set", lambda name, pw: store.__setitem__(name, pw))
    monkeypatch.setattr(credentials, "_kr_delete", lambda name: store.pop(name, None))

    c = TestClient(create_app(root=tmp_path, demo=True))
    c.put("/api/settings", json={"undo_seconds": 0})
    c._keychain = store
    return c


def test_providers_route(client):
    presets = client.get("/api/providers").json()
    assert any(p["id"] == "gmx" for p in presets)


def test_account_test_in_demo_is_skipped(client):
    r = client.post("/api/accounts/test", json={
        "provider": "imap", "address": "a@gmx.de", "imap_host": "imap.gmx.net",
        "imap_port": 993, "smtp_host": "mail.gmx.net", "smtp_port": 587, "password": "x",
    })
    assert r.json()["ok"] is True and r.json().get("demo") is True


def test_add_account_stores_password_in_keychain_not_plaintext(tmp_path, monkeypatch):
    """Echtbetrieb: Passwort landet im Schlüsselbund, NIE im accounts.json."""
    from fastapi.testclient import TestClient

    from postfach import credentials
    from postfach.app import create_app

    store: dict = {}
    monkeypatch.setattr(credentials, "_kr_get", lambda name: store.get(name))
    monkeypatch.setattr(credentials, "_kr_set", lambda name, pw: store.__setitem__(name, pw))
    monkeypatch.setattr(credentials, "_kr_delete", lambda name: store.pop(name, None))

    c = TestClient(create_app(root=tmp_path, demo=False, mailbox_factory=lambda account: None))
    c.put("/api/settings", json={"undo_seconds": 0})
    r = c.post("/api/accounts", json={
        "name": "gmxprivat", "provider": "imap", "address": "privat@gmx.de",
        "imap_host": "imap.gmx.net", "imap_port": 993,
        "smtp_host": "mail.gmx.net", "smtp_port": 587, "password": "streng-geheim",
    })
    assert r.status_code == 200 and r.json()["ok"] is True
    # Passwort im Schlüsselbund, NICHT im accounts.json (Echtbetrieb → data/)
    assert store.get("gmxprivat") == "streng-geheim"
    accounts_json = (tmp_path / "data" / "accounts.json").read_text(encoding="utf-8")
    assert "streng-geheim" not in accounts_json
    entry = next(a for a in c.get("/api/accounts").json() if a["name"] == "gmxprivat")
    assert entry["managed"] is True


def test_add_account_rejects_duplicate_name(client):
    body = {
        "name": "demo", "provider": "imap", "address": "x@gmx.de",
        "imap_host": "imap.gmx.net", "imap_port": 993,
        "smtp_host": "mail.gmx.net", "smtp_port": 587, "password": "x",
    }
    assert client.post("/api/accounts", json=body).status_code == 409


def test_delete_managed_account(client):
    client.post("/api/accounts", json={
        "name": "weg", "provider": "imap", "address": "weg@gmx.de",
        "imap_host": "imap.gmx.net", "imap_port": 993,
        "smtp_host": "mail.gmx.net", "smtp_port": 587, "password": "x",
    })
    assert client.delete("/api/accounts/weg").status_code == 200
    assert client._keychain.get("weg") is None
    assert all(a["name"] != "weg" for a in client.get("/api/accounts").json())


def test_delete_config_account_is_protected(client):
    # Das Demo-Konto stammt nicht aus accounts.json → schreibgeschützt
    assert client.delete("/api/accounts/demo").status_code == 409


# --- Ordner-Mapping ---


def test_folder_map_roundtrip_and_applies(client):
    got = client.get("/api/folder-map", params={"account": "demo"}).json()
    assert "categories" in got and "folders" in got
    client.put("/api/folder-map", json={"mapping": {"Werbung": "INBOX/Werbung"}})
    assert client.get("/api/folder-map", params={"account": "demo"}).json()["mapping"]["Werbung"] == "INBOX/Werbung"
    # Overlay überstimmt agent_config.folder_for
    assert client.app.state.folder_map.folder_for("Werbung") == "INBOX/Werbung"
    assert client.app.state.folder_map.folder_for("Unbekannt") is None  # kein Overlay → Fallback


# --- Review-Härtung (Batch-9-Review) ---


def test_validation_error_never_echoes_password(client):
    """FastAPI-422 spiegelt sonst den ganzen Body inkl. Klartext-Passwort."""
    r = client.post("/api/accounts", json={
        # name fehlt → Validierungsfehler; Passwort darf nicht zurückkommen
        "provider": "imap", "address": "a@gmx.de", "imap_host": "imap.gmx.net",
        "imap_port": 993, "smtp_host": "mail.gmx.net", "smtp_port": 587,
        "password": "SUPER-SECRET-PW-12345",
    })
    assert r.status_code == 422
    assert "SUPER-SECRET-PW-12345" not in r.text


def test_delete_protects_config_account_even_if_store_shadows_it(client, tmp_path):
    """Ein config/live-Konto darf nie über einen gleichnamigen accounts.json-
    Eintrag löschbar sein (409), sonst verschwindet es + sein Keychain-Secret."""
    # Store-Schatten für "demo" (Live-Konto stammt NICHT aus dem Store)
    client.app.state.accounts_store.add({
        "name": "demo", "provider": "imap", "address": "x@demo.example",
        "imap_host": "imap.x", "imap_port": 993, "smtp_host": "smtp.x", "smtp_port": 587,
    })
    client._keychain["demo"] = "sollte-bleiben"
    r = client.delete("/api/accounts/demo")
    assert r.status_code == 409
    assert "demo" in client.app.state.accounts  # Live-Konto unangetastet
    assert client._keychain.get("demo") == "sollte-bleiben"  # Secret unangetastet


def test_resolve_password_no_keychain_fallback_when_env_declared(monkeypatch):
    """Ist password_env deklariert (config-Konto), darf eine LEERE Env-Var nicht
    still ein gleichnamiges Keychain-Secret ziehen."""
    from postfach import credentials
    from postfach.config import MailAccount

    store = {"gmx": "MANAGED-secret"}
    monkeypatch.setattr(credentials, "_kr_get", lambda name: store.get(name))
    monkeypatch.delenv("GMX_PW", raising=False)  # Env unset
    acc = MailAccount(name="gmx", provider="imap", address="a@gmx.de", password_env="GMX_PW")
    assert credentials.resolve_password(acc) == ""  # KEIN Keychain-Fallback
    # Konto ohne password_env (verwaltet) nutzt weiter den Keychain
    managed = MailAccount(name="gmx", provider="imap", address="a@gmx.de", password_env="")
    assert credentials.resolve_password(managed) == "MANAGED-secret"


def test_add_account_in_demo_never_touches_real_keychain(client):
    """Demo-Modus darf NIE den echten Schlüsselbund beschreiben (öffentliche
    Demo). Das Test-Keychain (client._keychain) ist die echte keyring-Ebene —
    im Demo darf set_password sie nicht anfassen."""
    r = client.post("/api/accounts", json={
        "name": "demoadd", "provider": "imap", "address": "d@gmx.de",
        "imap_host": "imap.gmx.net", "imap_port": 993,
        "smtp_host": "mail.gmx.net", "smtp_port": 587, "password": "sollte-nicht-persistieren",
    })
    assert r.status_code == 200
    assert "demoadd" not in client._keychain  # Schlüsselbund UNBERÜHRT im Demo
    # In der Liste erscheint es trotzdem (Demo-Store isoliert)
    assert any(a["name"] == "demoadd" for a in client.get("/api/accounts").json())
