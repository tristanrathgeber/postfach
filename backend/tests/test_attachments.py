"""Anhänge: sichere Inline-Vorschau + zuverlässiger Download (Speichern).

Kernpunkte: nur ungefährliche Typen dürfen inline (kein HTML/SVG-XSS auf dem
App-Origin), Dateinamen sind gegen Path-Traversal gehärtet, und „Speichern"
legt ohne Überschreiben in Downloads ab.
"""

from __future__ import annotations

from pathlib import Path

from postfach import attach


class TestInlineSafe:
    def test_images_pdf_and_text_are_inline_safe(self):
        for ct in ["image/png", "image/jpeg", "image/webp", "application/pdf", "text/plain", "text/csv"]:
            assert attach.inline_safe(ct) is True, ct

    def test_html_svg_and_xml_are_never_inline(self):
        # Würden sonst als App-Origin-Dokument Skripte ausführen können.
        for ct in ["text/html", "image/svg+xml", "application/xhtml+xml", "text/xml", "application/xml"]:
            assert attach.inline_safe(ct) is False, ct

    def test_unknown_and_binary_types_are_not_inline(self):
        for ct in ["application/octet-stream", "application/zip", "", None]:
            assert attach.inline_safe(ct) is False, ct

    def test_content_type_parameters_are_ignored(self):
        assert attach.inline_safe("text/plain; charset=utf-8") is True
        assert attach.inline_safe("TEXT/HTML; charset=utf-8") is False


class TestSanitizeFilename:
    def test_strips_path_components(self):
        assert attach.sanitize_filename("../../etc/passwd") == "passwd"
        assert attach.sanitize_filename("/abs/evil.pdf") == "evil.pdf"
        assert attach.sanitize_filename("sub\\dir\\x.png") == "x.png"

    def test_removes_control_and_leading_dots(self):
        assert attach.sanitize_filename(".hidden") == "hidden"
        assert attach.sanitize_filename("a\x00b.txt") == "ab.txt"
        assert attach.sanitize_filename("...") == "anhang"

    def test_empty_becomes_fallback(self):
        assert attach.sanitize_filename("") == "anhang"
        assert attach.sanitize_filename("   ") == "anhang"

    def test_keeps_unicode_and_extension(self):
        assert attach.sanitize_filename("Rechnung Jülü.pdf") == "Rechnung Jülü.pdf"


class TestUniquePath:
    def test_returns_name_when_free(self, tmp_path: Path):
        assert attach.unique_path(tmp_path, "a.pdf") == tmp_path / "a.pdf"

    def test_inserts_counter_before_extension(self, tmp_path: Path):
        (tmp_path / "a.pdf").write_bytes(b"x")
        assert attach.unique_path(tmp_path, "a.pdf") == tmp_path / "a (1).pdf"
        (tmp_path / "a (1).pdf").write_bytes(b"x")
        assert attach.unique_path(tmp_path, "a.pdf") == tmp_path / "a (2).pdf"

    def test_handles_extensionless(self, tmp_path: Path):
        (tmp_path / "README").write_bytes(b"x")
        assert attach.unique_path(tmp_path, "README") == tmp_path / "README (1)"


class TestSaveBytes:
    def test_writes_and_returns_path(self, tmp_path: Path):
        p = attach.save_bytes_to_dir(tmp_path, "beleg.pdf", b"%PDF-1.4")
        assert p == tmp_path / "beleg.pdf"
        assert p.read_bytes() == b"%PDF-1.4"

    def test_traversal_name_stays_inside_dir(self, tmp_path: Path):
        p = attach.save_bytes_to_dir(tmp_path, "../../oops.txt", b"hi")
        assert p.parent == tmp_path
        assert p.name == "oops.txt"

    def test_does_not_overwrite(self, tmp_path: Path):
        first = attach.save_bytes_to_dir(tmp_path, "x.txt", b"1")
        second = attach.save_bytes_to_dir(tmp_path, "x.txt", b"2")
        assert first != second
        assert first.read_bytes() == b"1"
        assert second.read_bytes() == b"2"


# --- API-Endpunkte (Demo hat an uid 109 eine PDF (0) + ein PNG (1)) ----------

_A = "/api/messages/demo/109/attachments"


def _client(tmp_path):
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    return TestClient(create_app(root=tmp_path, demo=True))


def test_attachment_default_is_download(tmp_path):
    r = _client(tmp_path).get(f"{_A}/0?folder=INBOX")
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith("attachment;")


def test_attachment_inline_pdf_renders_inline(tmp_path):
    r = _client(tmp_path).get(f"{_A}/0?folder=INBOX&inline=1")
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith("inline;")
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.content[:4] == b"%PDF"


def test_attachment_inline_png_ok(tmp_path):
    r = _client(tmp_path).get(f"{_A}/1?folder=INBOX&inline=1")
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith("inline;")
    assert r.headers["content-type"].startswith("image/png")


def test_save_writes_to_downloads_dir(tmp_path, monkeypatch):
    from postfach import api

    downloads = tmp_path / "Downloads"
    monkeypatch.setattr(api, "_downloads_dir", lambda: downloads)
    r = _client(tmp_path).post(f"{_A}/0/save?folder=INBOX")
    assert r.status_code == 200
    body = r.json()
    saved = Path(body["path"])
    assert saved.parent == downloads
    assert saved.exists() and saved.read_bytes()[:4] == b"%PDF"
    assert body["filename"] == saved.name


def test_save_missing_attachment_is_404(tmp_path, monkeypatch):
    from postfach import api

    monkeypatch.setattr(api, "_downloads_dir", lambda: tmp_path / "Downloads")
    r = _client(tmp_path).post(f"{_A}/9/save?folder=INBOX")
    assert r.status_code == 404
