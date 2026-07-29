"""Protokoll-Datei und Diagnose.

Das gebündelte Programm hat kein Konsolenfenster — ohne Logdatei verschwindet
jeder Fehler spurlos und Beta-Bugreports sind nicht nachvollziehbar.
"""

from __future__ import annotations

import logging

from starlette.testclient import TestClient

from postfach.app import create_app
from postfach.logsetup import log_path, setup_logging


def test_setup_logging_writes_to_root(tmp_path):
    path = setup_logging(tmp_path)
    assert path == log_path(tmp_path)
    logging.getLogger("postfach.test").error("Testfehler mit Ümlaut")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert path.exists()
    assert "Testfehler mit Ümlaut" in path.read_text(encoding="utf-8")


def test_setup_logging_is_idempotent(tmp_path):
    before = len(logging.getLogger().handlers)
    setup_logging(tmp_path)
    setup_logging(tmp_path)
    added = len(logging.getLogger().handlers) - before
    assert added <= 1, "kein doppelter Handler bei mehrfachem Aufruf"


def test_setup_logging_survives_unwritable_root(tmp_path, monkeypatch):
    """Ein nicht schreibbares Verzeichnis darf den Start NIE verhindern."""

    def boom(*args, **kwargs):
        raise OSError("read-only")

    monkeypatch.setattr("pathlib.Path.mkdir", boom)
    assert setup_logging(tmp_path / "geht-nicht") is None


def test_diagnostics_endpoint_helps_bug_reports(tmp_path):
    client = TestClient(create_app(root=tmp_path, demo=True))
    data = client.get("/api/diagnostics").json()
    for key in ("version", "os", "arch", "data_root", "log_file", "accounts",
                "emilia_model", "embed_model", "indexed_mails"):
        assert key in data, key
    assert data["demo"] is True


def test_diagnostics_leaks_no_mail_content(tmp_path):
    """Die Diagnose darf niemals Mail-Inhalte oder Zugangsdaten enthalten."""
    client = TestClient(create_app(root=tmp_path, demo=True))
    raw = client.get("/api/diagnostics").text.lower()
    for forbidden in ("password", "passwort", "betreff", "subject", "body", "snippet", "token"):
        assert forbidden not in raw, forbidden
