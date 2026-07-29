"""Ollama einrichten, ohne dass der Nutzer irgendwo etwas herunterladen muss.

Postfach holt die offizielle, aktuelle Ollama-Ausgabe selbst, prüft sie gegen
die von GitHub veröffentlichte SHA-256-Summe und legt sie NEBEN die eigenen
Daten (`<root>/ollama/`). Bewusst so:

- **Kein Administrator nötig**, kein Eingriff ins System, nichts in /Applications.
- **Keine Kollision** mit einer vorhandenen Ollama-Installation: läuft schon ein
  Server, wird der benutzt und gar nichts geladen.
- **Nicht mitgeliefert, sondern geladen**: das Archiv ist ~145 MB und Ollama
  bekommt Sicherheitsaktualisierungen. Eine ins Bundle kopierte Fassung würde
  veralten und läge in unserer Verantwortung. Modelle müssen ohnehin geladen
  werden — der Download passt in denselben Ablauf.
- **Verifiziert**: die Summe kommt aus derselben API-Antwort wie die URL, nicht
  aus einer fest eingetragenen Konstante, die still veralten könnte.

Ollama steht unter der MIT-Lizenz (Mitliefern wäre erlaubt, siehe oben warum
nicht). Die Lizenz wird beim Einrichten neben das Archiv gelegt.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

_RELEASES_URL = "https://api.github.com/repos/ollama/ollama/releases/latest"
_ASSET_NAME = "ollama-darwin.tgz"
_CHUNK = 1 << 20  # 1 MiB


class OllamaSetupError(RuntimeError):
    """Einrichten fehlgeschlagen — die Meldung ist für den Nutzer gedacht."""


def ollama_dir(root: Path) -> Path:
    return Path(root) / "ollama"


def ollama_binary(root: Path) -> Path:
    return ollama_dir(root) / "ollama"


def is_installed(root: Path) -> bool:
    """Von Postfach eingerichtetes Ollama vorhanden und ausführbar?"""
    binary = ollama_binary(root)
    return binary.is_file() and os.access(binary, os.X_OK)


def server_reachable(base_url: str, timeout: float = 1.5) -> bool:
    """Läuft irgendein Ollama-Server (eigener ODER vom Nutzer installierter)?"""
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def pick_asset(release: dict) -> tuple[str, str, str]:
    """(Version, URL, sha256) des darwin-Archivs aus einer GitHub-Release-Antwort.

    Die Prüfsumme stammt aus derselben Antwort wie die URL — beides über HTTPS
    von api.github.com.
    """
    version = str(release.get("tag_name") or "").lstrip("vV")
    for asset in release.get("assets") or []:
        if asset.get("name") == _ASSET_NAME:
            url = str(asset.get("browser_download_url") or "")
            digest = str(asset.get("digest") or "")
            sha = digest.split(":", 1)[1] if digest.startswith("sha256:") else ""
            if not url:
                raise OllamaSetupError("Ollama-Download-Adresse fehlt in der GitHub-Antwort.")
            if not sha:
                raise OllamaSetupError(
                    "GitHub liefert keine Prüfsumme für das Ollama-Archiv — "
                    "Abbruch, statt etwas Unverifiziertes auszuführen."
                )
            return version, url, sha
    raise OllamaSetupError(f"Kein „{_ASSET_NAME}“ in der neuesten Ollama-Ausgabe gefunden.")


def latest_release() -> dict:
    try:
        response = httpx.get(_RELEASES_URL, timeout=20,
                             headers={"Accept": "application/vnd.github+json"})
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OllamaSetupError(f"Ollama-Ausgaben nicht abrufbar (offline?): {exc}") from exc


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _within(path: Path, root: Path) -> bool:
    """Liegt `path` (aufgelöst) innerhalb von `root`?"""
    resolved, base = path.resolve(), root.resolve()
    return resolved == base or base in resolved.parents


def _is_safe_member(member: tarfile.TarInfo, dest: Path) -> bool:
    """Darf dieser Archiv-Eintrag geschrieben werden?

    Ein Archiv aus dem Netz darf NICHT nach „../.." oder an einen absoluten
    Pfad schreiben, und ein Verweis darf nicht aus dem Zielverzeichnis
    hinausführen (ein Symlink auf /etc/hosts könnte sonst eine Systemdatei
    überschreiben). Geprüft wird jeweils der AUFGELÖSTE Pfad — den Namen allein
    zu prüfen ließe sich umgehen.

    Symlinks sind erlaubt, solange sie im Ziel bleiben: versionierte
    Bibliotheken (libfoo.dylib → libfoo.1.dylib) sind auf macOS normal, und
    Ollamas Archiv enthält genau solche. Ein pauschales Verbot machte das
    Einrichten unmöglich.
    """
    if member.isdev() or member.isfifo():
        return False
    if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
        return False

    name = Path(member.name)
    if name.is_absolute() or ".." in name.parts:
        return False
    if not _within(dest / name, dest):
        return False

    if member.issym() or member.islnk():
        link = Path(member.linkname)
        if link.is_absolute():
            return False
        # Symlink: relativ zum Verzeichnis des Eintrags. Hardlink: relativ zur
        # Archivwurzel (also zum Zielverzeichnis).
        base = (dest / name).parent if member.issym() else dest
        if not _within(base / link, dest):
            return False
    return True


def extract_archive(archive: Path, dest: Path) -> None:
    """Archiv entpacken — jeder Eintrag wird vorher einzeln geprüft.

    Bewusst NICHT extractall über das ganze Archiv: hier wird Eintrag für
    Eintrag validiert (siehe _is_safe_member) und zusätzlich Pythons
    „data"-Filter angewandt. Ein unsauberer Eintrag bricht ab, statt
    stillschweigend übersprungen zu werden.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if not _is_safe_member(member, dest):
                raise OllamaSetupError(
                    f"Archiv-Eintrag „{member.name}“ ist nicht sicher entpackbar — Abbruch."
                )
            tar.extract(member, dest, filter="data")


