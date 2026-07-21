"""Verwaltete Konten (per UI eingerichtet) in data/accounts.json.

Bewusst getrennt von der hand-editierten config.yaml: Postfach schreibt hier,
überschreibt nie die Nutzer-Konfiguration. Enthält NUR Verbindungsdaten —
das Passwort liegt ausschließlich im Schlüsselbund ([[credentials]]).
"""

from __future__ import annotations

from pathlib import Path

from .stores import _JsonFile

# Was persistiert wird — niemals ein Passwortfeld.
_FIELDS = ("name", "provider", "address", "imap_host", "imap_port",
           "smtp_host", "smtp_port", "sent_folder")


class AccountStore(_JsonFile):
    def __init__(self, path: Path) -> None:
        super().__init__(path, [])

    def list(self) -> list[dict]:
        with self._lock:
            return self._read()

    def names(self) -> set[str]:
        return {a["name"] for a in self.list()}

    def add(self, account: dict) -> None:
        clean = {k: account.get(k) for k in _FIELDS}
        clean["name"] = str(clean["name"]).strip()
        clean["imap_port"] = int(clean.get("imap_port") or 993)
        clean["smtp_port"] = int(clean.get("smtp_port") or 587)
        with self._lock:
            current = [a for a in self._read() if a["name"] != clean["name"]]
            current.append(clean)
            self._write(current)

    def remove(self, name: str) -> bool:
        with self._lock:
            current = self._read()
            remaining = [a for a in current if a["name"] != name]
            if len(remaining) == len(current):
                return False
            self._write(remaining)
        return True
