"""Emilia II: Streaming, NL-Suche, Sie/Du/Ton, Thread-Zusammenfassung, KI-Schalter."""

import json

import pytest

from postfach.emilia import EmiliaService


class _StreamLLM:
    """Fake mit Streaming — zeichnet Prompts auf."""

    def __init__(self):
        self.calls = []

    def complete(self, system, prompt, purpose):
        self.calls.append((purpose, system, prompt))
        return f"[{purpose}] ok"

    def stream(self, system, prompt, purpose):
        self.calls.append((purpose, system, prompt))
        yield "Hallo "
        yield "Welt"


class _CompleteOnlyLLM:
    def complete(self, system, prompt, purpose):
        return "Ein Rutsch"


class _NoMemory:
    def search(self, account, q, k=6):
        return []

    def upsert_many(self, entries):
        pass

    def upsert_contacts(self, contacts):
        pass


# --- Streaming ---


def test_chat_stream_yields_sources_deltas_done():
    svc = EmiliaService(_StreamLLM(), _NoMemory(), owner="Tester")
    events = list(svc.chat_stream("acc", "Wie war das mit dem Schlüssel?"))
    assert events[0] == {"sources": []}
    assert {"delta": "Hallo "} in events and {"delta": "Welt"} in events
    assert events[-1] == {"done": True}


def test_chat_stream_falls_back_to_complete():
    svc = EmiliaService(_CompleteOnlyLLM(), _NoMemory())
    events = list(svc.chat_stream("acc", "Frage"))
    assert {"delta": "Ein Rutsch"} in events
    assert events[-1] == {"done": True}


# --- Sie/Du/Ton ---


def test_improve_new_modes_use_distinct_prompts():
    llm = _StreamLLM()
    svc = EmiliaService(llm, _NoMemory())
    for mode in ("sie", "du", "kuerzer"):
        svc.improve("Hallo, wie geht es dir?", mode)
    systems = [c[1] for c in llm.calls]
    assert len(set(systems)) == 3
    assert any("Sie" in s for s in systems)
    assert any("Du" in s for s in systems)
    assert any("kürz" in s.lower() for s in systems)


# --- API (Demo) ---


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from postfach.app import create_app

    c = TestClient(create_app(root=tmp_path, demo=True))
    c.put("/api/settings", json={"undo_seconds": 0})
    return c


