"""Cookbook / Modell-Assistent — „welche KI passt am besten zu Postfach auf
diesem Rechner?"

Idee (nach dem Vorbild von Odysseus' Cookbook): den Rechner scannen, einen
kuratierten Katalog lokaler Modelle danach filtern, was TATSÄCHLICH laufen
würde, und daraus das empfehlen, das am besten zu Postfachs Aufgabe passt
(deutsche Mail: Sortieren als JSON, Entwürfe im eigenen Stil, Chat) — nicht das
größte. Herunterladen und Aktivieren übernimmt api.py über Ollama.

Der Fit-Wert kodiert genau diese Produkt-Eignung: qwen2.5:7b ist der Sweetspot
(bestes Deutsch/JSON-Verhältnis bei interaktivem Tempo), große Modelle sind
leicht abgewertet, weil sie das Sortieren/Antworten spürbar zäh machen.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    id: str  # Ollama-Tag
    label: str
    params: str  # z. B. "7B"
    size_gb: float  # Download-Größe
    min_ram_gb: int  # empfohlener Arbeitsspeicher, um flüssig zu laufen
    role: str  # "allround" | "klein" | "stark"
    strengths: tuple[str, ...]
    note: str
    fit: int  # 0–100: Eignung für Postfach (höher = besser passend)


# Kuratierter Katalog — bewusst klein gehalten; nur Modelle, die sich für
# deutsche Mail bewährt haben. Reihenfolge = Anzeige-Reihenfolge.
CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="qwen2.5:7b", label="Qwen 2.5 · 7B", params="7B", size_gb=4.7, min_ram_gb=12,
        role="allround",
        strengths=("Sehr gutes Deutsch", "Zuverlässiges JSON zum Sortieren", "Natürliche Entwürfe"),
        note="Der Sweetspot für Postfach: stark genug für gute Entwürfe, schnell genug für flüssiges Sortieren.",
        fit=92,
    ),
    ModelSpec(
        id="llama3.1:8b", label="Llama 3.1 · 8B", params="8B", size_gb=4.9, min_ram_gb=12,
        role="allround",
        strengths=("Solides Deutsch", "Gutes Instruktionsverständnis", "Verbreitet & robust"),
        note="Sehr ausgewogene Alternative zu Qwen — minimal weniger präzise beim Sortieren.",
        fit=86,
    ),
    ModelSpec(
        id="gemma2:9b", label="Gemma 2 · 9B", params="9B", size_gb=5.4, min_ram_gb=14,
        role="stark",
        strengths=("Exzellentes Deutsch (Google, EU-Sprachen)", "Schöne Formulierungen"),
        note="Die stärkste Wahl fürs Formulieren — etwas schwerer, lohnt sich ab 16 GB.",
        fit=84,
    ),
    ModelSpec(
        id="qwen2.5:14b", label="Qwen 2.5 · 14B", params="14B", size_gb=9.0, min_ram_gb=20,
        role="stark",
        strengths=("Bestes Deutsch im Katalog", "Sehr präzise"),
        note="Spürbar klüger, aber langsamer — nur wenn reichlich RAM da ist und Tempo egal.",
        fit=85,
    ),
    ModelSpec(
        id="qwen2.5:3b", label="Qwen 2.5 · 3B", params="3B", size_gb=1.9, min_ram_gb=8,
        role="klein",
        strengths=("Gutes Deutsch für die Größe", "Zuverlässiges JSON", "Flott"),
        note="Die beste kleine Wahl: erstaunlich fähig beim Sortieren, läuft auf 8 GB flüssig.",
        fit=78,
    ),
    ModelSpec(
        id="llama3.2:3b", label="Llama 3.2 · 3B", params="3B", size_gb=2.0, min_ram_gb=8,
        role="klein",
        strengths=("Ordentliches Deutsch", "Klein & schnell"),
        note="Postfachs bisheriger Standard — solide, aber Qwen 3B sortiert etwas sauberer.",
        fit=70,
    ),
    ModelSpec(
        id="gemma2:2b", label="Gemma 2 · 2B", params="2B", size_gb=1.6, min_ram_gb=6,
        role="klein",
        strengths=("Für 2B überraschend gutes Deutsch", "Sehr genügsam"),
        note="Gut für ältere/kleine Macs — Entwürfe werden einfacher, das Sortieren bleibt brauchbar.",
        fit=64,
    ),
    ModelSpec(
        id="llama3.2:1b", label="Llama 3.2 · 1B", params="1B", size_gb=1.3, min_ram_gb=5,
        role="klein",
        strengths=("Winzig & blitzschnell", "Läuft praktisch überall"),
        note="Notnagel für sehr wenig RAM: fürs Sortieren okay, Entwürfe werden holprig.",
        fit=48,
    ),
)

_BY_ID = {m.id: m for m in CATALOG}


def get_spec(model_id: str) -> ModelSpec | None:
    return _BY_ID.get(model_id)


def scan_system() -> dict:
    """Leichter, plattformübergreifender Scan: RAM, Architektur, Kerne, Chip."""
    ram_bytes = 0
    try:  # Unix/macOS: Seitenanzahl × Seitengröße
        ram_bytes = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (ValueError, OSError, AttributeError):
        ram_bytes = 0
    ram_gb = round(ram_bytes / (1024**3), 1) if ram_bytes else 0.0

    arch = platform.machine() or "?"
    chip = platform.processor() or arch
    # Auf Apple Silicon liefert processor() oft "arm"; Marketing-Name nicht nötig.
    if arch == "arm64" and (not chip or chip == "arm"):
        chip = "Apple Silicon"

    return {
        "os": platform.system() or "?",
        "arch": arch,
        "chip": chip,
        "cores": os.cpu_count() or 1,
        "ram_gb": ram_gb,
    }


def recommend(system: dict, installed: list[str] | tuple[str, ...] = ()) -> str | None:
    """Das am besten zu Postfach passende Modell, das auf DIESEM System läuft.

    Unter den lauffähigen gewinnt der höchste Fit; bei Gleichstand das kleinere
    (schneller/genügsamer). Bereits installierte Modelle bekommen einen kleinen
    Bonus, damit die Empfehlung nicht ohne Not einen großen Download verlangt,
    wenn schon etwas fast Gleichwertiges da ist.
    """
    ram = float(system.get("ram_gb") or 0)
    runnable = [m for m in CATALOG if m.min_ram_gb <= ram] if ram else list(CATALOG)
    if not runnable:
        # RAM kleiner als alles im Katalog → das genügsamste anbieten.
        runnable = [min(CATALOG, key=lambda m: m.min_ram_gb)]

    inst = set(installed)

    def score(m: ModelSpec) -> tuple[int, int]:
        bonus = 4 if m.id in inst else 0
        # Sekundär: kleineres Modell bevorzugen (negatives size als Tie-Break).
        return (m.fit + bonus, -int(m.size_gb * 10))

    return max(runnable, key=score).id


def annotate(system: dict, installed: list[str] | tuple[str, ...] = ()) -> list[dict]:
    """Katalog fürs Frontend: pro Modell runs/installed/recommended + Metadaten."""
    ram = float(system.get("ram_gb") or 0)
    inst = set(installed)
    rec = recommend(system, installed)
    rows: list[dict] = []
    for m in CATALOG:
        rows.append(
            {
                "id": m.id,
                "label": m.label,
                "params": m.params,
                "size_gb": m.size_gb,
                "min_ram_gb": m.min_ram_gb,
                "role": m.role,
                "strengths": list(m.strengths),
                "note": m.note,
                "fit": m.fit,
                "runs": (m.min_ram_gb <= ram) if ram else True,
                "installed": m.id in inst,
                "recommended": m.id == rec,
            }
        )
    return rows
