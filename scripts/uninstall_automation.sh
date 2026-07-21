#!/bin/zsh
# Entfernt die Sortier-Automatik (Gegenstück zu install_automation.sh).
set -euo pipefail

LABEL="de.postfach.email-agent"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$PLIST"
echo "Entfernt: $LABEL"
