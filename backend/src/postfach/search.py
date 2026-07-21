"""Lokale Volltextsuche über SQLite-FTS5 — Treffer in Millisekunden, offline.

Eigene DB (data/search.db), external-content-FTS mit Trigger-Sync.
Nutzereingaben werden NIE als FTS-Syntax interpretiert: jedes Token wandert
als gequotetes Literal in den MATCH-String (sonst wären AND/OR/NEAR/* von
außen steuerbar). Datums- und Anhang-Filter laufen als WHERE-Klauseln.

Der Index ist ABGELEITETE Information: Schreiboperationen sind non-raising
(Best Effort mit Log) — ein Index-Problem darf nie eine Mail-Aktion oder den
Watcher zu Fall bringen. Verschobene Mails werden ENTFERNT statt umgezogen:
IMAP vergibt im Zielordner neue UIDs, ein „Umzug" wäre ein toter Treffer.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path

from email_agent.textutil import truncate

log = logging.getLogger("postfach.search")

_BODY_CAP = 32_000  # FTS-Index-Größe: längere Bodies sind HTML-/Anhang-Reste
_LIMIT = 50
_WRITE_CHUNK = 1000  # eigene Transaktion je Chunk — kürzere Schreib-Locks

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mails (
  id INTEGER PRIMARY KEY,
  account TEXT NOT NULL,
  folder TEXT NOT NULL,
  uid INTEGER NOT NULL,
  subject TEXT NOT NULL DEFAULT '',
  from_name TEXT NOT NULL DEFAULT '',
  from_addr TEXT NOT NULL DEFAULT '',
  from_text TEXT NOT NULL DEFAULT '',
  recipients TEXT NOT NULL DEFAULT '',
  date_iso TEXT NOT NULL DEFAULT '',
  has_attachments INTEGER NOT NULL DEFAULT 0,
  seen INTEGER NOT NULL DEFAULT 1,
  snippet TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  UNIQUE(account, folder, uid)
);
CREATE TABLE IF NOT EXISTS meta (
  account TEXT PRIMARY KEY,
  full_index_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS mails_fts USING fts5(
  subject, from_text, recipients, body,
  content='mails', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS mails_ai AFTER INSERT ON mails BEGIN
  INSERT INTO mails_fts(rowid, subject, from_text, recipients, body)
  VALUES (new.id, new.subject, new.from_text, new.recipients, new.body);
END;
CREATE TRIGGER IF NOT EXISTS mails_ad AFTER DELETE ON mails BEGIN
  INSERT INTO mails_fts(mails_fts, rowid, subject, from_text, recipients, body)
  VALUES ('delete', old.id, old.subject, old.from_text, old.recipients, old.body);
END;
-- UPDATE OF: seen-Updates re-tokenisieren nicht den 32-kB-Body
DROP TRIGGER IF EXISTS mails_au;
CREATE TRIGGER mails_au AFTER UPDATE OF subject, from_text, recipients, body ON mails BEGIN
  INSERT INTO mails_fts(mails_fts, rowid, subject, from_text, recipients, body)
  VALUES ('delete', old.id, old.subject, old.from_text, old.recipients, old.body);
  INSERT INTO mails_fts(rowid, subject, from_text, recipients, body)
  VALUES (new.id, new.subject, new.from_text, new.recipients, new.body);
END;
"""


@dataclass
class Query:
    """Geparste Suchanfrage — Operatoren getrennt vom Volltext-Anteil."""

    text: list[str] = field(default_factory=list)
    phrases: list[str] = field(default_factory=list)
    from_: str | None = None
    to: str | None = None
    subject: str | None = None
    before: str | None = None
    after: str | None = None
    has_attachment: bool | None = None


_OPERATORS = {"von": "from_", "an": "to", "betreff": "subject", "vor": "before", "nach": "after"}
_TOKEN_RE = re.compile(r'"([^"]*)"|(\S+)')


