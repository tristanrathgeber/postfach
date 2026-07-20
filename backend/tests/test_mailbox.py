from postfach.mail_imap import Mailbox

MULTIPART = (
    b"Message-ID: <m1@example.com>\r\n"
    b"From: Alice Example <alice@example.com>\r\n"
    b"To: t@meinedomain.de\r\n"
    b"Cc: bob@example.com\r\n"
    b"Subject: =?utf-8?q?Gr=C3=BC=C3=9Fe?=\r\n"
    b"Date: Sat, 19 Jul 2026 10:00:00 +0200\r\n"
    b"Content-Type: multipart/mixed; boundary=OUTER\r\n"
    b"\r\n"
    b"--OUTER\r\n"
    b"Content-Type: multipart/alternative; boundary=INNER\r\n"
    b"\r\n"
    b"--INNER\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n"
    b"\r\n"
    b"Hallo Klartext\r\n"
    b"--INNER\r\n"
    b"Content-Type: text/html; charset=utf-8\r\n"
    b"\r\n"
    b"<p>Hallo <b>HTML</b></p>\r\n"
    b"--INNER--\r\n"
    b"--OUTER\r\n"
    b"Content-Type: application/pdf\r\n"
    b"Content-Disposition: attachment; filename=\"rechnung.pdf\"\r\n"
    b"Content-Transfer-Encoding: base64\r\n"
    b"\r\n"
    b"JVBERi0=\r\n"
    b"--OUTER--\r\n"
)


class FakeIMAP:
    def __init__(self, folders=("INBOX", "Gesendet", "Papierkorb"), fetch_result=None, search_result=(1,)):
        self.folders = list(folders)
        self.fetch_result = fetch_result or {1: {b"BODY[]": MULTIPART, b"FLAGS": (b"\\Seen",)}}
        self.search_result = list(search_result)
        self.calls = []

    def select_folder(self, name, readonly=False):
        self.calls.append(("select", name, readonly))
        return {}

    def search(self, criteria, charset=None):
        self.calls.append(("search", criteria, charset))
        return list(self.search_result)

    def fetch(self, uids, data):
        self.calls.append(("fetch", tuple(uids), tuple(data)))
        return {u: self.fetch_result[u] for u in uids if u in self.fetch_result}

    def list_folders(self):
        return [((b"\\HasNoChildren",), b"/", name) for name in self.folders]

    def find_special_folder(self, flag):
        return None

    def create_folder(self, name):
        self.calls.append(("create", name))
        self.folders.append(name)

    def move(self, uids, folder):
        self.calls.append(("move", tuple(uids), folder))

    def add_flags(self, uids, flags, silent=False):
        self.calls.append(("add_flags", tuple(uids), tuple(flags)))

    def remove_flags(self, uids, flags, silent=False):
        self.calls.append(("remove_flags", tuple(uids), tuple(flags)))

    def append(self, folder, msg, flags=()):
        self.calls.append(("append", folder, msg, tuple(flags)))

    def logout(self):
        pass


def test_list_messages_parses_summary_fields():
    box = Mailbox(FakeIMAP())
    [mail] = box.list_messages("INBOX", limit=50)
    assert mail.uid == 1
    assert mail.subject == "Grüße"
    assert mail.from_name == "Alice Example"
    assert mail.seen is True
    assert mail.date_iso.startswith("2026-07-19T10:00:00")
    assert "Hallo Klartext" in mail.body_text
    assert mail.body_html_raw and "<b>HTML</b>" in mail.body_html_raw
    assert [a.filename for a in mail.attachments] == ["rechnung.pdf"]
    assert mail.cc == ("bob@example.com",)
    assert mail.headers.get("message-id") == "<m1@example.com>"


def test_list_messages_newest_first_with_limit():
    fetch = {u: {b"BODY[]": MULTIPART, b"FLAGS": ()} for u in (1, 2, 3)}
    fake = FakeIMAP(fetch_result=fetch, search_result=(1, 2, 3))
    mails = Mailbox(fake).list_messages("INBOX", limit=2)
    assert [m.uid for m in mails] == [3, 2]
    assert mails[0].seen is False


