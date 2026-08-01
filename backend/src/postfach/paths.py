"""Pfad-Auflösung für Entwicklung UND das gebündelte Binary (PyInstaller).

Zwei getrennte Wurzeln, weil das Binary kein Repo hat:
- resource_dir(): mitgebündelte, NUR-lesbare Ressourcen (Frontend-dist, Defaults).
- user_data_root(): SCHREIBBARE config/data (im Binary unter Application Support).
"""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

_APP_SUPPORT = "Postfach"


def is_frozen() -> bool:
    """True im PyInstaller-Bundle (dann existiert sys._MEIPASS)."""
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


def resource_dir() -> Path:
    """Wurzel der mitgebündelten Ressourcen. Frozen: der PyInstaller-Auszug;
    Dev: die Repo-Wurzel (Elternteil von backend/)."""
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[3]


def user_data_root() -> Path:
    """Schreibbare Wurzel für config/ und data/.

    POSTFACH_ROOT hat immer Vorrang (Tests/Skripte). Sonst IMMER
    ~/Library/Application Support/Postfach — auch in der Entwicklung.

    Bewusst NICHT die Repo-Wurzel: dort lägen echte Mail-Daten, Passwort-Env
    und die private config.yaml mitten im Git-Arbeitsverzeichnis. Bei einem
    öffentlichen Repo genügt ein `git add -f` oder ein verrutschtes
    .gitignore-Muster, und die eigene Mailbox ist veröffentlicht. Getrennte
    Verzeichnisse machen diesen Fehler unmöglich statt nur unwahrscheinlich.
    """
    override = os.environ.get("POSTFACH_ROOT")
    if override:
        return Path(override)
    try:
        root = Path.home() / "Library" / "Application Support" / _APP_SUPPORT
    except RuntimeError:  # HOME unbestimmbar
        import tempfile

        root = Path(tempfile.gettempdir()) / _APP_SUPPORT
    # Best Effort — die Stores legen ihre Verzeichnisse ohnehin lazy an
    # (mkdir parents=True); ein Fehler hier darf den Start nicht crashen.
    with contextlib.suppress(OSError):
        root.mkdir(parents=True, exist_ok=True)
    return root