def parse_query(q: str) -> Query:
    """`von:` `an:` `betreff:` `vor:` `nach:` `hat:anhang` + Phrasen + Volltext."""
    result = Query()
    for match in _TOKEN_RE.finditer(q):
        phrase, word = match.groups()
        if phrase is not None:
            if phrase.strip():
                result.phrases.append(phrase.strip())
            continue
        op, _, value = word.partition(":")
        if value and op.lower() == "hat":
            if value.lower() in ("anhang", "attachment"):
                result.has_attachment = True
            else:
                # Tippfehler ('hat:anhänge') nie still als Filter deuten
                result.text.append(value)
        elif value and op.lower() in _OPERATORS:
            setattr(result, _OPERATORS[op.lower()], value)
        else:
            result.text.append(word)
    return result


def _quote(token: str) -> str:
    """Token als FTS-String-Literal — Nutzereingaben sind nie Syntax."""
    return '"' + token.replace('"', '""') + '"'


def _match_string(query: Query) -> str:
    parts: list[str] = []
    parts.extend(_quote(t) for t in query.text)
    parts.extend(_quote(p) for p in query.phrases)  # Quotes = Phrase in FTS5
    if query.subject:
        parts.append(f"subject:{_quote(query.subject)}")
    if query.from_:
        parts.append(f"from_text:{_quote(query.from_)}")
    if query.to:
        parts.append(f"recipients:{_quote(query.to)}")
    return " ".join(parts)


