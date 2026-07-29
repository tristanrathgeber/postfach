"""Live-Push muss für ALLE Konten laufen — auch für die per UI angelegten.

Regression: die Watcher-Schleife lief nur über cfg.accounts (config.yaml),
während UI-Konten erst danach dazugemischt wurden. Damit bekamen genau die
Konten, die das dokumentierte Onboarding anlegt, nie Push, nie
Benachrichtigungen und nie Auto-Indexierung neuer Mail.
"""

from __future__ import annotations

import json

import pytest

CONFIG_YAML = """\
accounts:
  - name: ausconfig
    address: a@example.org
    imap_host: imap.example.org
    smtp_host: smtp.example.org
"""


@pytest.fixture
def started(tmp_path, monkeypatch):
    """App im Echtbetrieb hochfahren, aber ohne Netz-Threads: der
    Watcher-Start wird abgefangen und nur protokolliert."""
    from postfach import app as app_mod

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "config.yaml").write_text(CONFIG_YAML, encoding="utf-8")
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "accounts.json").write_text(
        json.dumps([{
            "name": "perui", "provider": "imap", "address": "b@example.net",
            "imap_host": "imap.example.net", "imap_port": 993,
            "smtp_host": "smtp.example.net", "smtp_port": 587, "sent_folder": None,
        }]),
        encoding="utf-8",
    )

    names: list[str] = []
    monkeypatch.setattr(app_mod, "start_watcher_thread",
                        lambda name, connect, live, on_new: names.append(name))
    # Scheduler-Thread ebenfalls stilllegen — hier geht es nur um Watcher.
    monkeypatch.setattr(app_mod, "start_scheduler_thread", lambda *a, **k: None, raising=False)

    app_mod.create_app(root=tmp_path, demo=False)  # mailbox_factory=None = Echtbetrieb
    return names


def test_ui_added_account_gets_a_watcher(started):
    # Der eigentliche Regressionsfall: das per Onboarding angelegte Konto.
    assert "perui" in started


def test_config_account_still_gets_a_watcher(started):
    assert "ausconfig" in started


def test_every_account_watched_exactly_once(started):
    assert sorted(started) == ["ausconfig", "perui"]


def test_watcher_login_uses_keychain_for_managed_accounts(tmp_path, monkeypatch):
    """UI-Konten haben kein password_env — das Passwort kommt aus dem
    Schlüsselbund. Vorher las der Watcher stur os.environ und wäre mit
    leerem Passwort aufgelaufen."""
    from postfach import app as app_mod
    from postfach.config import MailAccount

    account = MailAccount(name="perui", provider="imap", address="b@example.net",
                          password_env="", imap_host="imap.example.net")

    seen: dict = {}
    monkeypatch.setattr("postfach.credentials.resolve_password", lambda acc: "geheim-aus-keychain")

    class FakeIMAP:
        def __init__(self, host, port=993, ssl=True):
            seen["host"] = host

        def login(self, address, password):
            seen["address"] = address
            seen["password"] = password

    monkeypatch.setattr("imapclient.IMAPClient", FakeIMAP)

    connect = app_mod._build_watch_connect(account)
    connect()
    assert seen["password"] == "geheim-aus-keychain"
    assert seen["address"] == "b@example.net"
