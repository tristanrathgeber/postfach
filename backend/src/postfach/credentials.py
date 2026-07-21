"""Passwort-Auflösung: Umgebungsvariable → macOS-Schlüsselbund.

Das Passwort liegt entweder in einer `.env`-Variable (Bestandskonten) oder im
Schlüsselbund (per UI eingerichtete Konten) — NIE im Klartext in einer Datei
dieses Projekts. Die keyring-Aufrufe sind gekapselt (`_kr_*`), damit Tests sie
ohne echten macOS-Zugriff ersetzen können.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

_SERVICE = "postfach"


def _kr_get(name: str) -> str | None:
    import keyring

    return keyring.get_password(_SERVICE, name)


def _kr_set(name: str, password: str) -> None:
    import keyring

    keyring.set_password(_SERVICE, name, password)


def _kr_delete(name: str) -> None:
    import keyring
    import keyring.errors

    try:
        keyring.delete_password(_SERVICE, name)
    except keyring.errors.PasswordDeleteError:
        pass  # war nie gesetzt — kein Fehler


def set_password(account_name: str, password: str) -> None:
    _kr_set(account_name, password)


def delete_password(account_name: str) -> None:
    _kr_delete(account_name)


def resolve_password(account) -> str:
    """Bestandskonto (password_env deklariert): NUR die Env-Variable — eine
    leere/vergessene Env darf nicht still ein gleichnamiges Keychain-Secret
    ziehen. Verwaltetes Konto (kein password_env): der Schlüsselbund. Leerer
    String, wenn nirgends hinterlegt — der Aufrufer entscheidet über den Fehler."""
    env_name = getattr(account, "password_env", "") or ""
    if env_name:
        return os.environ.get(env_name, "").strip()
    try:
        return (_kr_get(account.name) or "").strip()
    except Exception:  # Schlüsselbund gesperrt/nicht verfügbar — nie hart crashen
        log.exception("Schlüsselbund-Zugriff für %s fehlgeschlagen", account.name)
        return ""
