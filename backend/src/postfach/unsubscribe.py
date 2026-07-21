"""1-Klick-Abmelden über List-Unsubscribe (RFC 2369 / RFC 8058).

Strategie in fester Reihenfolge: One-Click-HTTPS-POST (Server, ohne Browser,
ohne Redirects) → mailto (Abmelde-Mail über den normalen SMTP-Pfad) → sonst
liefert die API nur den HTTPS-Link, den die UI im Browser öffnet. Header-
Inhalte sind UNTRUSTED Mail-Daten: nur https-URLs, mailto-Adressen laufen
durch die CRLF-Sanitisierung des Versand-Pfads.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx

_ENTRY_RE = re.compile(r"<([^>]+)>")
_TIMEOUT = 15


@dataclass(frozen=True)
class UnsubscribeTarget:
    https: str | None = None
    mailto: str | None = None
    mailto_subject: str | None = None
    one_click: bool = False


def parse_list_unsubscribe(header: str, post_header: str = "") -> UnsubscribeTarget:
    """`<mailto:…>, <https://…>` → Ziele; alles außer https/mailto wird ignoriert."""
    https = mailto = subject = None
    for raw in _ENTRY_RE.findall(header or ""):
        url = urlparse(raw.strip())
        if url.scheme == "https" and https is None:
            https = raw.strip()
        elif url.scheme == "mailto" and mailto is None:
            mailto = url.path.strip()
            params = parse_qs(url.query)
            subject = (params.get("subject") or [None])[0]
    one_click = "one-click" in (post_header or "").lower() and https is not None
    return UnsubscribeTarget(https=https, mailto=mailto, mailto_subject=subject, one_click=one_click)


def _host_is_public(host: str) -> bool:
    """SSRF-Schutz: der Header ist UNTRUSTED — nie an Loopback/LAN/Metadaten
    POSTen. Vorab-Auflösung; ein DNS-Rebinding-Restfenster bleibt (httpx löst
    erneut auf), akzeptabel für einen nutzergeklickten, blinden POST ohne
    zurückgereichte Antwort."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            return False
    return bool(infos)


def one_click_post(url: str) -> None:
    """RFC 8058: POST mit festem Body — keine Redirects (Abmelde-Endpunkte,
    die umleiten, bekommen keinen blinden Folge-Request)."""
    host = urlparse(url).hostname or ""
    if not _host_is_public(host):
        raise ValueError(f"Abmelde-Ziel {host!r} ist nicht öffentlich erreichbar")
    response = httpx.post(
        url,
        content="List-Unsubscribe=One-Click",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=_TIMEOUT,
        follow_redirects=False,
    )
    if response.status_code >= 400:
        raise httpx.HTTPStatusError(
            f"Abmelde-Endpunkt antwortete {response.status_code}",
            request=response.request, response=response,
        )
