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
    """Thread-sicherer Versionszähler je Konto (SSE-Quelle)."""

    def __init__(self) -> None:
        self._versions: dict[str, int] = {}
        self._lock = threading.Lock()

    def bump(self, account: str) -> None:
        with self._lock:
            self._versions[account] = self._versions.get(account, 0) + 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._versions)


class AccountWatcher:
    """Kern ohne Threading — testbar über poll_once mit injiziertem Client."""

    def __init__(self, account: str, state: LiveState, on_new_mail: Callable[[str], None] | None) -> None:
        self.account = account
        self._state = state
        self._on_new_mail = on_new_mail

    def poll_once(self, client) -> bool:
        responses = client.idle_check(timeout=_IDLE_CHECK_SECONDS)
        has_new = any(
            isinstance(item, tuple) and len(item) >= 2 and item[1] == b"EXISTS"
            for item in (responses or [])
        )
        if has_new:
            self._state.bump(self.account)
            if self._on_new_mail is not None:
                try:
                    self._on_new_mail(self.account)
                except Exception:
                    log.exception("new-mail-Hook für %s fehlgeschlagen", self.account)
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
                backoff = 0
                idle_started = time.monotonic()
                client.idle()
                try:
                    while True:
                        watcher.poll_once(client)
                        if time.monotonic() - idle_started > _REIDLE_AFTER_SECONDS:
                            client.idle_done()
                            client.idle()
                            idle_started = time.monotonic()
                finally:
                    try:
                        client.idle_done()
                        client.logout()
                    except Exception:
                        pass
            except Exception as exc:
                wait = _RECONNECT_BACKOFF[min(backoff, len(_RECONNECT_BACKOFF) - 1)]
                backoff += 1
                log.warning("Watcher %s: %s — neuer Versuch in %ss", account_name, exc, wait)
                time.sleep(wait)

    thread = threading.Thread(target=run, daemon=True, name=f"watcher-{account_name}")
    thread.start()
    return thread
