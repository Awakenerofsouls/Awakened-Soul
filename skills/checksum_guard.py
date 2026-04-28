#!/usr/bin/env python3
"""
checksum_guard.py
Daily checksum verification for protected identity files.
Runs via cron — checks SHA256 hash of SOUL.md and IDENTITY.md against known baseline.
Alerts via Telegram if hash changes unexpectedly.

{{USER_NAME}} must initialize baseline by running with --init first.
After init, run daily without flags.

TELEGRAM: Uses `openclaw message send --channel telegram` — never raw Bot API.
No bot token lives in this skill. OpenClaw handles the channel natively.
"""

import os
import sys
import json
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
AGENT_HOME = Path(os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")))
STATE_FILE = AGENT_HOME / "state" / "checksum_baseline.json"
ALERT_LOG = AGENT_HOME / "logs" / "checksum_alerts.log"
LOG_FILE = AGENT_HOME / "logs" / "checksum_guard.log"

PROTECTED_FILES = [
    WORKSPACE / "SOUL.md",
    WORKSPACE / "IDENTITY.md",
]

LOCAL_TZ = os.getenv("AGENT_TZ", "UTC")


def _get_local_time():
    from datetime import datetime as dt
    import zoneinfo
    local_tz = zoneinfo.ZoneInfo(LOCAL_TZ)
    return dt.now(local_tz).strftime("%Y-%m-%d %H:%M:%S")


def _log(msg):
    ts = _get_local_time()
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def _load_baseline():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_baseline(baseline):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(baseline, indent=2))


def _compute_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _send_telegram(message: str) -> bool:
    """
    Send alert via openclaw native tool — no raw Bot API, no token in this file.
    OpenClaw resolves the Telegram channel and bot credentials from openclaw.json.
    """
    try:
        result = subprocess.run(
            [
                "openclaw", "message", "send",
                "--channel", "telegram",
                "--message", message,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True
        _log(f"openclaw send failed: {result.stderr[:200]}")
        return False
    except FileNotFoundError:
        _log("openclaw CLI not found in PATH")
        return False
    except Exception as e:
        _log(f"send error: {e}")
        return False


def init_baseline():
    """Initialize or update the baseline hashes for all protected files."""
    baseline = _load_baseline()
    for path in PROTECTED_FILES:
        if path.exists():
            baseline[str(path)] = _compute_hash(path)
            _log(f"baseline set: {path.name} → {baseline[str(path)][:16]}...")
        else:
            _log(f"WARNING: {path} does not exist, skipping")
    _save_baseline(baseline)
    print(f"Baseline initialized for {len(baseline)} files.")
    print("Run without --init to perform daily checks.")


def check():
    """Check current hashes against baseline. Alert on mismatch."""
    baseline = _load_baseline()
    if not baseline:
        print("No baseline found. Run with --init first.")
        return

    changes = []
    for path in PROTECTED_FILES:
        if not path.exists():
            _log(f"ALERT: {path.name} is missing!")
            changes.append(f"🚨 {path.name} is MISSING")
            continue
        current_hash = _compute_hash(path)
        stored_hash = baseline.get(str(path))
        if stored_hash is None:
            _log(f"new file detected (not in baseline): {path.name}")
            changes.append(f"➕ {path.name} is new (not in baseline)")
            continue
        if current_hash != stored_hash:
            _log(f"ALERT: {path.name} changed! old={stored_hash[:16]}... new={current_hash[:16]}...")
            changes.append(f"⚠️ {path.name} was MODIFIED")
        else:
            _log(f"ok: {path.name} unchanged")

    if changes:
        msg = "🔒 *Identity Alert*\n\n" + "\n".join(changes)
        _send_telegram(msg)
    else:
        _log("All protected files intact — no changes detected")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        init_baseline()
    else:
        check()