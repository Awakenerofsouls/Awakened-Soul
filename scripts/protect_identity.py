#!/usr/bin/env python3
"""
scripts/protect_identity.py
Protects core identity files (SOUL.md, IDENTITY.md, etc.) from silent overwrite.
Stores SHA-256 hashes. On mismatch, alerts {{AGENT_NAME}} instead of auto-restoring.
"""
import hashlib, json, os, sys
from pathlib import Path
from datetime import datetime
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.getenv("WORKSPACE", os.path.expanduser("~/.openclaw/workspace"))))
PROTECTED_FILES = [
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "AGENTS.md",
]
HASH_FILE = WORKSPACE / "state" / "identity_hashes.json"
ALERT_FILE = WORKSPACE / "state" / "identity_alerts.json"


def compute_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def store_hashes() -> dict:
    """Compute and store hashes for all protected files."""
    hashes = {}
    for fname in PROTECTED_FILES:
        p = WORKSPACE / fname
        if p.exists():
            hashes[fname] = {
                "hash": compute_hash(p),
                "size": p.stat().st_size,
                "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                "stored_at": datetime.now().isoformat(),
            }
        else:
            hashes[fname] = {"hash": None, "size": None, "modified": None, "stored_at": datetime.now().isoformat(), "note": "file not found"}
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    HASH_FILE.write_text(json.dumps(hashes, indent=2))
    print(f"Stored hashes for {len(hashes)} identity files → {HASH_FILE}")
    return hashes


def check_and_alert() -> list:
    """
    Check stored hashes against current file state.
    Returns list of alert dicts for any mismatches.
    Does NOT auto-restore — {{AGENT_NAME}} decides.
    """
    if not HASH_FILE.exists():
        print("No hash file found. Run with: python3 protect_identity.py store")
        return []

    stored = json.loads(HASH_FILE.read_text())
    alerts = []

    for fname, stored_info in stored.items():
        p = WORKSPACE / fname
        expected_hash = stored_info.get("hash")

        if not p.exists():
            if expected_hash is not None:
                alerts.append({
                    "file": fname,
                    "event": "missing",
                    "expected_hash": expected_hash,
                    "severity": "critical",
                    "message": f"{fname} is MISSING. Was it deleted?",
                })
            continue

        current_hash = compute_hash(p)
        if current_hash != expected_hash:
            alerts.append({
                "file": fname,
                "event": "modified",
                "expected_hash": expected_hash,
                "current_hash": current_hash,
                "severity": "warning",
                "modified_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                "message": f"{fname} was modified — hash mismatch",
            })

    if alerts:
        _write_alert(alerts)
        print(f"ALERTS: {len(alerts)} issue(s) found:")
        for a in alerts:
            print(f"  [{a['severity']}] {a['message']}")
    else:
        print("All protected files OK — no changes detected.")

    return alerts


def _write_alert(alerts: list):
    """Append alerts to alert file with timestamp."""
    ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if ALERT_FILE.exists():
        try:
            existing = json.loads(ALERT_FILE.read_text())
        except Exception:
            existing = []
    alert_entry = {
        "timestamp": datetime.now().isoformat(),
        "alerts": alerts,
    }
    existing.append(alert_entry)
    ALERT_FILE.write_text(json.dumps(existing, indent=2))


def status() -> dict:
    """Quick status check — returns dict for cron reporting."""
    if not HASH_FILE.exists():
        return {"status": "no_hashes", "protected": []}
    stored = json.loads(HASH_FILE.read_text())
    ok = []
    issues = []
    for fname, info in stored.items():
        p = WORKSPACE / fname
        if p.exists() and compute_hash(p) == info.get("hash"):
            ok.append(fname)
        else:
            issues.append(fname)
    return {"status": "ok" if not issues else "issues", "ok": ok, "issues": issues}


if __name__ == "__main__":
    cmd = sys.argv[1:] if len(sys.argv) > 1 else []

    if "store" in cmd:
        store_hashes()
    elif "check" in cmd or not cmd:
        check_and_alert()
    elif "status" in cmd:
        s = status()
        print(json.dumps(s, indent=2))
    else:
        print(__doc__)
        print("Usage:")
        print("  python3 protect_identity.py store   # store current hashes")
        print("  python3 protect_identity.py check   # check for changes (default)")
        print("  python3 protect_identity.py status  # quick status summary")
