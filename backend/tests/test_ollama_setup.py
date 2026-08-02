"""Ollama selbst einrichten — Auswahl, Prüfsumme, sicheres Entpacken.

Sicherheitskern: Postfach lädt hier ein Archiv aus dem Netz und führt daraus
ein Programm aus. Ohne verifizierte Prüfsumme und ohne Schutz gegen
Pfad-Ausbrüche wäre das ein Einfallstor.
"""

from __future__ import annotations

import io
import json
import re
import tarfile

import pytest

from postfach import ollama_setup as os_mod
from postfach.ollama_setup import OllamaSetupError


def _release(name="ollama-darwin.tgz", digest="sha256:" + "a" * 64, url="https://example.org/o.tgz"):
    return {"tag_name": "v9.9.9", "assets": [
        {"name": "Ollama.dmg", "browser_download_url": "https://example.org/x.dmg", "digest": "sha256:" + "b" * 64},
        {"name": name, "browser_download_url": url, "digest": digest},
    ]}


class TestPickAsset:
    def test_picks_the_darwin_archive_with_version_and_checksum(self):
        version, url, sha = os_mod.pick_asset(_release())
        assert version == "9.9.9"
        assert url == "https://example.org/o.tgz"
        assert sha == "a" * 64  # ohne „sha256:"-Präfix

    def test_missing_asset_is_an_error(self):
        with pytest.raises(OllamaSetupError, match=re.escape("ollama-darwin.tgz")):
            os_mod.pick_asset(_release(name="ollama-linux.tgz"))

    def test_refuses_when_github_gives_no_checksum(self):
        """Ohne Prüfsumme wird NICHTS ausgeführt — lieber abbrechen."""
        with pytest.raises(OllamaSetupError, match="Prüfsumme"):
            os_mod.pick_asset(_release(digest=""))

    def test_refuses_a_non_sha256_digest(self):
        with pytest.raises(OllamaSetupError, match="Prüfsumme"):
            os_mod.pick_asset(_release(digest="md5:" + "c" * 32))


class TestChecksum:
    def test_sha256_matches_reference(self, tmp_path):
        import hashlib

        blob = b"Postfach" * 1000
        path = tmp_path / "f.bin"
        path.write_bytes(blob)
        assert os_mod.sha256_of(path) == hashlib.sha256(blob).hexdigest()


def _tar_with(tmp_path, entries: dict[str, bytes], *, symlink: tuple[str, str] | None = None):
    """Baut ein Test-Archiv; entries: Name → Inhalt."""
    archive = tmp_path / "test.tgz"
    with tarfile.open(archive, "w:gz") as tar:
        for name, content in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        if symlink:
            link_name, target = symlink
            info = tarfile.TarInfo(link_name)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            tar.addfile(info)
    return archive


class TestSafeExtraction:
    def test_normal_archive_extracts(self, tmp_path):
        archive = _tar_with(tmp_path, {"ollama": b"#!/bin/sh\n", "libggml.so": b"x"})
        dest = tmp_path / "out"
        os_mod.extract_archive(archive, dest)
        assert (dest / "ollama").read_bytes() == b"#!/bin/sh\n"
        assert (dest / "libggml.so").exists()

    def test_parent_traversal_is_refused(self, tmp_path):
        archive = _tar_with(tmp_path, {"../boese.txt": b"pwn"})
        dest = tmp_path / "out"
        with pytest.raises(OllamaSetupError, match="nicht sicher"):
            os_mod.extract_archive(archive, dest)
        assert not (tmp_path / "boese.txt").exists(), "nichts außerhalb des Ziels geschrieben"

    def test_absolute_path_is_refused(self, tmp_path):
        archive = _tar_with(tmp_path, {"/tmp/boese.txt": b"pwn"})
        dest = tmp_path / "out"
        with pytest.raises(OllamaSetupError, match="nicht sicher"):
            os_mod.extract_archive(archive, dest)

    def test_symlink_out_of_tree_is_refused(self, tmp_path):
        """Ein Symlink auf eine Systemdatei würde diese überschreibbar machen."""
        archive = _tar_with(tmp_path, {"ollama": b"x"}, symlink=("link", "/etc/hosts"))
        dest = tmp_path / "out"
        with pytest.raises(OllamaSetupError, match="nicht sicher"):
            os_mod.extract_archive(archive, dest)

    def test_relative_symlink_escaping_the_tree_is_refused(self, tmp_path):
        archive = _tar_with(tmp_path, {"ollama": b"x"}, symlink=("link", "../../draußen"))
        dest = tmp_path / "out"
        with pytest.raises(OllamaSetupError, match="nicht sicher"):
            os_mod.extract_archive(archive, dest)

    def test_internal_symlink_is_allowed(self, tmp_path):
        """Versionierte Bibliotheken (libfoo.dylib → libfoo.1.dylib) sind auf
        macOS normal und stecken auch in Ollamas Archiv — ein pauschales Verbot
        machte das Einrichten unmöglich (real aufgefallen)."""
        archive = _tar_with(
            tmp_path,
            {"ollama": b"x", "libggml-base.0.0.1.dylib": b"lib"},
            symlink=("libggml-base.0.dylib", "libggml-base.0.0.1.dylib"),
        )
        dest = tmp_path / "out"
        os_mod.extract_archive(archive, dest)
        link = dest / "libggml-base.0.dylib"
        assert link.is_symlink()
        assert link.resolve() == (dest / "libggml-base.0.0.1.dylib").resolve()


