"""AI-Glue: Klassifikation (mit Datei-Cache) und Antwortentwürfe.

Nutzt die getestete email-agent-Intelligenz. Dieses Modul hat bewusst KEINEN
Zugriff auf Versand- oder Lösch-Pfade (tests/test_safety.py erzwingt das) —
die AI liest und formuliert, Aktionen führt nur der Mensch aus.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from email_agent.classifier import Classifier
from email_agent.config import Config as AgentConfig
from email_agent.drafter import draft_reply_text
from email_agent.models import EmailMessage
from email_agent.style import load_style_profile

from .mail_imap import ParsedMail


def to_agent_message(mail: ParsedMail) -> EmailMessage:
    return EmailMessage(
        uid=mail.uid,
        message_id=mail.message_id,
        subject=mail.subject,
        from_addr=mail.from_addr,
        from_name=mail.from_name,
        to_addrs=mail.to,
        reply_to=mail.reply_to,
        date=mail.date_iso,
        body_text=mail.body_text,
        headers=mail.headers,
    )


class AiService:
    def __init__(
        self,
        agent_config: AgentConfig,
        backend,
        cache_path: Path,
        style_path: Path,
        draft_backend=None,
    ) -> None:
        self._config = agent_config
        self._backend = backend  # Klassifikation
        self._draft_backend = draft_backend or backend  # Entwürfe (ggf. anderes Modell)
        self._cache_path = Path(cache_path)
        self._style_path = Path(style_path)
        # FastAPI führt Sync-Routen im Threadpool aus — parallele /classify-Calls
        # (ein POST pro Konto in der „Alle Konten"-Ansicht) dürfen sich das
        # Load-Mutate-Save auf der Cache-Datei nicht gegenseitig zerschießen.
        self._lock = threading.Lock()

    def _load_cache(self) -> dict:
        if self._cache_path.exists():
            return json.loads(self._cache_path.read_text(encoding="utf-8"))
        return {}

    def _save_cache(self, cache: dict) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    @staticmethod
    def _key(account: str, folder: str, uid: int) -> str:
        # IMAP-UIDs sind nur PRO ORDNER eindeutig — ohne Ordner im Schlüssel
        # bekäme INBOX-uid 42 die Kategorie von Gesendet-uid 42.
        return f"{account}:{folder}:{uid}"

    def classify(self, account: str, folder: str, mails: list[ParsedMail]) -> dict[int, dict]:
        """Cache-Choreografie lebt NUR hier; Subklassen liefern via _classify_fresh."""
        with self._lock:
            cache = self._load_cache()
            missing = [m for m in mails if self._key(account, folder, m.uid) not in cache]
        if missing:
            fresh = self._classify_fresh(missing)
            with self._lock:
                cache = self._load_cache()
                for uid, entry in fresh.items():
                    key = self._key(account, folder, uid)
                    # Während des LLM-Laufs kann ein User-Override eingetroffen
                    # sein — Nutzerkorrekturen schlagen die KI, immer.
                    if cache.get(key, {}).get("source") == "user":
                        continue
                    cache[key] = entry
                self._save_cache(cache)
        return {
            m.uid: cache[self._key(account, folder, m.uid)]
            for m in mails
            if self._key(account, folder, m.uid) in cache
        }

    def _classify_fresh(self, missing: list[ParsedMail]) -> dict[int, dict]:
        classifications = Classifier(self._backend, self._config).classify(
            [to_agent_message(m) for m in missing]
        )
        return {
            clf.uid: {
                "category": clf.category,
                "is_newsletter": clf.is_newsletter,
                "interesting": clf.interesting,
                "needs_reply": clf.needs_reply,
                "reason": clf.reason,
            }
            for clf in classifications
        }

    def override_category(self, account: str, folder: str, uid: int, category: str) -> None:
        """Nutzer-Korrektur: schlägt die KI dauerhaft. classify() füllt nur
        FEHLENDE Keys — ein vorhandener Override wird also nie überschrieben."""
        defaults = {
            "is_newsletter": False,
            "interesting": False,
            "needs_reply": False,
            "reason": "Vom Nutzer einsortiert",
        }
        with self._lock:
            cache = self._load_cache()
            entry = cache.get(self._key(account, folder, uid), {})
            cache[self._key(account, folder, uid)] = {
                **defaults,
                **entry,
                "category": category,
                "source": "user",
            }
            self._save_cache(cache)

    def cached_categories(self, account: str, folder: str, uids: list[int]) -> dict[int, str]:
        """Ein Cache-Read pro Request statt einem pro Mail-Zeile."""
        many = self.cached_categories_many(account, [(folder, uid) for uid in uids])
        return {uid: category for (_f, uid), category in many.items()}

    def cached_categories_many(self, account: str, keys: list[tuple[str, int]]) -> dict[tuple[str, int], str]:
        """Ordnerübergreifend (Suche): EIN Cache-Load für beliebige (folder, uid)-Paare."""
        with self._lock:
            cache = self._load_cache()
        result = {}
        for folder, uid in keys:
            entry = cache.get(self._key(account, folder, uid))
            if entry:
                result[(folder, uid)] = entry["category"]
        return result

    def draft(self, mail: ParsedMail) -> str:
        style = load_style_profile(self._style_path)
        return draft_reply_text(self._draft_backend, style, to_agent_message(mail), self._config)


class DemoAiService(AiService):
    """Regelbasiert statt LLM — für POSTFACH_DEMO=1. Nur die Frisch-Quelle
    und der Entwurf unterscheiden sich; die Cache-Mechanik erbt sie."""

    def __init__(self, agent_config: AgentConfig, cache_path: Path, style_path: Path) -> None:
        super().__init__(agent_config, backend=None, cache_path=cache_path, style_path=style_path)

    def _classify_fresh(self, missing: list[ParsedMail]) -> dict[int, dict]:
        from .demo import demo_classify

        return demo_classify(missing)

    def draft(self, mail: ParsedMail) -> str:
        return (
            f"Hi {mail.from_name.split()[0] if mail.from_name else ''},\n\n"
            "[Demo-Entwurf — im echten Betrieb schreibt die AI hier in deinem Stil]\n\n"
            "Viele Grüße"
        )
