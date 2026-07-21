"""Native macOS-Benachrichtigungen via osascript.

Bewusst osascript statt UNUserNotificationCenter: Letzteres verweigert
unsignierten Apps den Dienst. Titel/Text stammen aus Mail-Inhalten und sind
UNTRUSTED — sie werden ausschließlich als argv übergeben (`on run argv`),
nie in den AppleScript-Quelltext interpoliert (Injection).
"""

from __future__ import annotations

import subprocess

_SCRIPT = 'on run argv\ndisplay notification (item 2 of argv) with title (item 1 of argv)\nend run'


def pick_new_unseen(mails, last_uid: int) -> list:
    """Meldenswerte Mails: ungelesen UND neuer als der letzte Wasserstand —
    verhindert Doppel-Meldungen (Re-IDLE, EXPUNGE-Echos) und verschluckt
    keine früheren Mails, wenn mehrere in einem Fenster eintreffen."""
    fresh = [m for m in mails if not m.seen and m.uid > last_uid]
    return sorted(fresh, key=lambda m: m.uid)


def notify_macos(title: str, text: str) -> None:
    try:
        subprocess.run(
            ["osascript", "-e", _SCRIPT, title[:120], text[:200]],
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        # Benachrichtigung ist Komfort — nie einen Watcher daran sterben lassen.
        pass
