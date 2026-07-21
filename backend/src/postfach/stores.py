"""Lokale JSON-Stores: Einstellungen (Signaturen), Entwürfe, Snippets.

Bewusst Dateien statt Datenbank: menschenlesbar, trivial zu sichern/exportieren
(Local-First-Versprechen). Thread-sicher über Locks; FastAPI-Routen laufen im
Threadpool.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path


class _JsonFile:
    def __init__(self, path: Path, default):
        self._path = Path(path)
        self._default = default
        self._lock = threading.Lock()
        self._cache = None  # geparster Inhalt — der Store ist alleiniger Schreiber

    def _read(self):
        if self._cache is None:
            self._cache = self._load()
        return copy.deepcopy(self._cache)

    def _load(self):
        if not self._path.exists():
            return copy.deepcopy(self._default)
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            # Kaputte Datei nie still verwerfen: beiseitelegen, mit Default weiterlaufen.
            self._path.replace(self._path.with_suffix(self._path.suffix + ".broken"))
            return copy.deepcopy(self._default)

    def _write(self, data) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Atomar via temp + rename — ein Absturz mitten im Schreiben darf die
        # Datei nicht korrumpieren (sonst 500er auf jedem Store-Endpunkt).
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self._path)
        self._cache = copy.deepcopy(data)


class SettingsStore(_JsonFile):
    def __init__(self, path: Path) -> None:
        super().__init__(path, {"signatures": {}, "notifications": {}, "undo_seconds": 15})

    def get(self) -> dict:
        with self._lock:
            data = self._read()
        data.setdefault("signatures", {})
        data.setdefault("notifications", {})
        data.setdefault("undo_seconds", 15)
        return data

    def put(self, data: dict) -> None:
        """Teil-Update: nur mitgeschickte Sektionen ersetzen — ein Client nach
        altem Contract (nur signatures) darf die Toggles nicht zurücksetzen."""
        with self._lock:
            current = self._read()
            if data.get("signatures") is not None:
                current["signatures"] = {str(k): str(v) for k, v in data["signatures"].items()}
            if data.get("notifications") is not None:
                # Fehlender Konto-Eintrag = Benachrichtigungen an (Default)
                current["notifications"] = {str(k): bool(v) for k, v in data["notifications"].items()}
            if data.get("undo_seconds") is not None:
                current["undo_seconds"] = max(0, min(int(data["undo_seconds"]), 60))
            self._write(current)

    def notifications_enabled(self, account: str) -> bool:
        return bool(self.get()["notifications"].get(account, True))


class DraftStore(_JsonFile):
    def __init__(self, path: Path) -> None:
        super().__init__(path, [])

    def upsert(self, draft: dict) -> str:
        # Das Modell ist bereits validiert (DraftSaveBody) — 1:1 persistieren,
        # damit neue Felder nicht still verschluckt werden. Nur id/updated ergänzen.
        draft_id = str(draft.get("id") or uuid.uuid4())
        entry = {
            **draft,
            "id": draft_id,
            "updated": datetime.now().isoformat(),
        }
        with self._lock:
            drafts = [d for d in self._read() if d.get("id") != draft_id]
            drafts.append(entry)
            self._write(drafts)
        return draft_id

    def list(self, account: str) -> list[dict]:
        with self._lock:
            drafts = self._read()
        mine = [d for d in drafts if d.get("account") == account]
        return sorted(mine, key=lambda d: d.get("updated", ""), reverse=True)

    def delete(self, draft_id: str) -> bool:
        with self._lock:
            drafts = self._read()
            remaining = [d for d in drafts if d.get("id") != draft_id]
            if len(remaining) == len(drafts):
                return False
            self._write(remaining)
        return True


class SnippetStore(_JsonFile):
    def __init__(self, path: Path) -> None:
        super().__init__(path, [])

    def get(self) -> list[dict]:
        with self._lock:
            return self._read()

    def put(self, items: list[dict]) -> None:
        cleaned = [
            {
                "abbrev": str(i.get("abbrev", "")).strip(),
                "title": str(i.get("title", "")).strip(),
                "text": str(i.get("text", "")),
            }
            for i in items
            if str(i.get("abbrev", "")).strip()
        ]
        with self._lock:
            self._write(cleaned)
