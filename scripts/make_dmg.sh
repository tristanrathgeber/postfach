#!/bin/zsh
# Baut aus dist/Postfach.app ein Installations-Image: dist/Postfach-<version>.dmg
#
# Warum DMG statt ZIP: Doppelklick öffnet ein Fenster mit der App und einer
# Verknüpfung zu „Programme" — Rüberziehen, fertig. Kein Entpacken, kein
# Terminal, keine Frage wohin. Das ist der Weg, den Mac-Nutzer kennen.
#
# Voraussetzung: dist/Postfach.app existiert (scripts/build_app.sh).
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP="$REPO/dist/Postfach.app"
[ -d "$APP" ] || { echo "FEHLER: $APP fehlt — zuerst scripts/build_app.sh"; exit 1; }

VERSION="$(cd "$REPO/backend" && uv run python -c 'import postfach; print(postfach.__version__)' 2>/dev/null | tail -1)"
[ -n "$VERSION" ] || VERSION="dev"
DMG="$REPO/dist/Postfach-$VERSION.dmg"
STAGE="$REPO/build/dmg"

echo "→ Inhalt zusammenstellen (Version $VERSION)"
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
# Verknüpfung, damit im Fenster daneben „Programme" steht → Rüberziehen genügt.
ln -s /Applications "$STAGE/Programme"

# Beim ersten Start meldet macOS „nicht überprüft" (die App ist unsigniert —
# dafür bräuchte es einen kostenpflichtigen Apple-Developer-Account). Die
# Anleitung liegt deshalb SICHTBAR im Fenster daneben.
cat > "$STAGE/Zuerst lesen.txt" <<'TXT'
Postfach installieren
=====================

1. „Postfach" auf „Programme" ziehen.
2. In den Programmen einmal doppelklicken. macOS meldet, dass die App
   nicht überprüft werden konnte — das ist normal: Postfach ist ein
   Hobby-Projekt ohne kostenpflichtiges Apple-Entwicklerzertifikat.
3. Systemeinstellungen → Datenschutz & Sicherheit öffnen, dort unten bei
   der Meldung zu Postfach auf „Trotzdem öffnen" klicken. Einmalig.

Danach führt die App selbst weiter: Sie fragt direkt nach deinem
E-Mail-Konto (das Passwort landet im macOS-Schlüsselbund, nirgends sonst).

Für die KI-Funktionen (Emilia) zusätzlich Ollama installieren:
https://ollama.com — danach in Postfach ⌘K → „Modell-Assistent",
der lädt das passende Modell für deinen Mac in einem Klick.

Handbuch und Quellcode:
https://github.com/tristanrathgeber/postfach
TXT

echo "→ Image schreiben"
# UDZO = komprimiert und nur lesbar; -quiet, damit der Build-Log ruhig bleibt.
hdiutil create -quiet -volname "Postfach $VERSION" -srcfolder "$STAGE" \
  -ov -format UDZO "$DMG"
rm -rf "$STAGE"

echo "✓ $DMG  ($(du -sh "$DMG" | cut -f1))"
