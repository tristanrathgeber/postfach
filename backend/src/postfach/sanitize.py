"""HTML-Mail-Sanitisierung: nh3 (ammonia) mit Bild-Blocking auf Parser-Ebene.

Zwei Varianten pro Mail: `blocked` (Remote-Bilder entfernt → Tracking-Schutz,
Standard) und `with_images` (Remote-Bilder erlaubt, auf expliziten Klick).
Beide vollständig sanitisiert — kein Script, keine Event-Handler.

Das Blocking läuft als nh3-attribute_filter im Parser, nicht als Regex über
den HTML-String: Regexe waren per alt=">"-Trick und protokoll-relativen URLs
umgehbar (Security-Review-Finding). Für die Banner-Anzeige wird zusätzlich
der Rohtext vorgescannt — ein falsch-positiver Banner ist harmlos, ein
unerkanntes Tracking-Pixel nicht.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import nh3

_ANCHOR_RE = re.compile(r"<a\b", re.I)
_RAW_REMOTE_IMG_RE = re.compile(r"(src|srcset)\s*=\s*[\"']?\s*(https?:)?//", re.I)
_REMOTE_PREFIXES = ("http://", "https://", "//")


@dataclass(frozen=True)
class SanitizedHtml:
    blocked: str
    with_images: str
    had_remote_images: bool


def _clean(html: str, attribute_filter=None) -> str:
    return nh3.clean(
        html,
        url_schemes={"http", "https", "mailto", "cid"},
        link_rel="noopener noreferrer",
        attribute_filter=attribute_filter,
    )


def _harden_links(html: str) -> str:
    return _ANCHOR_RE.sub('<a target="_blank"', html)


def sanitize_mail_html(html: str) -> SanitizedHtml:
    seen = {"remote": False}

    def _block_remote_imgs(tag: str, attr: str, value: str):
        if tag == "img" and attr in {"src", "srcset"}:
            candidate = value.strip().lower()
            if attr == "srcset" or candidate.startswith(_REMOTE_PREFIXES):
                seen["remote"] = True
                return None  # Attribut komplett entfernen — kein URL-Rest im Markup
        return value

    blocked = _harden_links(_clean(html, attribute_filter=_block_remote_imgs))
    with_images = _harden_links(_clean(html))
    had_remote = (
        seen["remote"]
        or blocked != with_images
        or bool(_RAW_REMOTE_IMG_RE.search(html))
    )
    return SanitizedHtml(blocked=blocked, with_images=with_images, had_remote_images=had_remote)
