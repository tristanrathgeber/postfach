"""Logdatei einrichten — damit Fehler nachvollziehbar sind.

Das gebündelte Programm hat kein Konsolenfenster (`console=False` in
postfach.spec): jede Ausnahme, jeder IMAP-Abbruch und jeder Startfehler
verschwand bisher spurlos. Ein Backend, das nicht hochkommt, sah für den
Nutzer aus wie „die App tut nichts" — und ein Beta-Bugreport ohne Log ist
nicht nachvollziehbar.

Bewusst KEINE Telemetrie: die Datei bleibt auf dem Rechner, wird rotiert und
enthält keine Mail-Inhalte (die Module loggen Kennungen und Fehlertexte).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_MAX_BYTES = 1_000_000  # ~1 MB je Datei
_BACKUPS = 3            # zusammen also höchstens ~4 MB
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def log_dir(root: Path) -> Path:
    return Path(root) / "logs"


def log_path(root: Path) -> Path:
    return log_dir(root) / "postfach.log"


def setup_logging(root: Path, level: int = logging.INFO) -> Path | None:
    """Root-Logger auf eine rotierende Datei unter <root>/logs/ legen.

    Gibt den Pfad zurück, oder None wenn nicht geschrieben werden kann (dann
    läuft die App weiter — ein fehlendes Log darf den Start nie verhindern).
    Mehrfach aufrufbar: ein bereits gesetzter Handler wird nicht verdoppelt.
    """
    target = log_path(root)
    root_logger = logging.getLogger()
    for existing in root_logger.handlers:
        # Nur als „schon eingerichtet" zählen, wenn es DIESELBE Datei ist —
        # sonst würde ein zweiter Aufruf mit anderer Wurzel stillschweigend
        # den alten Pfad melden, obwohl dort nichts geschrieben wird.
        if (
            isinstance(existing, RotatingFileHandler)
            and getattr(existing, "_postfach", False)
            and Path(existing.baseFilename) == target.resolve()
        ):
            return target
    try:
        log_dir(root).mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(target, maxBytes=_MAX_BYTES, backupCount=_BACKUPS,
                                      encoding="utf-8")
    except OSError:
        return None
    handler.setFormatter(logging.Formatter(_FORMAT))
    handler._postfach = True  # type: ignore[attr-defined]
    root_logger.addHandler(handler)
    # Nur anheben, nie herabsetzen — eine bewusst gesetzte Stufe bleibt.
    if root_logger.level == logging.NOTSET or root_logger.level > level:
        root_logger.setLevel(level)
    return target
