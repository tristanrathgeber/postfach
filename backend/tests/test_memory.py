from postfach.memory import FakeEmbedder, MailMemory


def _entry(uid, subject="Betreff", folder="INBOX"):
    return {
        "account": "gmx", "folder": folder, "uid": uid,
        "subject": subject, "from_name": "Alice", "from_addr": "a@b.de",
        "date": "2026-07-20T10:00:00+02:00", "snippet": f"Inhalt {subject}",
    }


def test_upsert_and_count(tmp_path):
    memory = MailMemory(tmp_path / "memory.db", FakeEmbedder())
    memory.upsert_many([_entry(1), _entry(2)])
    assert memory.count("gmx") == 2
    memory.upsert_many([_entry(1, subject="Neu")])  # idempotent: gleiche Mail ersetzt
    assert memory.count("gmx") == 2


def test_search_finds_semantically_matching_entry(tmp_path):
    # FakeEmbedder bildet Wort-Overlap ab → "Rechnung" matcht die Rechnungs-Mail
    memory = MailMemory(tmp_path / "memory.db", FakeEmbedder())
    memory.upsert_many([
        _entry(1, subject="Ihre Telekom Rechnung Juli"),
        _entry(2, subject="Training am Samstag"),
        _entry(3, subject="Newsletter Sommertrends"),
    ])
    results = memory.search("gmx", "Was kostet die Telekom Rechnung?", k=2)
    assert results
    assert results[0]["uid"] == 1
    assert len(results) <= 2


def test_embed_text_sanitizes_control_characters(tmp_path):
    # Mail-Bodies enthalten gern Steuerzeichen — die dürfen nie zu Ollama.
    memory = MailMemory(tmp_path / "m.db", FakeEmbedder())
    entry = _entry(1, subject="Mit \x00 Null und \x1b Escape")
    entry["snippet"] = "Inhalt\x07mit\x0cKontrollzeichen"
    memory.upsert_many([entry])  # darf nicht crashen
    text = MailMemory._embed_text(entry)
    assert "\x00" not in text and "\x1b" not in text and "\x07" not in text


def test_ollama_embedder_falls_back_to_single_texts_on_chunk_error(monkeypatch):
    # Lehnt Ollama einen Chunk ab (400), einzeln erneut versuchen und nur den
    # tatsächlich kaputten Text durch einen Platzhalter-Vektor ersetzen.
    import httpx as httpx_mod

    import postfach.memory as memory_mod
    from postfach.memory import OllamaEmbedder

    class FakeResponse:
        def __init__(self, texts, fail):
            self._texts, self._fail = texts, fail

        def raise_for_status(self):
            if self._fail:
                raise httpx_mod.HTTPStatusError("400", request=None, response=None)

        def json(self):
            return {"embeddings": [[1.0] * 4 for _ in self._texts]}

    def fake_post(url, json=None, timeout=None):
        texts = json["input"]
        return FakeResponse(texts, fail="BÖSE" in texts)

    monkeypatch.setattr(memory_mod.httpx, "post", fake_post)
    result = OllamaEmbedder("all-minilm").embed(["gut", "BÖSE", "auch gut"])
    assert len(result) == 3
    assert result[0] == [1.0] * 4
    assert result[1] == [0.0] * len(result[0])  # Platzhalter statt Crash
    assert result[2] == [1.0] * 4


def test_ollama_embedder_chunks_large_batches(monkeypatch):
    # Ollama lehnt sehr große Embed-Batches ab (400) → in 64er-Chunks anfragen.
    import postfach.memory as memory_mod
    from postfach.memory import OllamaEmbedder

    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"embeddings": [[0.0] * 4] * len(calls[-1])}

    def fake_post(url, json=None, timeout=None):
        calls.append(json["input"])
        return FakeResponse()

    monkeypatch.setattr(memory_mod.httpx, "post", fake_post)
    result = OllamaEmbedder("all-minilm").embed([f"text {i}" for i in range(150)])
    assert len(result) == 150
    assert len(calls) == 3
    assert all(len(batch) <= 64 for batch in calls)


def test_search_hybrid_lexical_boost_finds_exact_names(tmp_path):
    # Embeddings (klein, englisch-lastig) verfehlen deutsche Namen — der
    # lexikalische Bonus muss wörtliche Treffer in Betreff/Absender hochziehen.
    class ConstantEmbedder:
        def embed(self, texts):
            return [[1.0, 0.0, 0.0] for _ in texts]  # alle Vektoren identisch

    memory = MailMemory(tmp_path / "m.db", ConstantEmbedder())
    memory.upsert_many([
        _entry(1, subject="Ihre Reise für Ronny Weippert am 25.08."),
        _entry(2, subject="Newsletter Sommertrends"),
        _entry(3, subject="Rechnung Juli"),
    ])
    results = memory.search("gmx", "Wann ist die Reise für Ronny Weippert?", k=2)
    assert results
    assert results[0]["uid"] == 1


def test_search_scoped_per_account(tmp_path):
    memory = MailMemory(tmp_path / "memory.db", FakeEmbedder())
    memory.upsert_many([_entry(1)])
    assert memory.search("anderes-konto", "Betreff", k=3) == []
