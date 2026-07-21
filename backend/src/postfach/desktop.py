"""Postfach als natives macOS-Programm: WKWebView-Fenster statt Browser.

Startet den lokalen Server (falls nicht schon einer auf dem Port läuft) und
öffnet die App in einem eigenen Fenster. Läuft bereits ein Server (z. B. aus
dem Terminal), wird der einfach mitbenutzt.
"""

from __future__ import annotations

import socket
import threading
import time


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def main() -> None:
    import uvicorn
    import webview

    from email_agent.cli import load_env

    from .app import HOST, PORT, _root, create_app

    root = _root()  # user_data_root(): im Binary ~/Library/Application Support/Postfach
    if not _port_in_use(HOST, PORT):
        load_env(root)
        server = threading.Thread(
            target=lambda: uvicorn.run(create_app(root=root), host=HOST, port=PORT, log_level="warning"),
            daemon=True,
        )
        server.start()
        deadline = time.time() + 20
        while not _port_in_use(HOST, PORT):
            if time.time() > deadline:
                raise RuntimeError("Backend wollte nicht starten (Port 8722).")
            time.sleep(0.2)

    webview.create_window(
        "Postfach",
        f"http://{HOST}:{PORT}",
        width=1360,
        height=880,
        min_size=(1000, 640),
    )
    webview.start()


if __name__ == "__main__":
    main()
