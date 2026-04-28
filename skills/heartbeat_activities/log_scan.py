"""
Heartbeat activity: log_scan

Scan heartbeat and gateway logs for errors, warnings, or unusual patterns.
Reads recent entries from both logs and journals findings.
Configurable log paths via state dict.

Activity contract:
  Input:  state dict (WORKSPACE, HEARTBEAT_LOG, GATEWAY_LOG)
  Output: {"ok": bool, "status": "complete",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import random
from pathlib import Path

from .journal import write_to_journal
from .log import log_activity
SIGNAL_AFFINITY = {}


CATEGORY = "log_scan"

DEFAULT_HEARTBEAT_LOG = Path.home() / ".agent" / "logs" / "heartbeat.log"
DEFAULT_GATEWAY_LOG = Path.home() / ".openclaw" / "logs" / "gateway.log"


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))

    hb_log = Path(state.get("HEARTBEAT_LOG", str(DEFAULT_HEARTBEAT_LOG)))
    gw_log = Path(state.get("GATEWAY_LOG", str(DEFAULT_GATEWAY_LOG)))

    print(f"[heartbeat] log_scan: {hb_log}")

    errors, warnings = [], []

    if hb_log.exists():
        hb_errors, hb_warnings = _scan_file(hb_log, state.get("TICK_COUNT", 0))
        errors.extend(hb_errors)
        warnings.extend(hb_warnings)
    else:
        log_activity("log_scan", f"heartbeat log not found: {hb_log}", salience=0.2, tags="info")

    if gw_log.exists():
        gw_errors, gw_warnings = _scan_file(gw_log, state.get("TICK_COUNT", 0))
        errors.extend(gw_errors)
        warnings.extend(gw_warnings)

    content = _format_scan(errors, warnings, hb_log, gw_log)

    write_to_journal(category="log_scan", content=content,
                    workspace=workspace, state=state)

    return {
        "ok": True,
        "status": "complete",
        "content": content,
        "category": CATEGORY,
        "proactive": len(errors) > 0,
        "detail": f"{len(errors)} error(s), {len(warnings)} warning(s) in scanned logs",
    }


def _scan_file(path: Path, current_tick: int) -> tuple[list, list]:
    """Return (errors, warnings) from recent log entries."""
    try:
        lines = path.read_text().splitlines()[-200:]
    except Exception:
        return [], []

    # Skip lines that are our own {{AGENT_NAME}} conversation — they live in gateway.err.log
    # and contain words like "error" and "fix" from the transcript.
    # Recognised by ISO-8601 timestamp prefix: "2026-04-24T13:59:48.872-06:00 ..."
    import re
    IS_SELF_LINE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    errors, warnings = [], []
    for line in lines:
        if IS_SELF_LINE.match(line):
            continue  # skip {{AGENT_NAME}}'s own conversation logged to gateway.err.log

        line_lower = line.lower()

        # Skip success lines that happen to contain the word "error" in a different sense
        # e.g. "Operator plugins loaded: 19 OK, 0 errors" — success, not an error
        if " ok," in line_lower or " ok " in line_lower or line_lower.endswith(" ok"):
            continue  # "loaded: 19 OK, 0 errors" — success line, not an error

        if any(x in line_lower for x in ["exception", "traceback", "crashed", "fatal"]):
            errors.append(_clean_line(line))
        elif " error" in line_lower or line_lower.startswith("error"):
            errors.append(_clean_line(line))
        elif any(x in line_lower for x in ["warning", "warn", "retry"]):
            warnings.append(_clean_line(line))

    return errors, warnings


def _clean_line(line: str) -> str:
    """Strip timestamps and truncate."""
    parts = line.split("]", 1)
    if len(parts) > 1:
        return parts[1].strip()
    return line.strip()[:150]


def _format_scan(errors: list, warnings: list, hb_log: Path, gw_log: Path) -> str:
    lines = [f"Log scan — {len(errors)} errors, {len(warnings)} warnings", ""]

    if errors:
        lines.append(f"Errors ({len(errors)}):")
        for e in errors[-20:]:  # Cap at 20
            lines.append(f"  ✗ {e}")
        lines.append("")
    else:
        lines.append("No errors found. ✓")
        lines.append("")

    if warnings:
        lines.append(f"Warnings ({len(warnings)}):")
        for w in warnings[-10:]:
            lines.append(f"  ⚠ {w}")
        lines.append("")
    else:
        lines.append("No warnings found. ✓")

    lines.append(f"\nScanned: {hb_log}")
    if gw_log.exists():
        lines.append(f"         {gw_log}")

    return "\n".join(lines)