class SearchIndex:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=10)
        # WAL: Suchen laufen an laufenden Index-Transaktionen vorbei.
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def add_mails(self, account: str, folder: str, mails: list) -> int:
        rows = [
            (
                account, folder, m.uid,
                m.subject or "", m.from_name or "", m.from_addr or "",
                f"{m.from_name} {m.from_addr}".strip(),
                " ".join((*m.to, *m.cc)),
                m.date_iso or "", int(bool(m.attachments)), int(bool(m.seen)),
                truncate(re.sub(r"\s+", " ", (m.body_text or "")[:2000]).strip(), 120),
                (m.body_text or "")[:_BODY_CAP],
            )
            for m in mails
        ]
        if not rows:
            return 0
        try:
            with self._lock:
                for i in range(0, len(rows), _WRITE_CHUNK):
                    with self._connect() as conn:
                        conn.executemany(
                            "INSERT INTO mails (account, folder, uid, subject, from_name, from_addr,"
                            " from_text, recipients, date_iso, has_attachments, seen, snippet, body)"
                            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
                            " ON CONFLICT(account, folder, uid) DO UPDATE SET"
                            " subject=excluded.subject, from_name=excluded.from_name,"
                            " from_addr=excluded.from_addr, from_text=excluded.from_text,"
                            " recipients=excluded.recipients, date_iso=excluded.date_iso,"
                            " has_attachments=excluded.has_attachments, seen=excluded.seen,"
                            " snippet=excluded.snippet, body=excluded.body",
                            rows[i : i + _WRITE_CHUNK],
                        )
        except sqlite3.Error:
            log.exception("Such-Index: add_mails fehlgeschlagen (%s/%s)", account, folder)
            return 0
        return len(rows)

    def remove_mails(self, account: str, folder: str, uids: list[int]) -> None:
        """Mail wurde verschoben/entsorgt: Eintrag raus (IMAP vergibt im Ziel
        neue UIDs — ein Umzug im Index wäre ein toter Treffer). Best Effort."""
        if not uids:
            return
        try:
            with self._lock, self._connect() as conn:
                conn.executemany(
                    "DELETE FROM mails WHERE account=? AND folder=? AND uid=?",
                    [(account, folder, uid) for uid in uids],
                )
        except sqlite3.Error:
            log.exception("Such-Index: remove_mails fehlgeschlagen (%s/%s)", account, folder)

    def set_seen(self, account: str, folder: str, uids: list[int], seen: bool) -> None:
        """Gelesen-Status mitführen (kein FTS-Rebuild dank UPDATE-OF-Trigger)."""
        if not uids:
            return
        try:
            with self._lock, self._connect() as conn:
                conn.executemany(
                    "UPDATE mails SET seen=? WHERE account=? AND folder=? AND uid=?",
                    [(int(seen), account, folder, uid) for uid in uids],
                )
        except sqlite3.Error:
            log.exception("Such-Index: set_seen fehlgeschlagen (%s/%s)", account, folder)

    def prune_folder(self, account: str, folder: str, keep_uids: list[int]) -> None:
        """Nach einem Voll-Scan: Zeilen entfernen, die der Scan nicht mehr sah
        (extern verschoben/gelöscht) — sonst akkumulieren Geister-Treffer."""
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    "DELETE FROM mails WHERE account=? AND folder=?"
                    " AND uid NOT IN (SELECT value FROM json_each(?))",
                    (account, folder, json.dumps(keep_uids)),
                )
        except sqlite3.Error:
            log.exception("Such-Index: prune_folder fehlgeschlagen (%s/%s)", account, folder)

    def prune_missing_folders(self, account: str, scanned: list[str]) -> None:
        """Ordner, die der Voll-Scan nicht mehr besucht (gelöscht, Papierkorb,
        Spam): komplett aus dem Index — Weggeworfenes bleibt kein Suchtreffer."""
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    "DELETE FROM mails WHERE account=?"
                    " AND folder NOT IN (SELECT value FROM json_each(?))",
                    (account, json.dumps(scanned)),
                )
        except sqlite3.Error:
            log.exception("Such-Index: prune_missing_folders fehlgeschlagen (%s)", account)

    def mark_full_index(self, account: str, when: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO meta (account, full_index_at) VALUES (?, ?)"
                " ON CONFLICT(account) DO UPDATE SET full_index_at=excluded.full_index_at",
                (account, when),
            )

    def is_ready(self, account: str) -> bool:
        """True erst nach einem VOLLEN Index-Lauf — die paar Watcher-Zeilen
        eines frischen Setups dürfen den IMAP-Fallback nicht verschatten."""
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM meta WHERE account=?", (account,)).fetchone()
        return row is not None

    def count(self, account: str) -> int:
        with self._connect() as conn:
            [(n,)] = conn.execute("SELECT COUNT(*) FROM mails WHERE account=?", (account,))
        return n

    def search(self, account: str, q: str, folder: str | None = None) -> list[dict]:
        query = parse_query(q)
        match = _match_string(query)

        where = ["m.account = ?"]
        params: list = [account]
        if folder:
            where.append("m.folder = ?")
            params.append(folder)
        if query.before:
            where.append("m.date_iso < ?")
            params.append(query.before)
        if query.after:
            where.append("m.date_iso >= ?")
            params.append(query.after)
        if query.has_attachment is not None:
            where.append("m.has_attachments = ?")
            params.append(int(query.has_attachment))

        select = (
            "SELECT m.account, m.folder, m.uid, m.subject, m.from_name, m.from_addr,"
            " m.date_iso, m.snippet, m.seen, m.has_attachments"
        )
        if match:
            # bm25-Gewichte: Betreff > Absender/Empfänger > Body; Gleichstand → neuer zuerst
            sql = (
                f"{select} FROM mails_fts f JOIN mails m ON m.id = f.rowid"
                f" WHERE mails_fts MATCH ? AND {' AND '.join(where)}"
                " ORDER BY bm25(mails_fts, 10.0, 5.0, 5.0, 1.0), m.date_iso DESC LIMIT ?"
            )
            params = [match, *params, _LIMIT]
        else:
            sql = (
                f"{select} FROM mails m WHERE {' AND '.join(where)}"
                " ORDER BY m.date_iso DESC LIMIT ?"
            )
            params = [*params, _LIMIT]

        try:
            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            # Defensiv: sollte durch Literal-Quoting + WAL nie eintreten —
            # aber eine Suche darf niemals einen 500er produzieren.
            log.exception("Such-Index: Query fehlgeschlagen (%s, %r)", account, q)
            return []
        return [
            {
                "account": acc, "folder": fol, "uid": uid, "subject": subject,
                "from_name": from_name, "from_addr": from_addr, "date": date,
                "snippet": snippet, "seen": bool(seen),
                "has_attachments": bool(atts), "category": None,
            }
            for acc, fol, uid, subject, from_name, from_addr, date, snippet, seen, atts in rows
        ]
