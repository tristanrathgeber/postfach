#!/usr/bin/env python3
"""Prüft die Verweise in der Doku — ohne Abhängigkeiten, läuft überall.

Zwei Fehlerarten, die still passieren und niemandem auffallen:

1. Das Handbuch hat ein Inhaltsverzeichnis mit Ankern (`#5-lesen`). Wird ein
   Kapitel umbenannt, zeigt der Verweis ins Leere — die Seite rendert weiter,
   nur der Klick tut nichts.
2. README und Handbuch verweisen auf Dateien und Bilder im Repo. Zieht eine
   Datei um, bleibt ein toter Link zurück.

Beendet sich mit 1, wenn etwas nicht stimmt (für die CI).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = [REPO / "README.md", REPO / "docs" / "HANDBUCH.md", REPO / "CONTRIBUTING.md"]

# Externe Ziele und Anker prüfen wir nicht (kein Netz in dieser Prüfung).
_SKIP_LINK = re.compile(r"^(https?:|mailto:|#)")


def github_slug(heading: str) -> str:
    """GitHubs Anker-Regel: klein, Satzzeichen weg, Leerzeichen zu Bindestrichen."""
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s\-]", "", slug, flags=re.UNICODE)
    return slug.replace(" ", "-")


def check_anchors(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    headings = re.findall(r"^#{1,6}\s+(.+)$", text, re.M)
    slugs = {github_slug(h) for h in headings}
    problems = []
    for target in re.findall(r"\]\(#([^)]+)\)", text):
        if target not in slugs:
            problems.append(f"{path.name}: Anker „#{target}“ zeigt auf kein Kapitel")
    return problems


def check_files(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems = []
    for target in re.findall(r"\]\(([^)]+)\)", text):
        target = target.split("#", 1)[0].strip()
        if not target or _SKIP_LINK.match(target):
            continue
        if not (path.parent / target).resolve().exists():
            problems.append(f"{path.name}: Verweis „{target}“ existiert nicht")
    return problems


def main() -> int:
    problems: list[str] = []
    for path in DOCS:
        if not path.exists():
            problems.append(f"{path.name} fehlt")
            continue
        problems += check_anchors(path)
        problems += check_files(path)

    if problems:
        print("Doku-Prüfung fehlgeschlagen:", file=sys.stderr)
        for problem in problems:
            print(f"  • {problem}", file=sys.stderr)
        return 1
    print(f"Doku in Ordnung ({len(DOCS)} Dateien geprüft: Anker und Verweise).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
