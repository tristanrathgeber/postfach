"""Versions-Info + optionaler, expliziter Update-Check.

Der Update-Check spricht NUR auf ausdrücklichen Nutzer-Klick (`?check=1`) mit
GitHub — nie automatisch beim Start. Das ist eine bewusste Privatheits-
Entscheidung: Postfach macht im Normalbetrieb keinen einzigen Netz-Call, den
der Nutzer nicht selbst angestoßen hat.
"""

from __future__ import annotations

import logging

from . import __version__

log = logging.getLogger(__name__)

_RELEASES_URL = "https://api.github.com/repos/tristanrathgeber/postfach/releases/latest"


def _norm(tag: str) -> tuple[int, ...]:
    """„v0.10.0" → (0, 10, 0) für einen robusten Zahlenvergleich."""
    parts = tag.strip().lstrip("vV").split("-")[0].split(".")
    out = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            break
    return tuple(out)


def _fetch_latest_tag() -> str | None:
    """Neuester Release-Tag von GitHub — None bei Netzproblemen (nie werfen)."""
    import httpx

    try:
        resp = httpx.get(_RELEASES_URL, timeout=10, headers={"Accept": "application/vnd.github+json"})
        resp.raise_for_status()
        return str(resp.json().get("tag_name") or "") or None
    except Exception:
        log.info("Update-Check fehlgeschlagen (offline?) — ignoriert")
        return None


def version_info(check: bool = False) -> dict:
    info: dict = {"version": __version__, "update_available": False}
    if not check:
        return info  # kein Netz-Call ohne ausdrücklichen Wunsch
    latest = _fetch_latest_tag()
    # `checked` unterscheidet „erreicht, du bist aktuell" von „nicht erreichbar"
    # — sonst zeigt die UI bei Offline/Rate-Limit fälschlich „aktuell".
    info["checked"] = latest is not None
    if latest:
        info["latest"] = latest
        info["update_available"] = _norm(latest) > _norm(__version__)
    return info
