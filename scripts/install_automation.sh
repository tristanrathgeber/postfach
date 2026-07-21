#!/bin/zsh
# Installiert die Sortier-Automatik: der email-agent sortiert alle 30 Minuten
# neue Mails (--no-drafts: keine Antwortentwürfe im Hintergrund — die gibt es
# on-demand in der App; gesendet wird ohnehin nie).
#
# LaunchAgent im User-Scope — Deinstallation: scripts/uninstall_automation.sh
set -euo pipefail

AGENT_DIR="${EMAIL_AGENT_DIR:-$HOME/Projects/email-agent}"
LABEL="de.postfach.email-agent"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/postfach-email-agent.log"
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"

if [[ ! -d "$AGENT_DIR" ]]; then
  echo "email-agent nicht gefunden unter $AGENT_DIR (EMAIL_AGENT_DIR setzen?)" >&2
  exit 1
fi
if [[ ! -x "$UV" ]]; then
  echo "uv nicht gefunden ($UV) — sonst scheitert der launchd-Job still" >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$UV</string>
    <string>run</string>
    <string>--project</string>
    <string>$AGENT_DIR</string>
    <string>email-agent</string>
    <string>run</string>
    <string>--apply</string>
    <string>--no-drafts</string>
  </array>
  <key>WorkingDirectory</key><string>$AGENT_DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <!-- launchd kennt keinen Login-Shell-PATH — claude/uv/ollama liegen hier -->
    <key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
  <key>ProcessType</key><string>Background</string>
</dict>
</plist>
PLIST

# Neu laden, falls schon installiert
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installiert: $LABEL (alle 30 Min, Log: $LOG)"
echo "Sofort testen:  launchctl kickstart gui/$(id -u)/$LABEL"
echo "Deinstallieren: scripts/uninstall_automation.sh"
