#!/bin/zsh
# Baut ein ECHTES, portables Postfach.app (PyInstaller) nach dist/Postfach.app —
# kein uv/Node/Repo zur Laufzeit nötig, eingebettetes Python.
# Voraussetzungen zum BAUEN: uv, node/npm, macOS (iconutil). Nicht zur Laufzeit.
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"

echo "→ Frontend bauen"
cd "$REPO/frontend" && npm install --no-fund --no-audit >/dev/null && npm run build >/dev/null

echo "→ Build-Abhängigkeiten (PyInstaller, pywebview)"
cd "$REPO/backend" && uv sync --extra build >/dev/null

echo "→ Icon"
cd "$REPO" && uv run --project backend --with pillow python scripts/make_icon.py >/dev/null
iconutil -c icns -o "$REPO/dist/icon.icns" "$REPO/dist/icon.iconset"

echo "→ Binary bündeln (PyInstaller)"
cd "$REPO/backend"
uv run --extra build pyinstaller "$REPO/postfach.spec" --noconfirm \
  --distpath "$REPO/dist" --workpath "$REPO/build" >/dev/null

echo "✓ $REPO/dist/Postfach.app  ($(du -sh "$REPO/dist/Postfach.app" | cut -f1))"
echo "  Installieren:  cp -r \"$REPO/dist/Postfach.app\" /Applications/"
echo "  (Unsigniert — beim ersten Start Rechtsklick → Öffnen)"
