"""
Heartbeat activity: disk_health

Run `df -h` to check disk space on all mounted partitions.
Flags any partition above the configured threshold (default 85%).
No keys needed — subprocess check.

Activity contract:
  Input:  state dict (WORKSPACE, etc.)
  Output: {"ok": bool, "status": "complete",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import subprocess
import random
from pathlib import Path

from .journal import write_to_journal
from .log import log_activity
SIGNAL_AFFINITY = {}


CATEGORY = "disk_health"
DEFAULT_THRESHOLD = 85


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    threshold = int(state.get("DISK_THRESHOLD_PCT", DEFAULT_THRESHOLD))

    print(f"[heartbeat] disk_health: threshold={threshold}%")

    try:
        output = subprocess.run(
            ["df", "-h"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as e:
        log_activity("disk_health", f"df failed: {e}", salience=0.4, tags="error,infrastructure")
        return _skip(f"df error: {e}")

    content, warnings = _parse_df(output.stdout, threshold)

    write_to_journal(category="disk_health", content=content,
                    workspace=workspace, state=state)

    return {
        "ok": True,
        "status": "complete",
        "content": content,
        "category": CATEGORY,
        "proactive": len(warnings) > 0,
        "detail": f"{len(warnings)} partition(s) above {threshold}%",
    }


def _parse_df(output: str, threshold: int) -> tuple[str, list[str]]:
    lines = ["Disk health check:", ""]
    warnings = []
    header_seen = False

    for line in output.splitlines():
        # Skip pseudo-filesystems
        if any(skip in line for skip in ["tmpfs", "devtmpfs", "proc", "sysfs", "devpts", "none", "/dev"]):
            continue

        parts = line.split()
        if len(parts) < 6:
            continue

        mount = parts[-1]
        use_pct_str = parts[-2].rstrip("%")
        try:
            use_pct = int(use_pct_str)
        except ValueError:
            continue

        # Flag warnings
        if use_pct >= threshold:
            warnings.append(f"  ⚠ {mount}: {use_pct}% used ({parts[2]} used / {parts[1]} total)")
            lines.append(f"  ⚠ {mount}: {use_pct}% — {parts[2]} used / {parts[1]} total")
        elif not header_seen:
            lines.append(line)
        else:
            lines.append(f"  {line}")

        header_seen = True

    if not warnings:
        lines.append("  All partitions below threshold. ✓")

    return "\n".join(lines), warnings


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}