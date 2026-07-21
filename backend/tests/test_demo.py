from postfach.demo import DemoMailbox, demo_classify


def test_demo_inbox_has_varied_sample_mails():
    box = DemoMailbox()
    mails = box.list_messages("INBOX", limit=50)
    assert len(mails) >= 10
    assert any(m.body_html_raw and "http" in m.body_html_raw for m in mails)  # Remote-Bild-Fall
    assert any(m.attachments for m in mails)
    assert any(not m.seen for m in mails)


def test_demo_actions_mutate_folders():
    box = DemoMailbox()
    [first, *_] = box.list_messages("INBOX", limit=50)
    box.trash("INBOX", first.uid)
    assert first.uid not in [m.uid for m in box.list_messages("INBOX", limit=50)]
    assert first.uid in [m.uid for m in box.list_messages("Papierkorb", limit=50)]


def test_demo_set_seen_toggles():
    box = DemoMailbox()
    unread = [m for m in box.list_messages("INBOX", limit=50) if not m.seen][0]
    box.set_seen("INBOX", unread.uid, True)
    updated = box.get_message("INBOX", unread.uid)
    assert updated.seen is True


def test_demo_search_matches_subject_and_body():
    box = DemoMailbox()
    results = box.search("INBOX", "Rechnung")
    assert results
    assert all(
        "rechnung" in (m.subject + m.body_text).lower() for m in results
    )


def test_demo_append_sent_lands_in_gesendet():
    box = DemoMailbox()
    before = len(box.list_messages("Gesendet", limit=100))
    box.append_sent(
        b"From: t@demo.example\r\nTo: a@b.de\r\nSubject: Test\r\n\r\nHallo"
    )
    assert len(box.list_messages("Gesendet", limit=100)) == before + 1


def test_demo_classifier_is_deterministic_and_covers_categories():
    box = DemoMailbox()
    mails = box.list_messages("INBOX", limit=50)
    result = demo_classify(mails)
    assert set(result) == {m.uid for m in mails}
    categories = {r["category"] for r in result.values()}
    assert "Newsletter" in categories
    assert "Aktion-nötig" in categories
    assert result == demo_classify(mails)  # deterministisch


def test_demo_get_attachment_files_bulk():
    # Pendant zur Mailbox-Bulk-API: ein Fetch liefert alle Anhänge (Send-Pfad).
    box = DemoMailbox()
    files = box.get_attachment_files("INBOX", 109)
    assert [f.filename for f in files] == ["Rechnung Juli 39,95€.pdf"]
    assert files[0].payload
