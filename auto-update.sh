#!/bin/bash
set -euo pipefail

# Override with the public repo path at deployment time:
#   AGENT_UPSTREAM_REPO=org/awakened-soul ./auto-update.sh --check
REPO="${AGENT_UPSTREAM_REPO:-}"
if [ -z "$REPO" ]; then
 echo "auto-update: AGENT_UPSTREAM_REPO not set — skipping" >&2
 exit 0
fi
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_FILE="$INSTALL_DIR/SKILL.md"
LOG_FILE="$INSTALL_DIR/.update.log"

get_installed_version() {
 local v
 v=$(grep '^version:' "$SKILL_FILE" 2>/dev/null | head -1 | awk '{print $2}' | tr -d '"')
 if [ -n "$v" ]; then
  echo "$v"
 else
  git -C "$INSTALL_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown"
 fi
}

get_latest_version() {
 curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep '"tag_name"' | head -1 | sed 's/.*"v\(.*\)".*/\1/'
}

pull_update() {
 git -C "$INSTALL_DIR" fetch origin main --quiet
 # Refuse to update if local tree is dirty to avoid destructive overwrite.
 if [ -n "$(git -C "$INSTALL_DIR" status --porcelain)" ]; then
  echo "Skipped update: local changes detected" | tee -a "$LOG_FILE"
  return 1
 fi
 git -C "$INSTALL_DIR" pull --ff-only origin main --quiet
}

case "$1" in
 --install) 
  echo "0 9 * * * bash $INSTALL_DIR/auto-update.sh --check" | crontab -
  echo "Auto-update installed"
 ;;
 --check)
  INSTALLED=$(get_installed_version)
  LATEST=$(get_latest_version)
  if [ -n "$LATEST" ] && [ "$LATEST" != "$INSTALLED" ]; then
   echo "Update: $INSTALLED → $LATEST"
   pull_update
  fi
 ;;
esac
