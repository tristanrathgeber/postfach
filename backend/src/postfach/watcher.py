"""Live-Push: IMAP-IDLE-Watcher pro Konto + Versionszähler für Server-Sent Events.

Der Mailserver meldet neue Mails aktiv (IDLE, RFC 2177) — kein Polling gegen
den Server. Ein Watcher-Thread pro Konto hält eine eigene, rein lesende
IMAP-Verbindung; bei neuen Mails wird der Versionszähler erhöht (den streamt
/api/events an die App) und optional ein Hook gerufen (Emilia-Index).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

log = logging.getLogger("postfach.watcher")

_IDLE_CHECK_SECONDS = 20
_REIDLE_AFTER_SECONDS = 12 * 60  # Server werfen IDLE nach ~30 min ab — vorher erneuern
_RECONNECT_BACKOFF = [5, 15, 60, 180]


class LiveState:
    """Thread-sicher: Versionszähler je Konto (SSE-Quelle) + Verbindungsstatus."""

    def __init__(self) -> None:
        self._versions: dict[str, int] = {}
        self._status: dict[str, dict] = {}
        self._lock = threading.Lock()

    def bump(self, account: str) -> None:
        with self._lock:
            self._versions[account] = self._versions.get(account, 0) + 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._versions)

    def set_status(self, account: str, connected: bool, error: str | None = None) -> None:
        """Nie still scheitern: Zustandswechsel werden sichtbar gemacht.
        `since` = Zeitpunkt des letzten Wechsels (verbunden seit / getrennt seit)."""
        from datetime import datetime

        with self._lock:
            prev = self._status.get(account)
            since = (
                prev["since"]
                if prev is not None and prev["connected"] == connected
                else datetime.now().isoformat(timespec="seconds")
            )
            self._status[account] = {"connected": connected, "since": since, "last_error": error}

    def status_snapshot(self) -> dict[str, dict]:
        with self._lock:
            return {name: dict(entry) for name, entry in self._status.items()}


def _has_new_mail(responses) -> bool:
    return any(
        isinstance(item, tuple) and len(item) >= 2 and item[1] == b"EXISTS"
        for item in (responses or [])
    )


class AccountWatcher:
    """Kern ohne Threading — testbar über poll_once mit injiziertem Client."""

    def __init__(self, account: str, state: LiveState, on_new_mail: Callable[[str], None] | None) -> None:
        self.account = account
        self._state = state
        self._on_new_mail = on_new_mail

    def notify_new_mail(self) -> None:
        self._state.bump(self.account)
        if self._on_new_mail is not None:
            try:
                self._on_new_mail(self.account)
            except Exception:
                log.exception("new-mail-Hook für %s fehlgeschlagen", self.account)

    def poll_once(self, client) -> bool:
        responses = client.idle_check(timeout=_IDLE_CHECK_SECONDS)
        has_new = _has_new_mail(responses)
        if has_new:
            self.notify_new_mail()
        return has_new


def start_watcher_thread(
    account_name: str,
    connect: Callable[[], object],
    state: LiveState,
    on_new_mail: Callable[[str], None] | None = None,
) -> threading.Thread:
    """Daemon-Thread: verbinden → IDLE-Schleife → bei Fehlern mit Backoff neu."""
    watcher = AccountWatcher(account_name, state, on_new_mail)

    def run() -> None:
        backoff = 0
        while True:
            try:
                client = connect()
                client.select_folder("INBOX", readonly=True)
                state.set_status(account_name, connected=True)
                backoff = 0
                idle_started = time.monotonic()
                client.idle()
                try:
                    while True:
                        watcher.poll_once(client)
                        if time.monotonic() - idle_started > _REIDLE_AFTER_SECONDS:
                            # idle_done → (command_text, responses): ein EXISTS
                            # im Erneuerungsfenster darf nicht verloren gehen.
                            _text, pending = client.idle_done()
                            if _has_new_mail(pending):
                                watcher.notify_new_mail()
                            client.idle()
                            idle_started = time.monotonic()
                finally:
                    try:
                        client.idle_done()
                        client.logout()
                    except Exception:
                        pass
            except Exception as exc:
                state.set_status(account_name, connected=False, error=str(exc))
                wait = _RECONNECT_BACKOFF[min(backoff, len(_RECONNECT_BACKOFF) - 1)]
                backoff += 1
                log.warning("Watcher %s: %s — neuer Versuch in %ss", account_name, exc, wait)
                time.sleep(wait)

    thread = threading.Thread(target=run, daemon=True, name=f"watcher-{account_name}")
    thread.start()
    return thread
