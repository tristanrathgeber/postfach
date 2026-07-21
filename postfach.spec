# PyInstaller-Spec für Postfach.app — echtes macOS-Binary, kein uv/Node zur Laufzeit.
# Bauen: cd backend && uv run --extra build pyinstaller ../postfach.spec --noconfirm
#   (Voraussetzung: frontend/dist gebaut, dist/icon.icns erzeugt — s. scripts/build_app.sh)

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

REPO = os.path.abspath(os.getcwd() + "/..")  # gebaut aus backend/ heraus

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
    version="0.10.0",
    info_plist={
        "CFBundleName": "Postfach",
        "CFBundleDisplayName": "Postfach",
        "CFBundleShortVersionString": "0.10.0",
        "CFBundleVersion": "0.10.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "LSUIElement": False,
    },
)
