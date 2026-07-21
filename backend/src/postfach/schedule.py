"""Lokale Zeit-Warteschlange: Undo-Send, Später senden, Snooze, Follow-up.

Jobs liegen neustartfest in data/schedule.json (Muster wie DraftStore);
Send-Payloads inkl. Anhänge in data/outbox/. Der Scheduler-Kern ist
synchron und testbar (process_due(now)); den 20-s-Takt gibt ein
Daemon-Thread in app.py vor.

Sicherheits-Invariante: Send-Jobs entstehen AUSSCHLIESSLICH aus expliziten
Senden-Klicks (POST /api/send) — kein KI-/Automatik-Pfad legt sie an
(tests/test_safety.py erzwingt, dass ai/emilia dieses Modul nie importieren).
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from .stores import _JsonFile

log = logging.getLogger("postfach.schedule")

_MAX_ATTEMPTS = 3
_TICK_SECONDS = 20


def _validate_due(due: str) -> str:
    """Der Zeitvergleich ist ISO-String-Lexikografie — Müll wäre nie fällig.
    Aware Zeiten werden auf naive Lokalzeit normalisiert (eine Konvention)."""
    parsed = datetime.fromisoformat(due)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.isoformat(timespec="seconds")


def is_later(candidate: str, reference: str) -> bool:
    """Zeitvergleich über Zonen hinweg: Mail-Header tragen beliebige Offsets,
    lokale Zeiten sind naiv — Stringvergleich würde UTC-Antworten übersehen."""
    def aware(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone() if parsed.tzinfo else parsed.astimezone()

    try:
        return aware(candidate) > aware(reference)
    except ValueError:
        return candidate > reference  # defensiv: unparsebar → alte Semantik


class ScheduleStore(_JsonFile):
    """Jobs: {id, kind, account, due (iso), payload, attempts, created}."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, [])

    def add(self, kind: str, account: str, due: str, payload: dict) -> str:
        due = _validate_due(due)  # wirft ValueError bei Müll → Route macht 422
        job_id = str(uuid.uuid4())
        with self._lock:
            jobs = self._read()
            jobs.append({
                "id": job_id, "kind": kind, "account": account, "due": due,
                "payload": payload, "attempts": 0,
                "created": datetime.now().isoformat(),
            })
            self._write(jobs)
        return job_id

    def list(self, account: str) -> list[dict]:
        with self._lock:
            jobs = self._read()
        return sorted((j for j in jobs if j["account"] == account), key=lambda j: j["due"])

    def due(self, now: str) -> list[dict]:
        with self._lock:
            jobs = self._read()
        return [j for j in jobs if j["due"] <= now]

    def remove(self, job_id: str) -> bool:
        with self._lock:
            jobs = self._read()
            remaining = [j for j in jobs if j["id"] != job_id]
            if len(remaining) == len(jobs):
                return False
            self._write(remaining)
        return True

    def find_snooze(self, account: str, message_id: str) -> dict | None:
        with self._lock:
            jobs = self._read()
        for j in jobs:
            if j["account"] == account and j["kind"] == "snooze" and j["payload"].get("message_id") == message_id:
                return j
        return None

    def add_back(self, job: dict) -> None:
        """Geclaimten Job zurücklegen (Sendefehler → Retry)."""
        with self._lock:
            jobs = self._read()
            jobs.append(job)
            self._write(jobs)

    def update(self, job: dict) -> None:
        with self._lock:
            jobs = [job if j["id"] == job["id"] else j for j in self._read()]
            self._write(jobs)


