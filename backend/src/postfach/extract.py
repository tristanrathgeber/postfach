"""Lokale Struktur-Extraktion: Termine, Beträge, Sendungsnummern aus Mailtext.

Regelbasiert, KEIN LLM — schnell, deterministisch, offline. Sendungsnummern
verlinken auf die Tracking-Seite des Anbieters; das Ziel ist eine feste,
bekannte URL (Host-Allowlist), in die nur die Nummer eingesetzt wird — nie
eine aus der Mail übernommene Adresse.
"""

from __future__ import annotations

import re

# Entities stehen praktisch immer im oberen Teil einer Mail; der Cap begrenzt
# zugleich den Scan-Aufwand adversarischer Bodies (Amount-Regex ist O(n) je Position).
_TEXT_CAP = 10_000
_MAX_PER_KIND = 8

# Beträge: 39,95 € · € 1.200,00 · EUR 14,28 (deutsche Tausender/Dezimal).
# Possessive Quantoren (*+) gegen quadratisches Backtracking bei langen
# Tausender-Ketten ohne Währungs-Terminator (Python 3.11+).
_AMOUNT_RE = re.compile(
    r"(?:(?:€|EUR)\s*\d{1,3}(?:\.\d{3})*+(?:,\d{2})?"
    r"|\d{1,3}(?:\.\d{3})*+(?:,\d{2})?\s*(?:€|EUR))",
)

# Datum: 24.07.2026 · 24.7.26 · 24. Juli 2026 · 1. Januar
_MONTHS = "Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember"
_DATE_RE = re.compile(
    rf"(?:\b\d{{1,2}}\.\d{{1,2}}\.\d{{2,4}}\b"
    rf"|\b\d{{1,2}}\.\s*(?:{_MONTHS})(?:\s+\d{{4}})?)",
)
# Uhrzeit: 14:30 Uhr · 9:05
_TIME_RE = re.compile(r"\b\d{1,2}:\d{2}(?:\s*Uhr)?\b")

# Sendungsnummern (bekannte Anbieter-Muster) → (Regex, Tracking-URL-Template)
_TRACKING = [
    ("ups", re.compile(r"\b1Z[0-9A-Z]{16}\b"),
     "https://www.ups.com/track?tracknum={n}"),
    ("dhl", re.compile(r"\bJJD\d{16,18}\b|\b\d{20}\b"),
     "https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html?piececode={n}"),
    ("hermes", re.compile(r"\b\d{14}\b"),
     "https://www.myhermes.de/empfangen/sendungsverfolgung/sendungsinformation/#{n}"),
    ("dpd", re.compile(r"\b0\d{13}\b"),
     "https://tracking.dpd.de/status/de_DE/parcel/{n}"),
]


def _emit(seen: set[str], out: list, kind: str, text: str, value: str, url: str | None = None) -> bool:
    """True, wenn tatsächlich eingefügt (nicht dedupt) — für ehrliche Zähler."""
    key = f"{kind}:{value.lower()}"
    if key in seen:
        return False
    seen.add(key)
    entity = {"kind": kind, "text": text.strip(), "value": value.strip()}
    if url:
        entity["url"] = url
    out.append(entity)
    return True


def extract_entities(text: str) -> list[dict]:
    if not text:
        return []
    text = text[:_TEXT_CAP]
    out: list[dict] = []
    seen: set[str] = set()

    counts = {"tracking": 0, "amount": 0, "date": 0}

    # Sendungsnummern zuerst (spezifischste Muster) — verhindert, dass eine
    # 14-/20-stellige Nummer fälschlich als „Datum/Betrag" durchrutscht.
    for _carrier, pattern, url_tpl in _TRACKING:
        for match in pattern.finditer(text):
            if counts["tracking"] >= _MAX_PER_KIND:
                break
            number = match.group(0)
            if _emit(seen, out, "tracking", number, number, url_tpl.format(n=number)):
                counts["tracking"] += 1

    for match in _AMOUNT_RE.finditer(text):
        if counts["amount"] >= _MAX_PER_KIND:
            break
        raw = match.group(0)
        if _emit(seen, out, "amount", raw, re.sub(r"\s+", " ", raw)):
            counts["amount"] += 1

    for pattern in (_DATE_RE, _TIME_RE):
        for match in pattern.finditer(text):
            if counts["date"] >= _MAX_PER_KIND:
                break
            raw = match.group(0)
            if _emit(seen, out, "date", raw, re.sub(r"\s+", " ", raw)):
                counts["date"] += 1
    return out
