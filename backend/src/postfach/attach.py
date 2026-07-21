"""Anhang-Helfer: sichere Inline-Vorschau + Speichern in Downloads.

Sicherheitsleitplanke: NUR ungefährliche Typen dürfen inline ausgeliefert
werden. HTML/SVG/XML liefen sonst als Dokument auf dem App-Origin
(127.0.0.1) und könnten Skripte gegen die eigene API ausführen — die werden
als Download (octet-stream) behandelt, nie inline.
"""

from __future__ import annotations

import re
from pathlib import Path

# Typen, die im Browser Skripte ausführen könnten → niemals inline.
_DANGEROUS = {
    "text/html",
    "application/xhtml+xml",
    "image/svg+xml",
    "text/xml",
    "application/xml",
    "text/xsl",
}
_INLINE_TEXT = {"text/plain", "text/csv"}


def _bare_type(content_type: str | None) -> str:
    """Nur der MIME-Typ ohne Parameter, klein geschrieben."""
    return (content_type or "").split(";", 1)[0].strip().lower()


def inline_safe(content_type: str | None) -> bool:
    """Darf dieser Typ inline (Vorschau) statt als Download ausgeliefert werden?"""
    ct = _bare_type(content_type)
    if not ct or ct in _DANGEROUS:
        return False
    if ct == "application/pdf" or ct in _INLINE_TEXT:
        return True
    # Bilder ja — außer SVG, das oben schon ausgeschlossen ist.
    return ct.startswith("image/")


def sanitize_filename(name: str, fallback: str = "anhang") -> str:
    """Auf einen reinen Dateinamen reduzieren — kein Pfad, keine Steuerzeichen.

    Trennt Verzeichnisanteile ab (auch Windows-Backslashes), entfernt
    Steuerzeichen und führende Punkte; leer → fallback.
    """
    # Backslashes zu Slashes, dann letzten Pfadteil nehmen.
    candidate = str(name or "").replace("\\", "/").split("/")[-1]
    candidate = re.sub(r"[\x00-\x1f\x7f]", "", candidate)  # Steuerzeichen raus
    candidate = candidate.strip().lstrip(".").strip()
    return candidate or fallback


def unique_path(directory: Path, filename: str) -> Path:
    """Ein noch freier Pfad in `directory`: „a.pdf" → „a (1).pdf" → …"""
    target = directory / filename
    if not target.exists():
        return target
    name = Path(filename)  # .stem/.suffix werten einen führenden Punkt nicht als Extension
    counter = 1
    while True:
        candidate = directory / f"{name.stem} ({counter}){name.suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def save_bytes_to_dir(directory: Path, filename: str, data: bytes) -> Path:
    """Bytes ohne Überschreiben in `directory` ablegen; gibt den Zielpfad zurück."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = unique_path(directory, sanitize_filename(filename))
    target.write_bytes(data)
    return target
