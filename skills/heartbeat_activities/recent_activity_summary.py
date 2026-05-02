"""
Heartbeat activity: recent_activity_summary

Deterministic visibility layer for what the heartbeat has been doing.

Reads the tail of ACTIVITY_LOG.md and writes a clean summary to
WORKSPACE/RECENT_ACTIVITY.md. The summary is the file the agent's
identity loader references on session start so it knows what its own
loop did between conversations — no LLM round-trip required.

Why this exists:
  - The richer session_handoff_update activity asks an LLM to write
    a narrative handoff. When Ollama / the configured LLM endpoint is
    down (a common dev state), that activity skips and the agent boots
    a new session with no awareness of recent autonomous activity.
  - This activity is pure I/O: parse + group + write. Always succeeds
    as long as the disk is writable.

Output format (RECENT_ACTIVITY.md):
  # Recent Activity
  *Last updated: <timestamp>*
  *Window: last <N> entries from ACTIVITY_LOG.md*

  ## By Category
  - molty (3): chapter 2, posted...
  - dreams (2): ...
  - research (1): ...

  ## Latest Entries
  - [HH:MM] [molty] caption ...
  - [HH:MM] [dreams] ...

Activity contract:
  Input:  state dict (WORKSPACE)
  Output: standard activity result dict (always ok=True if disk works)
"""

from __future__ import annotations

import os
import re
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CATEGORY = "recent_activity_summary"
SIGNAL_AFFINITY: Dict[str, float] = {}  # ambient — no signal preference

ENTRIES_TO_SUMMARIZE = 25         # tail size from ACTIVITY_LOG.md
MAX_PER_CATEGORY_DETAIL = 3       # how many representative entries per category
MAX_LATEST_LIST = 12              # how many latest entries in flat list

# Matches lines written by skills.journal.log_activity:
#   [YYYY-MM-DD HH:MM] [category] [salience:0.6] [tags:foo,bar]
_HEADER_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] "
    r"\[(?P<category>[^\]]+)\] "
    r"\[salience:(?P<salience>[\d.]+)\]"
    r"(?: \[(?P<tags>[^\]]+)\])?\s*$"
)


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", ".")))
    activity_log = workspace / "ACTIVITY_LOG.md"
    out_path = workspace / "RECENT_ACTIVITY.md"

    if not activity_log.exists():
        # No activity yet — write a stub so the file is always present for
        # session-start loaders to read without crashing.
        try:
            out_path.write_text(_render_empty(), encoding="utf-8")
        except OSError as e:
            return _result(False, "", f"write failed: {e}")
        return _result(True, str(out_path), "no activity yet — stub written")

    try:
        text = activity_log.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return _result(False, "", f"read failed: {e}")

    entries = _parse_entries(text)
    if not entries:
        try:
            out_path.write_text(_render_empty(), encoding="utf-8")
        except OSError as e:
            return _result(False, "", f"write failed: {e}")
        return _result(True, str(out_path), "log present but empty — stub written")

    tail = entries[-ENTRIES_TO_SUMMARIZE:]
    rendered = _render_summary(tail)

    try:
        out_path.write_text(rendered, encoding="utf-8")
    except OSError as e:
        return _result(False, "", f"write failed: {e}")

    by_cat = _group_by_category(tail)
    cat_summary = ", ".join(f"{cat}({len(items)})" for cat, items in by_cat.items())
    return _result(
        True,
        str(out_path),
        f"summarized {len(tail)} entries — {cat_summary}",
    )


# ── Parsing ───────────────────────────────────────────────────────────────────


def _parse_entries(text: str) -> List[Dict[str, Any]]:
    """
    Walk ACTIVITY_LOG.md and split it into structured entries.

    Each entry begins with a header line matching _HEADER_RE; subsequent
    indented lines (starting with two spaces) belong to that entry until
    the next header or blank.
    """
    entries: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    for raw in text.splitlines():
        m = _HEADER_RE.match(raw)
        if m:
            if current:
                entries.append(current)
            current = {
                "ts":       m.group("ts"),
                "category": m.group("category"),
                "salience": float(m.group("salience")),
                "tags":     _parse_tags(m.group("tags")),
                "lines":    [],
            }
            continue
        if current is None:
            continue
        if raw.startswith("  "):
            current["lines"].append(raw[2:].rstrip())
        elif raw.strip() == "":
            entries.append(current)
            current = None

    if current:
        entries.append(current)

    return entries


def _parse_tags(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    raw = raw.strip()
    # Normalise "tags:foo,bar" or just "foo,bar" forms.
    if raw.lower().startswith("tags:"):
        raw = raw.split(":", 1)[1]
    return [t.strip() for t in raw.split(",") if t.strip()]


# ── Rendering ─────────────────────────────────────────────────────────────────


def _render_empty() -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        "# Recent Activity\n"
        f"*Last updated: {now}*\n\n"
        "_No autonomous activity has been logged yet._\n"
        "_Once the heartbeat runs activities, this file will summarize the most "
        "recent ones so a fresh session can see what its loop did._\n"
    )


def _render_summary(entries: List[Dict[str, Any]]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    by_cat = _group_by_category(entries)

    out: List[str] = [
        "# Recent Activity",
        f"*Last updated: {now}*",
        f"*Window: last {len(entries)} entries from ACTIVITY_LOG.md*",
        "",
        "## By Category",
    ]

    for category, items in by_cat.items():
        out.append(f"### {category} ({len(items)})")
        for entry in items[-MAX_PER_CATEGORY_DETAIL:]:
            preview = _preview(entry)
            out.append(f"- [{entry['ts'][-5:]}] {preview}")
        out.append("")

    out.append("## Latest Entries")
    for entry in entries[-MAX_LATEST_LIST:][::-1]:
        preview = _preview(entry)
        out.append(f"- [{entry['ts'][-5:]}] [{entry['category']}] {preview}")

    out.append("")  # trailing newline
    return "\n".join(out)


def _group_by_category(entries: List[Dict[str, Any]]) -> "OrderedDict[str, List[Dict[str, Any]]]":
    """Group entries by category preserving first-seen order."""
    grouped: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for e in entries:
        grouped.setdefault(e["category"], []).append(e)
    return grouped


def _preview(entry: Dict[str, Any], max_chars: int = 160) -> str:
    content = " ".join(line.strip() for line in entry.get("lines") or [] if line.strip())
    if not content:
        content = "(no content)"
    if len(content) > max_chars:
        content = content[: max_chars - 1].rstrip() + "…"
    return content


def _result(ok: bool, content: str, detail: str) -> Dict[str, Any]:
    return {
        "ok":        ok,
        "status":    "complete",
        "content":   content,
        "category":  CATEGORY,
        "proactive": False,
        "detail":    detail,
    }
