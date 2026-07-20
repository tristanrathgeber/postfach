from email import message_from_bytes
from email.policy import default as default_policy

import postfach.mail_send as mail_send
from postfach.config import MailAccount
from postfach.mail_send import build_outgoing, send_mail


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port
        self.calls = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, msg):
        self.calls.append(("send", msg))


def _account(port=587):
    return MailAccount(
        name="privat", provider="imap", address="t@meinedomain.de",
        password_env="MAIL_PRIVAT_PASSWORD", imap_host="mail.meinedomain.de",
        smtp_host="mail.meinedomain.de", smtp_port=port,
    )


def test_build_outgoing_sets_recipients_and_reply_threading():
    from postfach.demo import _mail
    from dataclasses import replace

    original = replace(
        _mail(1, "Frage", "Alice", "alice@example.com", "Hallo?"),
        message_id="<orig@example.com>",
        references="<a@x>",
    )
    mime_bytes = build_outgoing(
        from_addr="t@meinedomain.de",
        to=["alice@example.com"],
        cc=["bob@example.com"],
        subject="Antwort",
        body="Hallo Grüße äöü",
        reply_to_original=original,
    )
    parsed = message_from_bytes(mime_bytes, policy=default_policy)
    assert parsed["To"] == "alice@example.com"
    assert parsed["Cc"] == "bob@example.com"
    assert parsed["In-Reply-To"] == "<orig@example.com>"
    assert parsed["References"] == "<a@x> <orig@example.com>"
    assert parsed["Message-ID"]
    assert "Grüße äöü" in parsed.get_content()


def test_send_uses_starttls_on_587(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(mail_send.smtplib, "SMTP", FakeSMTP)
    mime = build_outgoing("t@meinedomain.de", ["a@b.de"], [], "Hi", "Text")
    send_mail(_account(587), "geheim", mime)
    [smtp] = FakeSMTP.instances
    assert smtp.port == 587
    assert smtp.calls[0] == "starttls"
    assert ("login", "t@meinedomain.de", "geheim") in smtp.calls
    assert any(c[0] == "send" for c in smtp.calls if isinstance(c, tuple))


def test_send_uses_ssl_on_465(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(mail_send.smtplib, "SMTP_SSL", FakeSMTP)
    mime = build_outgoing("t@meinedomain.de", ["a@b.de"], [], "Hi", "Text")
    send_mail(_account(465), "geheim", mime)
    [smtp] = FakeSMTP.instances
    assert smtp.port == 465
    assert "starttls" not in smtp.calls


def test_password_never_in_mime():
    mime = build_outgoing("t@x.de", ["a@b.de"], [], "Hi", "Text")
    assert b"geheim" not in mime
