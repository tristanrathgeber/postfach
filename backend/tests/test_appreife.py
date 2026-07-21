"""Batch 10: portable Pfade, Null-Konten-Start, Version, Netzwerk-Transparenz."""

import sys

import pytest


# --- paths.py: gebündelte Ressourcen vs. schreibbare Nutzerdaten ---


def test_paths_dev_mode_uses_repo():
    from postfach import paths

    assert paths.is_frozen() is False
    # Im Dev-Modus zeigt resource_dir aufs Repo (enthält frontend/ oder src/)
    assert (paths.resource_dir() / "frontend").exists() or (paths.resource_dir() / "backend").exists()


def test_paths_frozen_uses_meipass_and_appsupport(monkeypatch, tmp_path):
    from postfach import paths

    meipass = tmp_path / "bundle"
    meipass.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("POSTFACH_ROOT", raising=False)

    assert paths.is_frozen() is True
    assert paths.resource_dir() == meipass
    user_root = paths.user_data_root()
    assert "Application Support/Postfach" in str(user_root)
    assert user_root.exists()  # wird angelegt


def test_user_data_root_env_override(monkeypatch, tmp_path):
    from postfach import paths

    monkeypatch.setenv("POSTFACH_ROOT", str(tmp_path))
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert paths.user_data_root() == tmp_path


# --- Null-Konten-Start (frisches Binary ohne config.yaml) ---


def test_app_starts_with_zero_accounts(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    # Kein config/, kein data/ — wie ein frisch installiertes Binary.
    app = create_app(root=tmp_path, demo=False, mailbox_factory=lambda account: None)
    c = TestClient(app)
    assert c.get("/api/accounts").json() == []  # keine Konten, kein Crash
    # Onboarding funktioniert weiter (Provider-Presets da)
    assert any(p["id"] == "gmx" for p in c.get("/api/providers").json())


# --- API (Demo) ---


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    c = TestClient(create_app(root=tmp_path, demo=True))
    c.put("/api/settings", json={"undo_seconds": 0})
    return c


def test_version_no_network_by_default(client):
    v = client.get("/api/version").json()
    assert v["version"]  # eine Versionsnummer
    assert v["update_available"] is False
    assert "latest" not in v  # ohne ?check=1 KEIN Netz-Call


def test_version_check_is_opt_in(client, monkeypatch):
    from postfach import version as version_mod

    monkeypatch.setattr(version_mod, "_fetch_latest_tag", lambda: "v99.0.0")
    v = client.get("/api/version", params={"check": 1}).json()
    assert v["latest"] == "v99.0.0"
    assert v["update_available"] is True


def test_network_info_lists_only_outbound_targets(client):
    info = client.get("/api/network-info").json()
    assert "accounts" in info and "ollama" in info and "note" in info
    # Demo-Konto hat einen (Demo-)Host; nichts Unerwartetes
    assert isinstance(info["accounts"], list)


# --- Safety: keine Telemetrie ---


def test_no_telemetry_packages_imported():
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "postfach"
    forbidden = ("sentry_sdk", "posthog", "mixpanel", "segment", "google.analytics", "amplitude")
    for path in src.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pkg in forbidden:
            assert f"import {pkg}" not in content and f"from {pkg}" not in content, f"{path.name}: {pkg}"


# --- Review-Härtung (Batch-10-Review): Privatheit ehrlich + robust ---


def test_emilia_defaults_are_local():
    """Local-First: ein frisches Binary darf NICHT per Default Mail-Inhalte an
    die Cloud (Claude) schicken — beide KI-Pfade default-lokal."""
    from postfach.config import EmiliaConfig

    d = EmiliaConfig()
    assert d.sort_local is True
    assert d.draft_local is True


def test_network_info_no_cloud_when_local(client):
    """Demo/Default (lokal): kein Cloud-LLM-Ziel."""
    info = client.get("/api/network-info").json()
    assert info["cloud_llm"] is None
    # GitHub-Update-Ziel ist gelistet (nur auf Klick)
    assert any("github" in t.get("host", "").lower() for t in info["targets"])


def test_network_info_flags_cloud_when_configured(tmp_path, monkeypatch):
    """Opt-in-Cloud (draft_local=false) MUSS als ausgehendes Ziel erscheinen —
    das Transparenz-Panel darf nie lügen."""
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "config.yaml").write_text(
        "accounts:\n  - name: g\n    provider: gmail\n    address: x@gmail.com\n"
        "emilia:\n  sort_local: true\n  draft_local: false\n",
        encoding="utf-8",
    )
    c = TestClient(create_app(root=tmp_path, demo=False, mailbox_factory=lambda a: None))
    info = c.get("/api/network-info").json()
    assert info["cloud_llm"] is not None
    assert any("anthropic" in t["host"].lower() for t in info["targets"] if t.get("cloud"))


def test_network_info_dedups_by_host_and_port(client):
    info = client.get("/api/network-info").json()
    keys = [(t["host"], t["port"]) for t in info["targets"]]
    assert len(keys) == len(set(keys))  # keine Duplikate


def test_version_check_reports_unreachable(client, monkeypatch):
    """Fehlgeschlagene Prüfung darf nicht als „aktuell" durchgehen."""
    from postfach import version as version_mod

    monkeypatch.setattr(version_mod, "_fetch_latest_tag", lambda: None)
    v = client.get("/api/version", params={"check": 1}).json()
    assert v["checked"] is False  # konnte GitHub nicht erreichen
    assert v["update_available"] is False


def test_user_data_root_survives_unwritable_home(monkeypatch, tmp_path):
    """mkdir-Fehler im Binary darf den Start nicht crashen."""
    import sys

    from postfach import paths

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delenv("POSTFACH_ROOT", raising=False)

    def boom(*a, **k):
        raise PermissionError("read-only")

    monkeypatch.setattr(paths.Path, "mkdir", boom)
    # darf nicht werfen (Fallback auf ein temporäres/Home-Verzeichnis)
    root = paths.user_data_root()
    assert isinstance(root, paths.Path)
