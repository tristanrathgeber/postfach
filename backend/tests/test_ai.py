import json

from postfach.ai import AiService
from postfach.demo import DemoMailbox
from email_agent.config import Config as AgentConfig


class FakeBackend:
    def __init__(self):
        self.calls = 0

    def complete(self, system, prompt, purpose):
        self.calls += 1
        if purpose == "draft":
            return "Hi!\n\nPasst.\n\nVG\nTristan"
        import re

        uids = [int(u) for u in re.findall(r"uid=(\d+)", prompt)]
        items = [
            {
                "uid": u,
                "category": "Rechnungen",
                "is_newsletter": False,
                "interesting": False,
                "needs_reply": False,
                "confidence": 0.9,
                "reason": "Test",
            }
            for u in uids
        ]
        return json.dumps(items)


def _mails(n=2):
    return DemoMailbox().list_messages("INBOX", limit=n)


def test_classify_caches_results(tmp_path):
    backend = FakeBackend()
    service = AiService(AgentConfig(), backend, cache_path=tmp_path / "classify.json", style_path=tmp_path / "s.md")
    mails = _mails(2)
    first = service.classify("demo", "INBOX", mails)
    assert backend.calls == 1
    assert first[mails[0].uid]["category"] == "Rechnungen"

    second = service.classify("demo", "INBOX", mails)
    assert backend.calls == 1  # alles aus dem Cache
    assert second == first
    assert (tmp_path / "classify.json").exists()


def test_classify_cache_is_per_account(tmp_path):
    backend = FakeBackend()
    service = AiService(AgentConfig(), backend, cache_path=tmp_path / "c.json", style_path=tmp_path / "s.md")
    mails = _mails(1)
    service.classify("konto-a", "INBOX", mails)
    service.classify("konto-b", "INBOX", mails)
    assert backend.calls == 2


def test_classify_cache_is_per_folder(tmp_path):
    # IMAP-UIDs sind nur pro Ordner eindeutig — uid 1 in INBOX ≠ uid 1 in Gesendet.
    backend = FakeBackend()
    service = AiService(AgentConfig(), backend, cache_path=tmp_path / "c.json", style_path=tmp_path / "s.md")
    mails = _mails(1)
    service.classify("konto", "INBOX", mails)
    service.classify("konto", "Gesendet", mails)
    assert backend.calls == 2
    assert service.cached_categories("konto", "INBOX", [mails[0].uid])
    assert not service.cached_categories("konto", "Papierkorb", [mails[0].uid])


def test_draft_uses_style_and_returns_text(tmp_path):
    (tmp_path / "s.md").write_text("STIL: locker", encoding="utf-8")
    service = AiService(AgentConfig(), FakeBackend(), cache_path=tmp_path / "c.json", style_path=tmp_path / "s.md")
    text = service.draft(_mails(1)[0])
    assert text.startswith("Hi!")
