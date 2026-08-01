"""Postfach als natives macOS-Programm: WKWebView-Fenster statt Browser.

Startet den lokalen Server (falls nicht schon einer auf dem Port läuft) und
öffnet die App in einem eigenen Fenster. Läuft bereits ein Server (z. B. aus
dem Terminal), wird der einfach mitbenutzt.
"""

from __future__ import annotations

import logging
import socket
import threading
import time


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _failure_window(webview, message: str, logfile) -> None:
    """Startfehler SICHTBAR machen. Das Bundle hat kein Konsolenfenster — ohne
    dieses Fenster sähe ein kaputter Start aus wie „die App tut nichts"."""
    html = (
        "<html><body style=\"font:14px -apple-system,sans-serif;padding:28px;"
        "background:#faf9f6;color:#1a1917\">"
        "<h2 style=\"font-family:Georgia,serif;font-style:italic\">Postfach konnte nicht starten</h2>"
        f"<p>{message}</p>"
        f"<p style=\"color:#6f6a61;font-size:12.5px\">Details stehen im Protokoll:<br>"
        f"<code>{logfile or 'kein Protokoll schreibbar'}</code></p>"
        "<p style=\"color:#6f6a61;font-size:12.5px\">Bitte melde den Fehler mit diesem "
        "Protokoll-Auszug — ohne Passwörter oder privaten Mail-Inhalt.</p>"
        "</body></html>"
    )
    webview.create_window("Postfach — Fehler", html=html, width=620, height=380)
    webview.start()


def main() -> None:
    import uvicorn
    import webview
    from email_agent.cli import load_env

    from .app import HOST, PORT, _root, create_app
    from .logsetup import setup_logging

    root = _root()  # user_data_root(): im Binary ~/Library/Application Support/Postfach
    logfile = setup_logging(root)  # zuerst — sonst verschwindet ein Startfehler spurlos
    log = logging.getLogger("postfach.desktop")
    log.info("Postfach startet (Wurzel: %s)", root)

    if not _port_in_use(HOST, PORT):
        load_env(root)
        # Der Serverfehler passiert im Thread — dort abfangen und merken,
        # sonst stirbt er unbemerkt und wir warten nur auf einen Port.
        failure: list[BaseException] = []

        def serve() -> None:
            try:
                uvicorn.run(create_app(root=root), host=HOST, port=PORT, log_level="warning")
            except BaseException as exc:
                log.exception("Backend abgebrochen")
                failure.append(exc)

        server = threading.Thread(target=serve, daemon=True)
        server.start()
        deadline = time.time() + 20
        while not _port_in_use(HOST, PORT):
            if failure:
                _failure_window(webview, f"Das Backend brach ab: {failure[0]}", logfile)
                return
            if time.time() > deadline:
                log.error("Backend nicht erreichbar auf %s:%s (Zeitüberschreitung)", HOST, PORT)
                _failure_window(
                    webview,
                    f"Das Backend war nach 20 Sekunden nicht auf Port {PORT} erreichbar.",
                    logfile,
                )
                return
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