def test_stream_route_is_ndjson(client):
    with client.stream("POST", "/api/emilia/chat/stream",
                       json={"account": "demo", "message": "Was war mit dem Vereinsheim?"}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/x-ndjson")
        events = [json.loads(line) for line in r.iter_lines() if line]
    assert "sources" in events[0]
    assert any("delta" in e for e in events)
    assert events[-1] == {"done": True}


def test_nl_search_translates_and_searches(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    r = client.get("/api/search/nl", params={"account": "demo", "q": "rechnungen von telekom mit anhang"})
    data = r.json()
    assert "von:telekom" in data["query"] and "hat:anhang" in data["query"]
    assert any("Telekom" in h["subject"] for h in data["hits"])


def test_nl_search_needs_ready_index(client):
    r = client.get("/api/search/nl", params={"account": "demo", "q": "irgendwas"})
    assert r.status_code == 409


def test_thread_summary_on_demand(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    r = client.post("/api/emilia/thread_summary",
                    json={"account": "demo", "folder": "INBOX", "uid": 114})
    data = r.json()
    assert r.status_code == 200
    assert data["mails"] == 3  # Frage + Antwort + Dank im Demo-Faden
    assert data["summary"].strip()


def test_thread_summary_404_without_thread(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    r = client.post("/api/emilia/thread_summary",
                    json={"account": "demo", "folder": "INBOX", "uid": 99999})
    assert r.status_code == 404


# --- KI-Aus-Schalter ---


def test_ai_disabled_gates_all_ai_routes(client):
    client.post("/api/emilia/index", json={"account": "demo"})
    client.put("/api/settings", json={"ai_enabled": False})
    assert client.get("/api/settings").json()["ai_enabled"] is False

    gated = [
        ("post", "/api/classify", {"account": "demo", "folder": "INBOX", "uids": [114]}),
        ("post", "/api/draft", {"account": "demo", "folder": "INBOX", "uid": 114}),
        ("post", "/api/emilia/chat", {"account": "demo", "message": "hi"}),
        ("post", "/api/emilia/improve", {"text": "abc", "mode": "korrigieren"}),
        ("post", "/api/emilia/thread_summary", {"account": "demo", "folder": "INBOX", "uid": 114}),
    ]
    for method, path, body in gated:
        r = getattr(client, method)(path, json=body)
        assert r.status_code == 403, f"{path} -> {r.status_code}"
    assert client.get("/api/search/nl", params={"account": "demo", "q": "x"}).status_code == 403
    with client.stream("POST", "/api/emilia/chat/stream",
                       json={"account": "demo", "message": "hi"}) as r:
        assert r.status_code == 403

    # Nicht-KI bleibt: normale Suche, Nachrichtenliste, Kategorie-Cache lesbar
    assert client.get("/api/search", params={"account": "demo", "q": "Telekom"}).status_code == 200
    assert client.get("/api/messages", params={"account": "demo"}).status_code == 200
    # Nutzer-Korrektur ist KEINE KI-Aktion — bleibt erlaubt
    r = client.post("/api/classify/override",
                    json={"account": "demo", "folder": "INBOX", "uid": 114, "category": "Verein"})
    assert r.status_code == 200


def test_ai_disabled_index_skips_embeddings_keeps_search(client):
    client.put("/api/settings", json={"ai_enabled": False})
    client.post("/api/emilia/index", json={"account": "demo"})
    assert client.get("/api/emilia/status").json()["indexed_mails"] == 0
    assert client.get("/api/search/status", params={"account": "demo"}).json()["ready"] is True


def test_settings_partial_update_keeps_ai_enabled(client):
    client.put("/api/settings", json={"ai_enabled": False})
    client.put("/api/settings", json={"undo_seconds": 10})  # Teil-Update ohne ai_enabled
    assert client.get("/api/settings").json()["ai_enabled"] is False


# --- Review-Härtung (Batch-7-Review) ---


def test_llm_down_returns_502_not_500(client):
    """Ollama weg (LLMError) → lesbarer 502 auf allen LLM-Routen."""
    from email_agent.llm.base import LLMError

    client.post("/api/emilia/index", json={"account": "demo"})

    def boom(system, prompt, purpose):
        raise LLMError("Ollama nicht erreichbar: alles kaputt")

    client.app.state.emilia._llm.complete = boom
    assert client.get("/api/search/nl", params={"account": "demo", "q": "telekom"}).status_code == 502
    assert client.post("/api/emilia/thread_summary",
                       json={"account": "demo", "folder": "INBOX", "uid": 114}).status_code == 502
    assert client.post("/api/emilia/improve",
                       json={"text": "abc", "mode": "korrigieren"}).status_code == 502
    assert client.post("/api/emilia/chat",
                       json={"account": "demo", "message": "hi"}).status_code == 502


def test_thread_texts_keeps_newest_mails():
    """30er-Deckel darf nicht ausgerechnet die NEUESTEN Mails verwerfen."""
    from dataclasses import replace

    from postfach.demo import _mail
    from postfach.search import SearchIndex
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        index = SearchIndex(Path(tmp) / "s.db")
        mails = [
            replace(_mail(i, "Langer Faden", "P", "p@x.de", f"Beitrag {i}"),
                    references="<root@x.de>" if i > 1 else "",
                    date_iso=f"2026-07-01T10:{i:02d}:00")
            for i in range(1, 36)
        ]
        mails[0] = replace(mails[0], message_id="<root@x.de>")
        index.add_mails("demo", "INBOX", mails)
        texts = index.thread_texts("demo", "<root@x.de>")
        assert len(texts) == 30
        bodies = [t["body"] for t in texts]
        assert "Beitrag 35" in bodies[-1] or any("Beitrag 35" in b for b in bodies)  # neueste dabei
        dates = [t["date"] for t in texts]
        assert dates == sorted(dates)  # chronologisch aufsteigend


def test_translate_search_survives_llm_chatter():
    """Erklärzeilen und Markdown-Fences des Modells dürfen die Query nicht fressen."""
    from postfach.emilia import EmiliaService

    class ChattyLLM:
        def __init__(self, out):
            self.out = out

        def complete(self, system, prompt, purpose):
            return self.out

    class NoMem:
        def search(self, *a, **k):
            return []

    svc = EmiliaService(ChattyLLM("Hier ist die Suchquery:\nvon:hetzner nach:2026-06-21"), NoMem())
    assert svc.translate_search("rechnungen von hetzner", "2026-07-21") == "von:hetzner nach:2026-06-21"

    svc = EmiliaService(ChattyLLM("```\nvon:martin hat:anhang\n```"), NoMem())
    assert svc.translate_search("anhänge von martin", "2026-07-21") == "von:martin hat:anhang"

    svc = EmiliaService(ChattyLLM(""), NoMem())
    assert svc.translate_search("telekom rechnung", "2026-07-21") == "telekom rechnung"

    # „Thinking"-Modelle (qwen3 &c.) klammern ihren Gedankengang in <think>…</think>;
    # der darf NICHT als Query landen — nur die echte Operator-Zeile zählt.
    thinking = "<think>\nDer Nutzer will Rechnungen. Also von:hetzner...\n</think>\nvon:hetzner"
    svc = EmiliaService(ChattyLLM(thinking), NoMem())
    assert svc.translate_search("rechnungen von hetzner", "2026-07-21") == "von:hetzner"