class OutboxStore:
    """Send-Payloads (JSON + Anhang-Blobs) für verzögerte Sends."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def _dir(self, job_id: str) -> Path:
        return self._root / job_id

    def save(self, job_id: str, body: dict, attachments: list[tuple[str, str, bytes]]) -> None:
        folder = self._dir(job_id)
        folder.mkdir(parents=True, exist_ok=True)
        manifest = {
            "body": body,
            "attachments": [
                {"filename": name, "content_type": ctype, "blob": f"{i:03d}.bin"}
                for i, (name, ctype, _payload) in enumerate(attachments)
            ],
        }
        for i, (_name, _ctype, payload) in enumerate(attachments):
            (folder / f"{i:03d}.bin").write_bytes(payload)
        (folder / "job.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    def load(self, job_id: str):
        manifest_path = self._dir(job_id) / "job.json"
        if not manifest_path.exists():
            return None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        attachments = [
            (a["filename"], a["content_type"], (self._dir(job_id) / a["blob"]).read_bytes())
            for a in manifest["attachments"]
        ]
        return manifest["body"], attachments

    def delete(self, job_id: str) -> None:
        shutil.rmtree(self._dir(job_id), ignore_errors=True)


class Scheduler:
    """Synchroner Kern: process_due(now) arbeitet fällige Jobs ab.

    Handler werden injiziert (app.py verdrahtet die echten):
    - send_fn(job): führt den Versand aus (wirft bei Fehler)
    - wake_fn(job): holt eine gesnoozte Mail zurück
    - followup_fn(job) -> bool: True = Antwort kam, Job löst sich still
    - notify_fn(title, text): macOS-Meldung
    """

    def __init__(self, store: ScheduleStore, outbox: OutboxStore,
                 send_fn, wake_fn, followup_fn, notify_fn) -> None:
        self._store = store
        self._outbox = outbox
        self._send_fn = send_fn
        self._wake_fn = wake_fn
        self._followup_fn = followup_fn
        self._notify_fn = notify_fn

    def process_due(self, now: str) -> None:
        for job in self._store.due(now):
            try:
                self._process_one(job)
            except Exception:
                log.exception("Scheduler-Job %s (%s) fehlgeschlagen", job["id"], job["kind"])
                self._register_failure(job)

    def _process_one(self, job: dict) -> None:
        kind = job["kind"]
        if kind == "send":
            # Job VOR dem Versand claimen: ein paralleles Storno sieht dann
            # ehrlich 404 statt eine bereits laufende Mail zu "stornieren".
            if not self._store.remove(job["id"]):
                return  # zwischenzeitlich storniert
            try:
                self._send_fn(job)
            except Exception:
                self._store.add_back(job)  # zurück in die Schlange → Retry-Zählung
                raise
            self._outbox.delete(job["id"])
        elif kind == "snooze":
            self._wake_fn(job)
            self._store.remove(job["id"])
        elif kind == "followup":
            if self._followup_fn(job):
                self._store.remove(job["id"])  # Antwort kam — still auflösen
            else:
                job["kind"] = "followup_due"
                self._store.update(job)
                subject = job["payload"].get("subject", "")
                self._notify_fn("Keine Antwort erhalten", subject or "Wiedervorlage fällig")
        # *_failed / followup_due: warten auf den Nutzer, nichts tun

    def _register_failure(self, job: dict) -> None:
        # Deckel für ALLE Job-Arten — ein kaputter Job darf nicht alle 20 s
        # den Log fluten und ewig weiterprobieren.
        job["attempts"] = job.get("attempts", 0) + 1
        if job["attempts"] >= _MAX_ATTEMPTS and not job["kind"].endswith("_failed"):
            base = job["kind"]
            job["kind"] = f"{base}_failed"
            subject = job["payload"].get("subject", "")
            titles = {"send": "Senden fehlgeschlagen", "snooze": "Wiedervorlage fehlgeschlagen"}
            self._notify_fn(titles.get(base, "Zeitplan-Job fehlgeschlagen"), subject or job["id"])
        self._store.update(job)


def start_scheduler_thread(scheduler: Scheduler) -> threading.Thread:
    def run() -> None:
        while True:
            time.sleep(_TICK_SECONDS)
            try:
                scheduler.process_due(datetime.now().isoformat(timespec="seconds"))
            except Exception:
                log.exception("Scheduler-Tick fehlgeschlagen")

    thread = threading.Thread(target=run, daemon=True, name="scheduler")
    thread.start()
    return thread
