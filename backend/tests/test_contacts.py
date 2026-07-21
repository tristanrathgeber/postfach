"""Kontakte-Ernte aus dem Mailbestand (memory.db) + Ranking."""

from postfach.demo import DemoMailbox
from postfach.emilia import EmiliaService
from postfach.memory import FakeEmbedder, MailMemory


def _memory(tmp_path):
    return MailMemory(tmp_path / "m.db", FakeEmbedder())


def test_index_harvests_senders_and_recipients(tmp_path):
    memory = _memory(tmp_path)
    EmiliaService(None, memory).index("demo", DemoMailbox())
    results = memory.search_contacts("mart")
    assert any(c["addr"] == "m.becker@web.example" for c in results)


def test_contact_search_matches_name_and_addr_prefix(tmp_path):
    memory = _memory(tmp_path)
    EmiliaService(None, memory).index("demo", DemoMailbox())
    by_name = memory.search_contacts("becker")
    by_addr = memory.search_contacts("m.becker@")
    assert by_name and by_addr
    assert by_name[0]["addr"] == by_addr[0]["addr"]


def test_sent_recipients_rank_higher_than_one_time_senders(tmp_path):
    # Martin bekommt Post von uns (Gesendet) → muss vor gleichnamigen Einmal-Absendern liegen
    memory = _memory(tmp_path)
    EmiliaService(None, memory).index("demo", DemoMailbox())
    results = memory.search_contacts("m")
    addrs = [c["addr"] for c in results]
    assert "m.becker@web.example" in addrs[:3]


def test_contact_search_limit(tmp_path):
    memory = _memory(tmp_path)
    EmiliaService(None, memory).index("demo", DemoMailbox())
    assert len(memory.search_contacts("e", limit=3)) <= 3


def test_name_search_matches_uppercase_umlauts(tmp_path):
    # SQLites LOWER() foldet nur ASCII — "MÜLLER" muss trotzdem via "müller" gefunden werden.
    memory = _memory(tmp_path)
    memory.upsert_contacts([("MÜLLER GMBH", "kontakt@mueller.example", 1.0, "2026-07-01")])
    assert memory.search_contacts("müller")


def test_noreply_variants_are_filtered(tmp_path):
    memory = _memory(tmp_path)
    memory.upsert_contacts([
        ("", "no_reply@shop.example", 1.0, "2026-07-01"),
        ("", "do-not-reply@shop.example", 1.0, "2026-07-01"),
        ("", "donotreply@shop.example", 1.0, "2026-07-01"),
        ("", "bounce@shop.example", 1.0, "2026-07-01"),
        ("", "postmaster@shop.example", 1.0, "2026-07-01"),
        ("Echt", "echt@shop.example", 1.0, "2026-07-01"),
    ])
    addrs = [c["addr"] for c in memory.search_contacts("shop.example", limit=20)]
    assert addrs == ["echt@shop.example"]


def test_owner_address_is_not_harvested(tmp_path):
    memory = _memory(tmp_path)
    box = DemoMailbox()
    EmiliaService(None, memory).index_mails(
        "demo", "INBOX", box.list_messages("INBOX", 100), owner_addr="alex@demo.example",
    )
    addrs = [c["addr"] for c in memory.search_contacts("demo.example", limit=20)]
    assert "alex@demo.example" not in addrs


def test_sent_detection_uses_shared_folder_names(tmp_path):
    # "Gesendete Elemente" (Outlook-Deutsch) muss als Sent-Ordner zählen —
    # Erkennung kommt aus mail_imap, nicht aus einer Emilia-Kopie.
    from postfach.mail_imap import is_sent_folder

    assert is_sent_folder("Gesendete Elemente")
    assert is_sent_folder("INBOX/Gesendet")
    assert not is_sent_folder("INBOX")