class TestPathsAndState:
    def test_not_installed_on_a_fresh_root(self, tmp_path):
        assert os_mod.is_installed(tmp_path) is False

    def test_installed_requires_an_executable_binary(self, tmp_path):
        binary = os_mod.ollama_binary(tmp_path)
        binary.parent.mkdir(parents=True)
        binary.write_text("#!/bin/sh\n")
        assert os_mod.is_installed(tmp_path) is False, "nicht ausführbar → nicht einsatzbereit"
        binary.chmod(0o755)
        assert os_mod.is_installed(tmp_path) is True

    def test_start_server_without_installation_returns_none(self, tmp_path):
        assert os_mod.start_server(tmp_path, "http://127.0.0.1:11434") is None

    def test_start_server_skips_when_one_already_runs(self, tmp_path, monkeypatch):
        """Kein zweiter Server — der Port wäre belegt und würde scheitern."""
        binary = os_mod.ollama_binary(tmp_path)
        binary.parent.mkdir(parents=True)
        binary.write_text("#!/bin/sh\n")
        binary.chmod(0o755)
        monkeypatch.setattr(os_mod, "server_reachable", lambda url, timeout=1.5: True)
        called = []
        monkeypatch.setattr(os_mod.subprocess, "Popen", lambda *a, **k: called.append(a))
        assert os_mod.start_server(tmp_path, "http://127.0.0.1:11434") is None
        assert called == []


class TestInstallGuards:
    def test_checksum_mismatch_aborts_and_keeps_old_installation(self, tmp_path, monkeypatch):
        """Stimmt die Summe nicht, wird nichts ersetzt — eine vorhandene,
        funktionierende Installation bleibt unangetastet."""
        # Vorhandene "Installation"
        old = os_mod.ollama_binary(tmp_path)
        old.parent.mkdir(parents=True)
        old.write_text("alt")

        monkeypatch.setattr(os_mod, "latest_release", lambda: _release())

        class FakeStream:
            def __init__(self, *a, **k):
                self.headers = {"content-length": "4"}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def raise_for_status(self):
                pass

            def iter_bytes(self, size):
                yield b"MUEL"

        monkeypatch.setattr(os_mod.httpx, "stream", lambda *a, **k: FakeStream())
        with pytest.raises(OllamaSetupError, match="Prüfsumme"):
            os_mod.install(tmp_path)
        assert old.read_text() == "alt", "alte Installation überlebt einen fehlgeschlagenen Versuch"


class TestInstallRoute:
    """Der Zusammenbau in api.py (POST /ollama/install) — die Bausteine oben sind
    einzeln getestet, hier der ganze Ablauf: Demo-Sperre, NDJSON-Fortschritt,
    Erfolgs- und Fehlerfall."""

    def _client(self, tmp_path):
        from fastapi.testclient import TestClient

        from postfach.app import create_app

        return TestClient(create_app(root=tmp_path, demo=False, mailbox_factory=lambda a: None))

    def test_blocked_in_demo(self, tmp_path):
        from fastapi.testclient import TestClient

        from postfach.app import create_app

        c = TestClient(create_app(root=tmp_path, demo=True))
        assert c.post("/api/ollama/install").status_code == 403

    def test_streams_progress_and_reports_reachable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            os_mod, "install",
            lambda root, progress=None: progress(50, 100, "lädt herunter"),
        )
        monkeypatch.setattr(os_mod, "start_server", lambda root, base_url: None)
        monkeypatch.setattr(os_mod, "server_reachable", lambda base_url, timeout=1.5: True)

        with self._client(tmp_path).stream("POST", "/api/ollama/install") as r:
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("application/x-ndjson")
            events = [json.loads(line) for line in r.iter_lines() if line]

        assert {"done": 50, "total": 100, "status": "lädt herunter"} in events
        assert events[-1] == {"done_all": True, "reachable": True}

    def test_setup_error_lands_as_event_not_a_crash(self, tmp_path, monkeypatch):
        """Ein Download- oder Prüfsummenfehler beendet den Stream mit einer
        Fehlermeldung — der Hintergrund-Thread darf die App nicht mitreißen."""

        def _boom(root, progress=None):
            raise OllamaSetupError("Prüfsumme stimmt nicht")

        monkeypatch.setattr(os_mod, "install", _boom)

        with self._client(tmp_path).stream("POST", "/api/ollama/install") as r:
            assert r.status_code == 200
            events = [json.loads(line) for line in r.iter_lines() if line]

        assert events == [{"error": "Prüfsumme stimmt nicht"}]
