import textwrap

from postfach.config import load_postfach_config


def _write(tmp_path, body):
    path = tmp_path / "config.yaml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_smtp_defaults_fall_back_to_imap_host_and_587(tmp_path):
    path = _write(
        tmp_path,
        """
        accounts:
          - name: privat
            address: t@meinedomain.de
            imap_host: mail.meinedomain.de
        """,
    )
    cfg = load_postfach_config(path)
    [account] = cfg.accounts
    assert account.smtp_host == "mail.meinedomain.de"
    assert account.smtp_port == 587
    assert account.password_env == "MAIL_PRIVAT_PASSWORD"


def test_gmail_provider_gets_gmail_smtp(tmp_path):
    path = _write(
        tmp_path,
        """
        accounts:
          - name: g
            provider: gmail
            address: x@gmail.com
            password_env: GMAIL_APP_PASSWORD
        """,
    )
    [account] = load_postfach_config(path).accounts
    assert account.smtp_host == "smtp.gmail.com"
    assert account.smtp_port == 587


def test_explicit_smtp_overrides(tmp_path):
    path = _write(
        tmp_path,
        """
        accounts:
          - name: a
            address: a@b.de
            imap_host: mail.b.de
            smtp_host: send.b.de
            smtp_port: 465
        """,
    )
    [account] = load_postfach_config(path).accounts
    assert account.smtp_host == "send.b.de"
    assert account.smtp_port == 465


def test_agent_config_passthrough(tmp_path):
    path = _write(tmp_path, "llm_backend: ollama\n")
    cfg = load_postfach_config(path)
    assert cfg.agent.llm_backend == "ollama"
    assert "Newsletter" in cfg.agent.taxonomy
