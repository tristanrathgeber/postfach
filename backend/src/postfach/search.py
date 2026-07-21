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

import hashlib
import json
import logging
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
  message_id TEXT NOT NULL DEFAULT '',
  thread_root TEXT NOT NULL DEFAULT '',
  subject_norm TEXT NOT NULL DEFAULT '',
  list_unsubscribe TEXT NOT NULL DEFAULT '',
  list_unsubscribe_post TEXT NOT NULL DEFAULT '',
  is_sent INTEGER NOT NULL DEFAULT 0,
  UNIQUE(account, folder, uid)
);
CREATE INDEX IF NOT EXISTS idx_thread ON mails(account, thread_root);
CREATE INDEX IF NOT EXISTS idx_subject_norm ON mails(account, subject_norm);
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


_REPLY_PREFIX_RE = re.compile(r"^\s*((re|aw|antw|fwd?|wg)\s*:\s*)+", re.IGNORECASE)


def normalize_subject(subject: str) -> str:
    """Re:/AW:/Fwd:-Präfixe ab, getrimmt, lowercase — für den Betreff-Fallback."""
    return _REPLY_PREFIX_RE.sub("", subject or "").strip().lower()


_MSGID_RE = re.compile(r"<[^>]+>")


def _parse_refs(references: str) -> list[str]:
    """Nur echte <Message-IDs> — RFC-5322-Kommentare u. Ä. ignorieren."""
    return _MSGID_RE.findall(references or "")