def install(root: Path, progress=None) -> Path:
    """Ollama herunterladen, verifizieren, entpacken. Gibt den Binärpfad zurück.

    progress(done_bytes, total_bytes, phase) wird laufend gerufen (optional).
    """

    def report(done: int, total: int, phase: str) -> None:
        if progress:
            progress(done, total, phase)

    report(0, 0, "Neueste Ollama-Ausgabe suchen")
    version, url, expected_sha = pick_asset(latest_release())

    target = ollama_dir(root)
    with tempfile.TemporaryDirectory(prefix="postfach-ollama-") as tmp:
        archive = Path(tmp) / _ASSET_NAME
        report(0, 0, f"Ollama {version} wird geladen")
        try:
            with httpx.stream("GET", url, timeout=None, follow_redirects=True) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length") or 0)
                done = 0
                with open(archive, "wb") as handle:
                    for block in response.iter_bytes(_CHUNK):
                        handle.write(block)
                        done += len(block)
                        report(done, total, f"Ollama {version} wird geladen")
        except httpx.HTTPError as exc:
            raise OllamaSetupError(f"Download fehlgeschlagen: {exc}") from exc

        report(0, 0, "Prüfsumme vergleichen")
        actual = sha256_of(archive)
        if actual != expected_sha:
            raise OllamaSetupError(
                "Die Prüfsumme des Downloads stimmt nicht mit der von GitHub "
                "veröffentlichten überein — nichts wurde installiert."
            )

        report(0, 0, "Entpacken")
        staging = Path(tmp) / "out"
        extract_archive(archive, staging)
        if not (staging / "ollama").is_file():
            raise OllamaSetupError("Im Archiv fehlt das Programm „ollama“.")
        # Erst jetzt das alte Verzeichnis ersetzen — ein Fehler oben lässt eine
        # vorhandene, funktionierende Installation unangetastet.
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), str(target))

    binary = ollama_binary(root)
    binary.chmod(0o755)
    (target / "LIZENZ-Ollama.txt").write_text(
        "Ollama steht unter der MIT-Lizenz: https://github.com/ollama/ollama/blob/main/LICENSE\n"
        f"Hier eingerichtete Fassung: {version}\n",
        encoding="utf-8",
    )
    log.info("Ollama %s eingerichtet: %s", version, binary)
    return binary


def start_server(root: Path, base_url: str) -> subprocess.Popen | None:
    """Den eingerichteten Ollama-Server starten (Kindprozess, kein System-Dienst).

    Gibt None zurück, wenn nichts eingerichtet ist. Läuft schon ein Server,
    wird KEIN zweiter gestartet — der Port wäre belegt.
    """
    if not is_installed(root):
        return None
    if server_reachable(base_url):
        return None
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    env = dict(os.environ)
    env["OLLAMA_HOST"] = f"{parsed.hostname or '127.0.0.1'}:{parsed.port or 11434}"
    log.info("Starte eingerichteten Ollama-Server (%s)", env["OLLAMA_HOST"])
    return subprocess.Popen(
        [str(ollama_binary(root)), "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # überlebt nicht als Zombie am Terminal
    )
