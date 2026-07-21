"""Kategorie → Ordner-Overlay (Ordner-Mapping-Assistent).

Additiver Overlay über `agent_config.folder_for`: liegt für eine Kategorie
ein bestehender Ordner (z. B. `INBOX/Werbung`), wird der genutzt statt
`AI/<Kategorie>`. Wichtig für Anbieter mit Ordner-Limit (GMX). Ändert nie den
Klassifikator, nur das Archiv-Ziel.
"""

from __future__ import annotations

from pathlib import Path

from .stores import _JsonFile


class FolderMap(_JsonFile):
    def __init__(self, path: Path) -> None:
        super().__init__(path, {})

    def mapping(self) -> dict[str, str]:
        with self._lock:
            return self._read()

    def put(self, mapping: dict) -> None:
        clean = {
            str(cat).strip(): str(folder).strip()
            for cat, folder in (mapping or {}).items()
            if str(cat).strip() and str(folder).strip()
        }
        with self._lock:
            self._write(clean)

    def folder_for(self, category: str) -> str | None:
        """Overlay-Ordner für die Kategorie oder None (→ Aufrufer nutzt den
        agent_config-Fallback AI/<Kategorie>)."""
        return self.mapping().get(category)
