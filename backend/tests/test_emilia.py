from postfach.demo import DemoMailbox
from postfach.emilia import EmiliaService
from postfach.memory import FakeEmbedder, MailMemory


class FakeChatLLM:
    def __init__(self, reply="Die Telekom-Rechnung beträgt 39,95 €."):
        self.reply = reply
        self.calls = []

    def complete(self, system, prompt, purpose):
        self.calls.append((system, prompt, purpose))
        return self.reply


def _service(tmp_path, llm=None):
    memory = MailMemory(tmp_path / "m.db", FakeEmbedder())
    return EmiliaService(llm or FakeChatLLM(), memory), memory


def test_index_walks_mailbox_folders(tmp_path):
    service, memory = _service(tmp_path)
    box = DemoMailbox()
    indexed = service.index("demo", box)
    assert indexed >= 12  # Demo-Inbox + Gesendet
    assert memory.count("demo") == indexed
    # idempotent
    assert service.index("demo", box) == indexed


def test_chat_uses_memory_and_returns_sources(tmp_path):
    service, memory = _service(tmp_path)
    service.index("demo", DemoMailbox())
    llm = FakeChatLLM()
    service._llm = llm  # noqa: SLF001 — Test greift bewusst auf das Fake zu
    result = service.chat("demo", "Was steht in der Telekom Rechnung?")
    assert result["reply"].startswith("Die Telekom-Rechnung")
    assert result["sources"]
    assert any("Telekom" in s["subject"] for s in result["sources"])
    [(system, prompt, _)] = llm.calls
    assert "DATEN" in system  # Injection-Guard
    assert "Telekom" in prompt  # Gedächtnis-Kontext im Prompt


def test_chat_includes_open_mail_context(tmp_path):
    service, _ = _service(tmp_path)
    box = DemoMailbox()
    service.index("demo", box)
    llm = FakeChatLLM("Martin fragt wegen Samstag.")
    service._llm = llm
    service.chat("demo", "Worum geht es hier?", context_mail=box.get_message("INBOX", 110))
    [(_, prompt, _)] = llm.calls
    assert "Training am Samstag" in prompt


def test_improve_modes(tmp_path):
    llm = FakeChatLLM("Ich habe die Rechnung erhalten.")
    service, _ = _service(tmp_path, llm)
    korrigiert = service.improve("Ich habe die Rechung erhalten.", "korrigieren")
    assert korrigiert == "Ich habe die Rechnung erhalten."
    [(system1, _, _)] = llm.calls
    assert "NUR" in system1 and "Rechtschreib" in system1

    llm.calls.clear()
    service.improve("Text.", "verbessern")
    [(system2, _, _)] = llm.calls
    assert "Stil" in system2