def test_get_attachment_returns_bytes_and_meta():
    box = Mailbox(FakeIMAP())
    att = box.get_attachment("INBOX", 1, 0)
    assert att.filename == "rechnung.pdf"
    assert att.content_type == "application/pdf"
    assert att.payload == b"%PDF-"


def test_get_messages_fetches_only_requested_uids():
    fetch = {u: {b"BODY[]": MULTIPART, b"FLAGS": ()} for u in (1, 2, 3)}
    fake = FakeIMAP(fetch_result=fetch)
    mails = Mailbox(fake).get_messages("INBOX", [3, 1])
    assert sorted(m.uid for m in mails) == [1, 3]
    fetch_calls = [c for c in fake.calls if c[0] == "fetch"]
    assert fetch_calls[0][1] == (1, 3)  # nur die angefragten UIDs, kein Volllisting


def test_exists_uses_cheap_uid_search():
    fake = FakeIMAP(search_result=(7,))
    box = Mailbox(fake)
    assert box.exists("INBOX", 7) is True
    fake.search_result = []
    assert box.exists("INBOX", 8) is False
    assert not [c for c in fake.calls if c[0] == "fetch"]  # kein Body-Download


def test_move_with_ensure_creates_missing_folder():
    fake = FakeIMAP()
    Mailbox(fake).move("INBOX", 1, "AI/Rechnungen", ensure=True)
    assert ("create", "AI/Rechnungen") in fake.calls
    assert ("move", (1,), "AI/Rechnungen") in fake.calls


def test_set_seen_adds_and_removes_flag():
    fake = FakeIMAP()
    box = Mailbox(fake)
    box.set_seen("INBOX", 1, True)
    box.set_seen("INBOX", 1, False)
    assert ("add_flags", (1,), (b"\\Seen",)) in fake.calls
    assert ("remove_flags", (1,), (b"\\Seen",)) in fake.calls


def test_trash_resolves_german_folder_name():
    fake = FakeIMAP()
    Mailbox(fake).trash("INBOX", 1)
    assert ("move", (1,), "Papierkorb") in fake.calls


def test_trash_resolves_gmx_geloescht():
    fake = FakeIMAP(folders=("INBOX", "Gelöscht"))
    Mailbox(fake).trash("INBOX", 1)
    assert ("move", (1,), "Gelöscht") in fake.calls


def test_search_uses_imap_text_search():
    fake = FakeIMAP()
    Mailbox(fake).search("INBOX", "Rechnung Juli")
    criteria = [c for c in fake.calls if c[0] == "search"][0][1]
    assert criteria == ["TEXT", "Rechnung Juli"]


def test_search_with_umlauts_uses_utf8_charset():
    fake = FakeIMAP()
    Mailbox(fake).search("INBOX", "Grüße Müller")
    search_calls = [c for c in fake.calls if c[0] == "search"]
    assert search_calls[0][2] == "UTF-8"  # charset-Argument


def test_search_falls_back_to_local_filter_when_server_rejects_charset():
    from imapclient.exceptions import IMAPClientError

    fake = FakeIMAP(search_result=(1,))
    original_search = fake.search

    def picky_search(criteria, charset=None):
        if charset is not None:
            raise IMAPClientError("BAD Unsupported CHARSET")
        return original_search(criteria)

    fake.search = picky_search
    results = Mailbox(fake).search("INBOX", "Grüße")
    # Fixture-Mail enthält "Grüße" im Betreff → lokaler Filter findet sie
    assert [m.uid for m in results] == [1]


def test_append_sent_targets_sent_folder():
    fake = FakeIMAP()
    Mailbox(fake).append_sent(b"MIME")
    [(_, folder, msg, flags)] = [c for c in fake.calls if c[0] == "append"]
    assert folder == "Gesendet"
    assert msg == b"MIME"
    assert b"\\Seen" in flags
