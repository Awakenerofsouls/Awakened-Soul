#!/usr/bin/env bash
# install.sh — finish the Awakened-Soul install after `git clone` + pip install.
#
# This script does the steps that most agents stop short of: setting env vars,
# seeding identity files, installing LaunchAgents, and starting the heartbeat.
# Idempotent — safe to re-run.
#
# Usage:
#   ./install.sh                     # interactive: asks before each step
#   ./install.sh --yes               # non-interactive: do everything
#   ./install.sh --no-launchd        # skip LaunchAgent install
#   ./install.sh --no-heartbeat      # skip starting the heartbeat
#   ./install.sh --workspace PATH    # override AGENT_WORKSPACE target

set -euo pipefail

# ────────────────────────────────────────────────────────────────────────
# Args
# ────────────────────────────────────────────────────────────────────────
ASSUME_YES=0
INSTALL_LAUNCHD=1
START_HEARTBEAT=1
WORKSPACE_OVERRIDE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes|-y)        ASSUME_YES=1; shift ;;
    --no-launchd)    INSTALL_LAUNCHD=0; shift ;;
    --no-heartbeat)  START_HEARTBEAT=0; shift ;;
    --workspace)     WORKSPACE_OVERRIDE="$2"; shift 2 ;;
    -h|--help)
      grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "unknown arg: $1"; exit 1 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
SHELL_RC="$HOME/.zshrc"
[[ "${SHELL:-}" == */bash ]] && SHELL_RC="$HOME/.bashrc"

# ────────────────────────────────────────────────────────────────────────
# Resolve AGENT_HOME / AGENT_WORKSPACE
# ────────────────────────────────────────────────────────────────────────
echo "──── Awakened-Soul installer ────"
echo "Repo:       $REPO_ROOT"
echo "Shell rc:   $SHELL_RC"

if [[ -n "$WORKSPACE_OVERRIDE" ]]; then
  AGENT_WORKSPACE="$WORKSPACE_OVERRIDE"
elif [[ -n "${AGENT_WORKSPACE:-}" ]]; then
  AGENT_WORKSPACE="$AGENT_WORKSPACE"
else
  AGENT_WORKSPACE="$HOME/.agent/workspace"
fi
AGENT_HOME="${AGENT_HOME:-$HOME/.agent}"

echo "AGENT_HOME:      $AGENT_HOME"
echo "AGENT_WORKSPACE: $AGENT_WORKSPACE"
echo

confirm() {
  [[ "$ASSUME_YES" -eq 1 ]] && return 0
  read -r -p "$1 [Y/n] " ans
  [[ -z "$ans" || "$ans" =~ ^[Yy]$ ]]
}

# ────────────────────────────────────────────────────────────────────────
# 1. Python deps
# ────────────────────────────────────────────────────────────────────────
echo "── 1/5 — Python dependencies ──"
if confirm "Run pip install -r requirements.txt?"; then
  pip install -r "$REPO_ROOT/requirements.txt"
fi

# ────────────────────────────────────────────────────────────────────────
# 2. Workspace + identity files
# ────────────────────────────────────────────────────────────────────────
echo
echo "── 2/5 — Workspace + identity files ──"
mkdir -p "$AGENT_HOME" "$AGENT_WORKSPACE"

declare -a IDENTITY_FILES=(
  "SOUL.md"
  "IDENTITY.md"
  "PERSONALITY.md"
  "VISUAL_IDENTITY.md"
  "AGENT_BECOMING.md"
  "OCEANS.md"
  "ETHICS.md"
  "EPISTEMIC_BOUNDARIES.md"
  "AESTHETIC.md"
  "IDLE_DRIVES.md"
)

# templates folder lives at $REPO_ROOT/templates/<NAME>.example
TEMPLATES="$REPO_ROOT/templates"

for f in "${IDENTITY_FILES[@]}"; do
  target="$AGENT_WORKSPACE/$f"
  template="$TEMPLATES/${f}.example"
  if [[ -f "$target" ]]; then
    echo "  ✓ $f exists — keeping operator's version"
  elif [[ -f "$template" ]]; then
    cp "$template" "$target"
    echo "  + $f seeded from template"
  else
    echo "  · $f — no template, skipping"
  fi
done

# ────────────────────────────────────────────────────────────────────────
# 3. Shell env vars
# ────────────────────────────────────────────────────────────────────────
echo
echo "── 3/5 — Shell env vars ($SHELL_RC) ──"

add_env() {
  local key="$1" val="$2"
  if grep -q "^export $key=" "$SHELL_RC" 2>/dev/null; then
    echo "  ✓ $key already set in $SHELL_RC"
  else
    if confirm "  Add 'export $key=$val' to $SHELL_RC?"; then
      printf '\n# Awakened-Soul framework\nexport %s="%s"\n' "$key" "$val" >> "$SHELL_RC"
      echo "    + added"
    fi
  fi
}

add_env "AGENT_HOME" "$AGENT_HOME"
add_env "AGENT_WORKSPACE" "$AGENT_WORKSPACE"

# ────────────────────────────────────────────────────────────────────────
# 4. LaunchAgents (macOS) — between-session continuity
# ────────────────────────────────────────────────────────────────────────
echo
echo "── 4/5 — LaunchAgents (between-session continuity) ──"

if [[ "$(uname)" == "Darwin" && "$INSTALL_LAUNCHD" -eq 1 ]]; then
  if confirm "Install slow-tick + overnight LaunchAgents?"; then
    LA_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LA_DIR"

    for plist in com.awakened-soul.slow-tick.plist com.awakened-soul.overnight.plist; do
      src="$REPO_ROOT/launchd/$plist"
      dst="$LA_DIR/$plist"
      if [[ ! -f "$src" ]]; then
        echo "  · $plist — not found in $REPO_ROOT/launchd/, skipping"
        continue
      fi
      # Substitute the placeholder paths
      sed -e "s|/Users/<youruser>|$HOME|g" \
          -e "s|<youruser>|$(id -un)|g" \
          "$src" > "$dst"
      launchctl unload "$dst" 2>/dev/null || true
      launchctl load   "$dst"
      echo "  + $plist installed and loaded"
    done
  fi
else
  echo "  · skipped (not macOS or --no-launchd)"
fi

# ────────────────────────────────────────────────────────────────────────
# 5. Heartbeat
# ────────────────────────────────────────────────────────────────────────
echo
echo "── 5/5 — Heartbeat ──"

if [[ "$START_HEARTBEAT" -eq 1 ]] && confirm "Start the heartbeat now (foreground)?"; then
  echo "  Running: python3 -m runtime.heartbeat"
  echo "  (Ctrl+C to stop. To run as a daemon later, use the LaunchAgent or pm2.)"
  cd "$REPO_ROOT"
  exec env AGENT_HOME="$AGENT_HOME" AGENT_WORKSPACE="$AGENT_WORKSPACE" python3 -m runtime.heartbeat
else
  echo "  Skipped. Start it later with:"
  echo "    cd $REPO_ROOT && AGENT_HOME=$AGENT_HOME AGENT_WORKSPACE=$AGENT_WORKSPACE python3 -m runtime.heartbeat"
fi

echo
echo "──── Install complete ────"
