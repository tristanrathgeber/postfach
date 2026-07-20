"""Postfach-Konfiguration: email-agent-Accounts plus SMTP-Versanddaten.

Die Konten werden vom (validierenden) email-agent-Loader geparst; hier kommen
nur die SMTP-Extras dazu — kein zweiter Parser, keine Validierungs-Drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from email_agent.config import AccountConfig
from email_agent.config import Config as AgentConfig
from email_agent.config import load_config as load_agent_config

_GMAIL_IMAP = "imap.gmail.com"
_GMAIL_SMTP = "smtp.gmail.com"


@dataclass(frozen=True)
class MailAccount:
    name: str
    provider: str  # "imap" | "gmail"
    address: str
    password_env: str
    imap_host: str = ""
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 587  # STARTTLS; 465 = SSL
    sent_folder: str | None = None


@dataclass(frozen=True)
class EmiliaConfig:
    model: str = "llama3.2"
    embed_model: str = "all-minilm:l6-v2"
    ollama_url: str = "http://localhost:11434"
    sort_local: bool = False
    draft_local: bool = False


@dataclass(frozen=True)
class PostfachConfig:
    accounts: tuple[MailAccount, ...]
    agent: AgentConfig
    emilia: EmiliaConfig = EmiliaConfig()


def _to_mail_account(account: AccountConfig, raw: dict) -> MailAccount:
    imap_host = account.imap_host or (_GMAIL_IMAP if account.provider == "gmail" else "")
    smtp_default = _GMAIL_SMTP if account.provider == "gmail" else imap_host
    return MailAccount(
        name=account.name,
        provider=account.provider,
        address=account.address,
        password_env=account.password_env,
        imap_host=imap_host,
        imap_port=account.imap_port,
        smtp_host=str(raw.get("smtp_host", "")) or smtp_default,
        smtp_port=int(raw.get("smtp_port", 587)),
        sent_folder=account.sent_folder,
    )


def load_postfach_config(path: Path) -> PostfachConfig:
    agent = load_agent_config(path)
    raw_by_name: dict[str, dict] = {}
    emilia_raw: dict = {}
    if Path(path).exists():
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        raw_by_name = {
            str(entry.get("name", "")).strip(): entry for entry in data.get("accounts") or []
        }
        emilia_raw = data.get("emilia") or {}
    accounts = tuple(
        _to_mail_account(account, raw_by_name.get(account.name, {}))
        for account in agent.accounts
    )
    defaults = EmiliaConfig()
    emilia = EmiliaConfig(
        model=str(emilia_raw.get("model", defaults.model)),
        embed_model=str(emilia_raw.get("embed_model", defaults.embed_model)),
        ollama_url=str(emilia_raw.get("ollama_url", defaults.ollama_url)),
        sort_local=bool(emilia_raw.get("sort_local", defaults.sort_local)),
        draft_local=bool(emilia_raw.get("draft_local", defaults.draft_local)),
    )
    return PostfachConfig(accounts=accounts, agent=agent, emilia=emilia)
