#!/bin/zsh
# Baut Postfach.app (natives macOS-Programm) nach dist/Postfach.app.
# Voraussetzungen: uv, node/npm (fürs Frontend), macOS (iconutil).
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP="$REPO/dist/Postfach.app"

echo "→ Frontend bauen"
cd "$REPO/frontend" && npm install --no-fund --no-audit >/dev/null && npm run build >/dev/null

echo "→ Backend-Abhängigkeiten (inkl. Desktop)"
cd "$REPO/backend" && uv sync --extra desktop >/dev/null

echo "→ Icon"
cd "$REPO" && uv run --project backend --with pillow python scripts/make_icon.py >/dev/null
iconutil -c icns -o "$REPO/dist/icon.icns" "$REPO/dist/icon.iconset"

echo "→ App-Bundle"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$REPO/dist/icon.icns" "$APP/Contents/Resources/icon.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>Postfach</string>
    <key>CFBundleDisplayName</key><string>Postfach</string>
    <key>CFBundleIdentifier</key><string>app.postfach.desktop</string>
    <key>CFBundleVersion</key><string>0.2.0</string>
    <key>CFBundleShortVersionString</key><string>0.2</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>Postfach</string>
    <key>CFBundleIconFile</key><string>icon</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>LSMinimumSystemVersion</key><string>12.0</string>
</dict>
</plist>
PLIST

cat > "$APP/Contents/MacOS/Postfach" <<LAUNCHER
#!/bin/zsh
# Von build_app.sh erzeugt — Repo-Pfad ist fest eingebrannt.
export PATH="\$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH"
cd "$REPO/backend"
exec uv run --extra desktop postfach-app
LAUNCHER
chmod +x "$APP/Contents/MacOS/Postfach"

echo "✓ $APP"
echo "  Installieren:  cp -r \"$APP\" /Applications/"
echo "  (Unsigniert — beim ersten Start Rechtsklick → Öffnen)"
