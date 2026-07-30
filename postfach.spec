# PyInstaller-Spec für Postfach.app — echtes macOS-Binary, kein uv/Node zur Laufzeit.
# Bauen: cd backend && uv run --extra build pyinstaller ../postfach.spec --noconfirm
#   (Voraussetzung: frontend/dist gebaut, dist/icon.icns erzeugt — s. scripts/build_app.sh)

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

REPO = os.path.abspath(os.getcwd() + "/..")  # gebaut aus backend/ heraus

# Version aus EINER Quelle lesen (postfach/__init__.py). Vorher stand sie hier
# dreimal hartkodiert und lief auseinander — das Bundle hätte dem eingebauten
# Update-Check eine falsche Version gemeldet.
_version_file = os.path.join(REPO, "backend", "src", "postfach", "__init__.py")
with open(_version_file, encoding="utf-8") as _f:
    for _line in _f:
        if _line.startswith("__version__"):
            VERSION = _line.split("=", 1)[1].strip().strip('"').strip("'")
            break
    else:
        raise SystemExit(f"__version__ nicht gefunden in {_version_file}")

datas, binaries, hiddenimports = [], [], []

# Ganze Pakete einsammeln (inkl. Daten/Untermodule) — email_agent ist Path-Dependency.
for pkg in ("postfach", "email_agent", "webview", "keyring", "icalendar", "nh3", "imapclient"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# uvicorn lädt seine Protokoll-/Loop-Module dynamisch → als Hidden-Imports.
hiddenimports += collect_submodules("uvicorn")
# pywebview-Cocoa + keyring-macOS brauchen die pyobjc-Frameworks.
hiddenimports += [
    "objc", "Foundation", "AppKit", "WebKit", "Cocoa", "Quartz", "Security",
    "keyring.backends.macOS", "email_agent.llm.ollama", "email_agent.cli",
]

# Das gebaute Frontend wird als Ressource mitgebündelt (resource_dir()/frontend/dist).
datas += [(os.path.join(REPO, "frontend", "dist"), "frontend/dist")]

a = Analysis(
    [os.path.join(REPO, "backend", "postfach_main.py")],
    pathex=[os.path.join(REPO, "backend", "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "PyInstaller"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="Postfach", console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Postfach")

app = BUNDLE(
    coll,
    name="Postfach.app",
    icon=os.path.join(REPO, "dist", "icon.icns"),
    bundle_identifier="app.postfach.desktop",
    version=VERSION,
    info_plist={
        "CFBundleName": "Postfach",
        "CFBundleDisplayName": "Postfach",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "LSUIElement": False,
    },
)
