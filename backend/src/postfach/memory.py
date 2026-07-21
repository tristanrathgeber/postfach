"""Emilias Mail-Gedächtnis: SQLite + Embeddings, vollständig lokal.

Kein Volltext-Upload irgendwohin — Embeddings kommen vom lokalen Ollama
(all-minilm), gespeichert wird in data/memory.db (gitignored).
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import threading
import zlib
from pathlib import Path

import httpx

# Automaten-Absender (kein Mensch antwortet): geteilt zwischen Kontakt-Ernte
# und Screener-Heuristik — EINE Liste, die nicht auseinanderdriftet.
NOREPLY_RE = re.compile(
    r"^(no[-_]?reply|do[-_]?not[-_]?reply|donotreply|newsletter|news|mailing"
    r"|notifications?|updates?|info|mailer-daemon|postmaster|bounces?|daemon)[@.+\-_]",
    re.I,
)


class FakeEmbedder:
    """Deterministisch, ohne Ollama — für Tests und Demo-Modus.
    Wort-Hash-Bag: Texte mit Wort-Überlappung bekommen ähnliche Vektoren."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * 64
            for word in re.findall(r"\w+", text.lower()):
                vector[zlib.crc32(word.encode()) % 64] += 1.0
            vectors.append(vector)
        return vectors


class OllamaEmbedder:
    _CHUNK = 64  # Ollama lehnt sehr große Batches mit 400 ab

    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self._model = model
        self._url = base_url.rstrip("/")

    def _request(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{self._url}/api/embed", json={"model": self._model, "input": texts}, timeout=120
        )
        response.raise_for_status()
        return response.json()["embeddings"]

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        dim: int | None = None
        for start in range(0, len(texts), self._CHUNK):
            chunk = texts[start : start + self._CHUNK]
            try:
                batch = self._request(chunk)
            except httpx.HTTPStatusError:
                # Ein Text im Chunk ist Ollama nicht genehm → einzeln versuchen,
                # nur der tatsächlich kaputte bekommt einen Platzhalter-Vektor.
                batch = []
                for text in chunk:
                    try:
                        batch.extend(self._request([text]))
                    except httpx.HTTPStatusError:
                        batch.append([0.0] * (dim or (len(batch[0]) if batch else 384)))
            if batch and dim is None:
                dim = len(batch[0])
            embeddings.extend(batch)
        return embeddings


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class MailMemory:
    def __init__(self, db_path: Path, embedder) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._embedder = embedder
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS mails ("
                "account TEXT, folder TEXT, uid INTEGER,"
                "subject TEXT, from_name TEXT, from_addr TEXT, date TEXT,"
                "snippet TEXT, embedding TEXT,"
                "PRIMARY KEY (account, folder, uid))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS contacts ("
                "addr TEXT PRIMARY KEY, name TEXT, weight REAL, last_seen TEXT)"
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        # SQLites eingebautes LOWER() foldet nur ASCII — „MÜLLER" bliebe bei
        # der Namenssuche unauffindbar. Pythons str.lower kann Unicode.
        conn.create_function("lower", 1, lambda s: s.lower() if isinstance(s, str) else s)
        return conn

    @staticmethod
    def _embed_text(entry: dict) -> str:
        text = f"{entry['subject']}\n{entry['from_name']}\n{entry['snippet']}"
        # Steuerzeichen raus (außer Zeilenumbruch/Tab); hart kappen — sehr lange
        # Eingaben quittiert Ollama mit 400, und minilm sieht eh nur ~256 Token.
        return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text)[:1500]

    def upsert_many(self, entries: list[dict]) -> None:
        # Mails sind unveränderlich — bereits indexierte UIDs überspringen,
        # sonst rechnet jeder Push-/Re-Index dieselben Embeddings neu.
        with self._lock, self._connect() as conn:
            known = set(conn.execute("SELECT account, folder, uid FROM mails"))
        entries = [e for e in entries if (e["account"], e["folder"], e["uid"]) not in known]
        if not entries:
            return
        embeddings = self._embedder.embed([self._embed_text(e) for e in entries])
        with self._lock, self._connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO mails VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    (
                        e["account"], e["folder"], e["uid"], e["subject"], e["from_name"],
                        e["from_addr"], e["date"], e["snippet"], json.dumps(emb),
                    )
                    for e, emb in zip(entries, embeddings)
                ],
            )

    def count(self, account: str) -> int:
        with self._connect() as conn:
            [(n,)] = conn.execute("SELECT COUNT(*) FROM mails WHERE account=?", (account,))
        return n

    def count_all(self) -> int:
        with self._connect() as conn:
            [(n,)] = conn.execute("SELECT COUNT(*) FROM mails")
        return n

    # --- Kontakte (für Empfänger-Autocomplete) ---

    _NOREPLY_RE = NOREPLY_RE

    def upsert_contacts(self, entries: list[tuple[str, str, float, str]]) -> None:
        """entries: (name, addr, gewicht, datum-iso). Gewicht kumuliert —
        Empfänger eigener Mails zählen höher als Einmal-Absender."""
        rows = []
        for name, addr, weight, date in entries:
            addr = addr.strip().lower()
            if not addr or "@" not in addr or self._NOREPLY_RE.match(addr):
                continue
            rows.append((addr, name.strip(), weight, date))
        if not rows:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                "INSERT INTO contacts (addr, name, weight, last_seen) VALUES (?,?,?,?) "
                "ON CONFLICT(addr) DO UPDATE SET "
                "weight = weight + excluded.weight, "
                "name = CASE WHEN excluded.name != '' THEN excluded.name ELSE contacts.name END, "
                "last_seen = MAX(contacts.last_seen, excluded.last_seen)",
                rows,
            )

    def search_contacts(self, query: str, limit: int = 8) -> list[dict]:
        needle = f"%{query.strip().lower()}%"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, addr FROM contacts "
                "WHERE addr LIKE ? OR LOWER(name) LIKE ? "
                "ORDER BY weight DESC, last_seen DESC LIMIT ?",
                (needle, needle, limit),
            ).fetchall()
        return [{"name": name, "addr": addr} for name, addr in rows]

    def search(self, account: str, query: str, k: int = 6) -> list[dict]:
        """Hybrid: Cosine-Ähnlichkeit + lexikalischer Bonus für Worttreffer.

        Der Bonus ist essenziell: kleine (englisch-lastige) Embedding-Modelle
        verfehlen deutsche Eigennamen, die wörtlich im Betreff stehen."""
        [query_vector] = self._embedder.embed([query])
        terms = {w for w in re.findall(r"\w+", query.lower()) if len(w) > 2}
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT folder, uid, subject, from_name, from_addr, date, snippet, embedding "
                "FROM mails WHERE account=?",
                (account,),
            ).fetchall()
        scored = []
        for folder, uid, subject, from_name, from_addr, date, snippet, embedding in rows:
            score = _cosine(query_vector, json.loads(embedding))
            head = f"{subject} {from_name} {from_addr}".lower()
            body = snippet.lower()
            lexical = sum(0.3 for t in terms if t in head) + sum(0.08 for t in terms if t in body)
            score += min(lexical, 1.2)
            scored.append((score, {
                "account": account, "folder": folder, "uid": uid, "subject": subject,
                "from_name": from_name, "from_addr": from_addr, "date": date, "snippet": snippet,
            }))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for score, entry in scored[:k] if score > 0.05]
