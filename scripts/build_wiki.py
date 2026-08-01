"""Baut das GitHub-Wiki aus docs/HANDBUCH.md — eine Seite je Kapitel.

Bewusst generiert statt von Hand kopiert: das Handbuch bleibt die Quelle,
das Wiki die navigierbare Fassung. Interne Anker (#14-modell-assistent-…)
werden dabei zu Wiki-Verweisen umgeschrieben.
"""
import re
import shutil
from pathlib import Path

HANDBUCH = Path(__file__).resolve().parent.parent / "docs" / "HANDBUCH.md"
WIKI = Path(__file__).resolve().parent.parent.parent / "postfach.wiki"  # Nachbar-Klon:
# git clone https://github.com/tristanrathgeber/postfach.wiki.git
RAW = "https://raw.githubusercontent.com/tristanrathgeber/postfach/main/docs/img"
REPO = "https://github.com/tristanrathgeber/postfach"

# Kapitelnummer → ASCII-Seitenname (Umlaute in Dateinamen vermeiden)
PAGES = {
    1: "Was-ist-Postfach", 2: "Erste-Schritte", 3: "Konten-einrichten",
    4: "Oberflaeche", 5: "Lesen", 6: "Schreiben", 7: "Senden-mit-Netz",
    8: "Ordnung-halten", 9: "Suchen", 10: "Abos-und-Screener", 11: "Emilia",
    12: "Kalender-und-Export", 13: "Farbthemen", 14: "Modell-Assistent",
    15: "Benachrichtigungen", 16: "Privatsphaere", 17: "Einstellungen",
    18: "Tastaturkuerzel", 19: "Diagnose", 20: "FAQ",
}

text = HANDBUCH.read_text(encoding="utf-8")

# --- Kapitel zerlegen -------------------------------------------------------
parts = re.split(r"^## (\d+)\. (.+)$", text, flags=re.M)
# parts: [vorspann, nr, titel, inhalt, nr, titel, inhalt, ...]
chapters = []
for i in range(1, len(parts), 3):
    num, title, body = int(parts[i]), parts[i + 1].strip(), parts[i + 2]
    chapters.append((num, title, body.strip().rstrip("-").strip()))

assert len(chapters) == 20, f"erwartet 20 Kapitel, gefunden {len(chapters)}"


def slug(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    return s.replace(" ", "-")


# Anker („#14-modell-assistent-cookbook") → Seitenname
anchor_to_page = {f"#{n}-{slug(t)}": PAGES[n] for n, t, _ in chapters}


def rewrite_links(body: str) -> str:
    def repl(match):
        label, anchor = match.group(1), match.group(2)
        page = anchor_to_page.get(anchor)
        return f"[{label}]({page})" if page else match.group(0)

    return re.sub(r"\[([^\]]+)\]\((#[^)]+)\)", repl, body)


# --- Seiten schreiben -------------------------------------------------------
for path in WIKI.glob("*.md"):
    path.unlink()

count = len(chapters)
for idx, (num, title, body) in enumerate(chapters):
    page = PAGES[num]
    nav = []
    if idx > 0:
        prev_num, prev_title, _ = chapters[idx - 1]
        nav.append(f"← [{prev_title}]({PAGES[prev_num]})")
    if idx < count - 1:
        next_num, next_title, _ = chapters[idx + 1]
        nav.append(f"[{next_title}]({PAGES[next_num]}) →")
    footer = "\n\n---\n\n" + "  ·  ".join(nav) if nav else ""
    content = f"# {title}\n\n{rewrite_links(body)}{footer}\n"
    (WIKI / f"{page}.md").write_text(content, encoding="utf-8")

# --- Seitenleiste -----------------------------------------------------------
sidebar = ["### Postfach-Handbuch\n", "**[Startseite](Home)**\n"]
for num, title, _ in chapters:
    sidebar.append(f"{num}. [{title}]({PAGES[num]})")
sidebar += [
    "\n---\n",
    f"[Quellcode]({REPO})",
    f"[Neuestes Release]({REPO}/releases/latest)",
    f"[Fehler melden]({REPO}/issues/new/choose)",
    f"[Diskussionen]({REPO}/discussions)",
]
(WIKI / "_Sidebar.md").write_text("\n".join(sidebar) + "\n", encoding="utf-8")

(WIKI / "_Footer.md").write_text(
    f"Postfach ist quelloffen (MIT) · [Repository]({REPO}) · "
    f"[Handbuch als eine Datei]({REPO}/blob/main/docs/HANDBUCH.md)\n",
    encoding="utf-8",
)

# --- Startseite -------------------------------------------------------------
toc = "\n".join(f"{num}. **[{title}]({PAGES[num]})**" for num, title, _ in chapters)
home = f"""# Postfach — Handbuch

**Postfach** ist eine local-first Mail-App für macOS: deine Mails bleiben auf
deinem Mac, es gibt keine Telemetrie, und der KI-Copilot **Emilia** rechnet
lokal über [Ollama](https://ollama.com).

Dieses Wiki erklärt jede Funktion — von der Installation bis zum letzten
Tastaturkürzel.

![Postfach — Posteingang mit geöffneter Mail]({RAW}/01-posteingang.png)

## Schnellstart

1. **[Neuestes Release]({REPO}/releases/latest)** herunterladen (`.dmg`).
2. Doppelklicken und **„Postfach" auf „Programme" ziehen**.
3. Einmal öffnen. macOS meldet Bedenken, weil die App unsigniert ist →
   **Systemeinstellungen → Datenschutz & Sicherheit → „Trotzdem öffnen"**.
4. Die App fragt direkt nach deinem Konto — das Passwort landet im
   macOS-Schlüsselbund.
5. Für die KI: **⌘K → „Modell-Assistent"** → *Ollama einrichten*, dann
   *Laden & aktivieren*. Postfach lädt alles selbst.

Ausführlich: **[Erste Schritte](Erste-Schritte)** ·
**[Konten einrichten](Konten-einrichten)** ·
**[Modell-Assistent](Modell-Assistent)**

## Alle Kapitel

{toc}

## Häufig gebraucht

- **[Tastaturkürzel](Tastaturkuerzel)** — die komplette Referenz
- **[Suchen](Suchen)** — Operatoren und natürlichsprachige Suche
- **[Privatsphäre](Privatsphaere)** — was nach außen geht, nachprüfbar
- **[Diagnose & Fehlerberichte](Diagnose)** — wenn etwas hakt
- **[Häufige Fragen](FAQ)** — Problemlösungen

## Mitreden

Fehler bitte als **[Issue]({REPO}/issues/new/choose)**, Fragen und Ideen in den
**[Diskussionen]({REPO}/discussions)**. Sicherheitslücken **nicht** öffentlich —
siehe [SECURITY.md]({REPO}/blob/main/SECURITY.md).

> Dieses Wiki wird aus [`docs/HANDBUCH.md`]({REPO}/blob/main/docs/HANDBUCH.md)
> erzeugt. Inhaltliche Änderungen bitte dort.
"""
(WIKI / "Home.md").write_text(home, encoding="utf-8")

print(f"{count} Kapitelseiten + Home + _Sidebar + _Footer geschrieben")
for p in sorted(WIKI.glob("*.md")):
    print(f"  {p.name:34} {p.stat().st_size:>6} B")
