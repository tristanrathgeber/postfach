"""Gemeinsame Test-Infrastruktur.

Die App lehnt fremde Host-Header ab (DNS-Rebinding-Schutz, siehe
tests/test_safety.py). Starlettes TestClient schickt per Default
`Host: testserver` und liefe damit überall in ein 400. Statt in jedem
einzelnen Test eine base_url zu setzen, wird sie hier zentral auf localhost
gestellt — die Schutzschicht bleibt in Produktion unangetastet.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient


@pytest.fixture(autouse=True)
def _testclient_uses_localhost(monkeypatch):
    original_init = TestClient.__init__

    def patched_init(self, app, *args, **kwargs):
        kwargs.setdefault("base_url", "http://127.0.0.1")
        return original_init(self, app, *args, **kwargs)

    monkeypatch.setattr(TestClient, "__init__", patched_init)