def thread_root_for(mail) -> str:
    """Wurzel des Gesprächsfadens: References[0] → eigene Message-ID →
    synthetisch (stabil, aber eindeutig pro Mail — leere Message-IDs dürfen
    nicht alle im selben Faden landen)."""
    refs = _parse_refs(mail.references)
    if refs:
        return refs[0]
    if mail.message_id:
        return mail.message_id
    seed = f"{mail.subject}|{mail.from_addr}|{mail.date_iso}|{mail.uid}"
    return "<synth-" + hashlib.sha1(seed.encode()).hexdigest()[:16] + ">"


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
            self._migrate(conn)
            conn.executescript(_SCHEMA)

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Bestands-DBs (v0.5) um die Thread-Spalten ergänzen — die Werte
        füllt der nächste Voll-Index."""
        existing = {row[1] for row in conn.execute("PRAGMA table_info(mails)")}
        if existing:
            for column in ("message_id", "thread_root", "subject_norm",
                           "list_unsubscribe", "list_unsubscribe_post"):
                if column not in existing:
                    conn.execute(f"ALTER TABLE mails ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
            if "is_sent" not in existing:
                from .mail_imap import is_sent_folder

                conn.execute("ALTER TABLE mails ADD COLUMN is_sent INTEGER NOT NULL DEFAULT 0")
                # Backfill sofort: das Gesendet-Wissen speist den Screener-
                # "bekannt"-Filter — ohne Backfill flutet er nach dem Update
                # mit längst bekannten Kontakten, bis der Voll-Index läuft.
                folders = [r[0] for r in conn.execute("SELECT DISTINCT folder FROM mails")]
                sent = [f for f in folders if is_sent_folder(f)]
                if sent:
                    conn.execute(
                        "UPDATE mails SET is_sent=1 WHERE folder IN"
                        " (SELECT value FROM json_each(?))",
                        (json.dumps(sent),),
                    )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=10)
        # WAL: Suchen laufen an laufenden Index-Transaktionen vorbei.
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _fallback_root(self, conn, account: str, mail, chunk_seen: dict) -> str | None:
        """Betreff-Fallback für Antworten OHNE Referenzen (kaputte Clients):
        nur wenn GENAU EIN Kandidaten-Faden mit passendem Betreff und
        beteiligter Gegenseite existiert — nie raten. Kandidaten kommen aus der
        DB UND aus dem aktuellen Chunk (der Voll-Index sieht sonst nichts)."""
        norm = normalize_subject(mail.subject)
        if not norm or norm == (mail.subject or "").strip().lower():
            return None  # kein Antwort-Präfix → keine Zuordnung per Betreff
        addr = (mail.from_addr or "").lower()
        # Token-Match: ' addr ' im gepolsterten Empfänger-String — a@x.de darf
        # nicht via Substring an petra@x.de andocken.
        rows = conn.execute(
            "SELECT DISTINCT thread_root FROM mails"
            " WHERE account=? AND subject_norm=? AND thread_root != ''"
            " AND (lower(from_addr)=? OR instr(' '||lower(recipients)||' ', ' '||?||' ') > 0)"
            " LIMIT 3",
            (account, norm, addr, addr),
        ).fetchall()
        candidates = {r[0] for r in rows}
        for root, c_from, c_recipients in chunk_seen.get(norm, ()):
            if c_from == addr or f" {addr} " in f" {c_recipients} ":
                candidates.add(root)
        return next(iter(candidates)) if len(candidates) == 1 else None

    _UPSERT_COMMON = (
        " subject=excluded.subject, from_name=excluded.from_name,"
        " from_addr=excluded.from_addr, from_text=excluded.from_text,"
        " recipients=excluded.recipients, date_iso=excluded.date_iso,"
        " has_attachments=excluded.has_attachments, seen=excluded.seen,"
        " snippet=excluded.snippet, body=excluded.body,"
        " message_id=excluded.message_id, subject_norm=excluded.subject_norm,"
        " list_unsubscribe=excluded.list_unsubscribe,"
        " list_unsubscribe_post=excluded.list_unsubscribe_post, is_sent=excluded.is_sent"
    )
    _INSERT_SQL = (
        "INSERT INTO mails (account, folder, uid, subject, from_name, from_addr,"
        " from_text, recipients, date_iso, has_attachments, seen, snippet, body,"
        " message_id, thread_root, subject_norm,"
        " list_unsubscribe, list_unsubscribe_post, is_sent)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    )

    def add_mails(self, account: str, folder: str, mails: list) -> int:
        if not mails:
            return 0
        # Chronologisch verarbeiten: der Betreff-Fallback muss die Wurzel
        # gesehen haben, BEVOR die kaputte Antwort dran ist (list_messages
        # liefert absteigend — genau verkehrt herum).
        ordered = sorted(mails, key=lambda m: m.date_iso or "")
        try:
            with self._lock:
                for i in range(0, len(ordered), _WRITE_CHUNK):
                    chunk = ordered[i : i + _WRITE_CHUNK]
                    with self._connect() as conn:
                        self._insert_chunk(conn, account, folder, chunk)
        except sqlite3.Error:
            log.exception("Such-Index: add_mails fehlgeschlagen (%s/%s)", account, folder)
            return 0
        return len(mails)

    def _insert_chunk(self, conn, account: str, folder: str, chunk: list) -> None:
        from .mail_imap import is_sent_folder

        sent_flag = int(is_sent_folder(folder))
        with_refs, without_refs = [], []
        chunk_seen: dict[str, list] = {}
        for m in chunk:
            has_refs = bool(_parse_refs(m.references))
            root = thread_root_for(m)
            if not has_refs:
                root = self._fallback_root(conn, account, m, chunk_seen) or root
            chunk_seen.setdefault(normalize_subject(m.subject), []).append(
                (root, (m.from_addr or "").lower(), " ".join((*m.to, *m.cc)).lower())
            )
            headers = getattr(m, "headers", None) or {}
            row = (
                account, folder, m.uid,
                m.subject or "", m.from_name or "", m.from_addr or "",
                f"{m.from_name} {m.from_addr}".strip(),
                " ".join((*m.to, *m.cc)),
                m.date_iso or "", int(bool(m.attachments)), int(bool(m.seen)),
                truncate(re.sub(r"\s+", " ", (m.body_text or "")[:2000]).strip(), 120),
                (m.body_text or "")[:_BODY_CAP],
                m.message_id or "", root, normalize_subject(m.subject),
                headers.get("list-unsubscribe", "")[:2000],  # feindliche Riesen-Header kappen
                headers.get("list-unsubscribe-post", "")[:200], sent_flag,
            )
            (with_refs if has_refs else without_refs).append(row)
        if with_refs:
            conn.executemany(
                self._INSERT_SQL + " ON CONFLICT(account, folder, uid) DO UPDATE SET"
                + self._UPSERT_COMMON + ", thread_root=excluded.thread_root",
                with_refs,
            )
        if without_refs:
            # Referenzlose Mails: ein früher per Fallback gefundener Root bleibt
            # erhalten — ein Re-Index darf den Faden nicht wieder zerreißen.
            conn.executemany(
                self._INSERT_SQL + " ON CONFLICT(account, folder, uid) DO UPDATE SET"
                + self._UPSERT_COMMON
                + ", thread_root=COALESCE(NULLIF(mails.thread_root, ''), excluded.thread_root)",
                without_refs,
            )

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

    # --- Konversations-Threads ---

    _HIT_SELECT = (
        "SELECT account, folder, uid, subject, from_name, from_addr,"
        " date_iso, snippet, seen, has_attachments FROM mails"
    )

    def thread(self, account: str, root: str) -> list[dict]:
        """Alle Mails des Fadens, kontoweit, chronologisch aufsteigend."""
        with self._connect() as conn:
            rows = conn.execute(
                f"{self._HIT_SELECT} WHERE account=? AND thread_root=?"
                " ORDER BY date_iso ASC LIMIT 100",
                (account, root),
            ).fetchall()
        return [{**self._row_to_summary(row), "thread_count": len(rows)} for row in rows]

    def thread_roots_of(self, account: str, folder: str, uids: list[int]) -> dict[int, str]:
        """Gespeicherte Roots (inkl. Betreff-Fallback) für eine Listen-Seite."""
        if not uids:
            return {}
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT uid, thread_root FROM mails WHERE account=? AND folder=?"
                " AND uid IN (SELECT value FROM json_each(?)) AND thread_root != ''",
                (account, folder, json.dumps(uids)),
            ).fetchall()
        return dict(rows)

    def thread_root_of(self, account: str, folder: str, uid: int) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT thread_root FROM mails WHERE account=? AND folder=? AND uid=?",
                (account, folder, uid),
            ).fetchone()
        return row[0] if row and row[0] else None

    def thread_counts(self, account: str, roots: list[str]) -> dict[str, int]:
        """EIN Query für die Zähler einer ganzen Listen-Seite."""
        if not roots:
            return {}
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT thread_root, COUNT(*) FROM mails"
                " WHERE account=? AND thread_root IN (SELECT value FROM json_each(?))"
                " GROUP BY thread_root",
                (account, json.dumps(sorted(set(roots)))),
            ).fetchall()
        return dict(rows)

    @staticmethod
    def _row_to_summary(row) -> dict:
        acc, fol, uid, subject, from_name, from_addr, date, snippet, seen, atts = row
        return {
            "account": acc, "folder": fol, "uid": uid, "subject": subject,
            "from_name": from_name, "from_addr": from_addr, "date": date,
            "snippet": snippet, "seen": bool(seen),
            "has_attachments": bool(atts), "category": None,
        }

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
            " m.date_iso, m.snippet, m.seen, m.has_attachments, m.thread_root"
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
        counts = self.thread_counts(account, [row[10] for row in rows if row[10]])
        return [
            {**self._row_to_summary(row[:10]), "thread_count": max(counts.get(row[10], 1), 1)}
            for row in rows
        ]

    # --- Posteingangs-Hygiene (Abo-Manager + Screener) ---

    def _hygiene_folders_sql(self, conn, account: str) -> tuple[str, list]:
        """WHERE-Fragment, das Spam/Papierkorb ausblendet: Absender, die nur
        dort liegen, sind weder Abo noch Screener-Kandidat."""
        from .mail_imap import is_junk_or_trash_folder

        folders = [r[0] for r in conn.execute(
            "SELECT DISTINCT folder FROM mails WHERE account=?", (account,))]
        excluded = [f for f in folders if is_junk_or_trash_folder(f)]
        if not excluded:
            return "", []
        return " AND folder NOT IN (SELECT value FROM json_each(?))", [json.dumps(excluded)]

    @staticmethod
    def _per_month(count: int, first: str, last: str) -> float:
        """Frequenz aus Zeitspanne — tz-Suffixe kappen, Mischformen (naiv vs.
        aware) lassen sich sonst nicht subtrahieren. Mit nur einer Mail gibt es
        keine Spanne — dann ist die ehrliche Zahl schlicht die Mail-Anzahl."""
        if count < 2:
            return float(count)
        try:
            span = (datetime.fromisoformat(last[:19]) - datetime.fromisoformat(first[:19])).days
        except ValueError:
            return float(count)
        return round(count * 30 / max(span, 1), 1)

    def subscriptions(self, account: str) -> list[dict]:
        """Abo-Liste: Absender mit List-Unsubscribe-Header, gruppiert, nach
        Frequenz absteigend. `method` = beste verfügbare Abmelde-Strategie."""
        from .unsubscribe import parse_list_unsubscribe

        with self._connect() as conn:
            extra, extra_params = self._hygiene_folders_sql(conn, account)
            # Header-PAAR immer aus der NEUESTEN Mail (ROW_NUMBER statt zweier
            # unabhängiger MAX()): sonst mischt die Liste list_unsubscribe von
            # Mail A mit dem One-Click-Post von Mail B und verspricht eine
            # Methode, die die Abmelde-Aktion (gleiche Quelle!) nicht einlöst.
            rows = conn.execute(
                "SELECT addr, name, cnt, first, last, list_unsubscribe, list_unsubscribe_post"
                " FROM (SELECT lower(from_addr) AS addr, from_name AS name,"
                "  COUNT(*) OVER w AS cnt, MIN(date_iso) OVER w AS first,"
                "  MAX(date_iso) OVER w AS last, list_unsubscribe, list_unsubscribe_post,"
                "  ROW_NUMBER() OVER (PARTITION BY lower(from_addr) ORDER BY date_iso DESC) AS rn"
                f"  FROM mails WHERE account=? AND list_unsubscribe != ''"
                f"  AND is_sent=0 AND from_addr != ''{extra}"
                "  WINDOW w AS (PARTITION BY lower(from_addr)))"
                " WHERE rn=1",
                (account, *extra_params),
            ).fetchall()
        subs = []
        for addr, name, count, first, last, lu, lup in rows:
            target = parse_list_unsubscribe(lu, lup)
            if target.one_click:
                method = "oneclick"
            elif target.mailto:
                method = "mailto"
            elif target.https:
                method = "link"
            else:
                method = "none"  # Header vorhanden, aber nichts Verwertbares (http:/kaputt)
            subs.append({
                "addr": addr, "name": name or addr, "count": count,
                "first_date": first, "last_date": last,
                "per_month": self._per_month(count, first, last),
                "method": method,
            })
        subs.sort(key=lambda s: s["per_month"], reverse=True)
        return subs

    def unsubscribe_header(self, account: str, addr: str) -> tuple[str, str] | None:
        """(list_unsubscribe, list_unsubscribe_post) der NEUESTEN Mail des
        Absenders — alte Abmelde-Links laufen gern ab."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT list_unsubscribe, list_unsubscribe_post FROM mails"
                " WHERE account=? AND lower(from_addr)=? AND list_unsubscribe != ''"
                " ORDER BY date_iso DESC LIMIT 1",
                (account, addr.strip().lower()),
            ).fetchone()
        return (row[0], row[1]) if row else None

    def first_contacts(self, account: str, days: int = 30,
                       exclude: list[str] | None = None) -> list[dict]:
        """Screener-Kandidaten: Absender, deren ERSTE Mail jünger als `days`
        ist und die nie Empfänger einer Gesendet-Mail waren (Token-Match —
        a@x.de darf nicht via Substring an petra@x.de andocken)."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        skip = {a.lower() for a in (exclude or [])}
        out = []
        with self._connect() as conn:
            extra, extra_params = self._hygiene_folders_sql(conn, account)
            rows = conn.execute(
                "SELECT lower(from_addr), MAX(from_name), COUNT(*),"
                " MIN(date_iso), MAX(date_iso), MAX(list_unsubscribe)"
                f" FROM mails WHERE account=? AND is_sent=0 AND from_addr != ''{extra}"
                " GROUP BY lower(from_addr) HAVING MIN(date_iso) >= ?"
                " ORDER BY MAX(date_iso) DESC LIMIT 200",
                (account, *extra_params, cutoff),
            ).fetchall()
            known = " " + " ".join(
                r[0].lower() for r in conn.execute(
                    "SELECT recipients FROM mails WHERE account=? AND is_sent=1", (account,))
            ) + " "
            for addr, name, count, first, last, lu in rows:
                if addr in skip or f" {addr} " in known:
                    continue
                newest = conn.execute(
                    "SELECT subject, snippet, folder, uid FROM mails"
                    " WHERE account=? AND lower(from_addr)=? AND is_sent=0"
                    " ORDER BY date_iso DESC LIMIT 1",
                    (account, addr),
                ).fetchone()
                subject, snippet, folder, uid = newest or ("", "", "", 0)
                out.append({
                    "addr": addr, "name": name or addr, "count": count,
                    "first_date": first, "last_date": last,
                    "has_unsubscribe": bool(lu),
                    "subject": subject, "snippet": snippet,
                    "folder": folder, "uid": uid,
                })
        return out
