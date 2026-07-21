"""Cookbook / Modell-Assistent: Systemscan, Katalog, Empfehlung.

Die Empfehlung ist deterministisch: unter den Modellen, die auf dem System
LAUFEN würden, gewinnt das mit dem höchsten Postfach-Fit — nicht das größte.
"""

from __future__ import annotations

from postfach import cookbook


def _system(ram_gb: float, arch: str = "arm64") -> dict:
    return {"ram_gb": ram_gb, "arch": arch, "chip": "Apple M-Test", "cores": 8, "os": "Darwin"}


def test_scan_system_reports_ram_arch_and_cores():
    s = cookbook.scan_system()
    assert s["ram_gb"] > 0
    assert isinstance(s["cores"], int) and s["cores"] >= 1
    assert isinstance(s["arch"], str) and s["arch"]


def test_catalog_entries_are_well_formed():
    ids = [m.id for m in cookbook.CATALOG]
    assert len(ids) == len(set(ids)), "Modell-IDs müssen eindeutig sein"
    for m in cookbook.CATALOG:
        assert m.size_gb > 0 and m.min_ram_gb > 0
        assert 0 <= m.fit <= 100
        assert m.strengths, f"{m.id} braucht mindestens eine Stärke"


def test_recommend_picks_product_sweetspot_not_biggest_on_large_machine():
    # 32 GB: sowohl 7b als auch 14b laufen — empfohlen wird der Produkt-Sweetspot
    # (qwen2.5:7b), nicht das langsamere 14b.
    rec = cookbook.recommend(_system(32))
    assert rec == "qwen2.5:7b"


def test_recommend_steps_down_on_small_machine():
    # 8 GB: 7b (min 12) läuft nicht mehr → kleineres, passendes Modell.
    rec = cookbook.recommend(_system(8))
    spec = {m.id: m for m in cookbook.CATALOG}[rec]
    assert spec.min_ram_gb <= 8
    # und es ist das beste unter den lauffähigen
    runnable = [m for m in cookbook.CATALOG if m.min_ram_gb <= 8]
    assert spec.fit == max(m.fit for m in runnable)


def test_recommend_returns_most_frugal_when_ram_below_everything():
    # 4 GB liegt unter dem Boden jedes Modells → das genügsamste anbieten,
    # statt gar nichts (ehrliche „geht knapp"-Empfehlung).
    rec = cookbook.recommend(_system(4))
    spec = {m.id: m for m in cookbook.CATALOG}[rec]
    assert spec.min_ram_gb == min(m.min_ram_gb for m in cookbook.CATALOG)


def test_annotate_marks_runs_and_installed():
    rows = cookbook.annotate(_system(16), installed=["qwen2.5:7b"])
    by_id = {r["id"]: r for r in rows}
    assert by_id["qwen2.5:7b"]["installed"] is True
    assert by_id["qwen2.5:7b"]["runs"] is True
    # 14b braucht mehr als 16 GB → läuft nicht
    assert by_id["qwen2.5:14b"]["runs"] is False
    assert by_id["qwen2.5:14b"]["installed"] is False


def test_annotate_flags_the_recommendation():
    rows = cookbook.annotate(_system(32), installed=[])
    recommended = [r for r in rows if r["recommended"]]
    assert [r["id"] for r in recommended] == ["qwen2.5:7b"]


def test_installed_but_unfit_still_runnable_if_ram_allows():
    # Ein bereits installiertes, kleines Modell bleibt nutzbar (runs=True),
    # auch wenn es nicht die Empfehlung ist.
    rows = cookbook.annotate(_system(16), installed=["llama3.2:3b"])
    by_id = {r["id"]: r for r in rows}
    assert by_id["llama3.2:3b"]["runs"] is True
    assert by_id["llama3.2:3b"]["recommended"] is False


# --- API-Endpunkte -----------------------------------------------------------


def _demo_client(tmp_path):
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    return TestClient(create_app(root=tmp_path, demo=True))


def test_cookbook_overview_returns_system_and_catalog(tmp_path):
    c = _demo_client(tmp_path)
    r = c.get("/api/cookbook")
    assert r.status_code == 200
    data = r.json()
    assert data["system"]["ram_gb"] >= 0
    assert data["demo"] is True
    assert any(row["recommended"] for row in data["catalog"])
    assert data["recommended"] in {m.id for m in cookbook.CATALOG}


def test_cookbook_pull_and_activate_blocked_in_demo(tmp_path):
    c = _demo_client(tmp_path)
    assert c.post("/api/cookbook/pull", json={"model": "qwen2.5:7b"}).status_code == 403
    assert c.post("/api/cookbook/activate", json={"model": "qwen2.5:7b"}).status_code == 403


def test_cookbook_activate_persists_and_hot_swaps(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import yaml

    from postfach import api
    from postfach.app import create_app

    # Ollama meldet das Modell als installiert.
    monkeypatch.setattr(api, "_ollama_tags", lambda base: (True, ["qwen2.5:7b"]))
    app = create_app(root=tmp_path, demo=False, mailbox_factory=lambda account: None)
    c = TestClient(app)

    r = c.post("/api/cookbook/activate", json={"model": "qwen2.5:7b"})
    assert r.status_code == 200 and r.json()["active_model"] == "qwen2.5:7b"

    # 1) persistiert
    cfg_yaml = yaml.safe_load((tmp_path / "config" / "config.yaml").read_text(encoding="utf-8"))
    assert cfg_yaml["emilia"]["model"] == "qwen2.5:7b"
    # 2) laufende Instanz umgeschaltet (geteilt mit Emilia + Sortieren/Entwerfen)
    assert app.state.local_llm._model == "qwen2.5:7b"
    assert app.state.config.emilia.model == "qwen2.5:7b"


def test_cookbook_activate_rejects_unknown_and_uninstalled(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from postfach import api
    from postfach.app import create_app

    app = create_app(root=tmp_path, demo=False, mailbox_factory=lambda account: None)
    c = TestClient(app)

    assert c.post("/api/cookbook/activate", json={"model": "nope:99b"}).status_code == 400

    # Ollama erreichbar, Modell NICHT installiert → 409
    monkeypatch.setattr(api, "_ollama_tags", lambda base: (True, ["llama3.2:3b"]))
    assert c.post("/api/cookbook/activate", json={"model": "qwen2.5:7b"}).status_code == 409
