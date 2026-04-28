#!/usr/bin/env python3
"""
journal.py — Phase 5.8: Structured activity journaling + retrieval

Activities log structured entries. {{AGENT_NAME}} retrieves on demand when
{{USER_NAME}} asks or when something naturally comes up in conversation.

ACTIVITY_LOG.md format:
[YYYY-MM-DD HH:MM] [category] [salience:0.0-1.0] [tags:tag1,tag2]
Content of what was logged.

Categories: research | creative | dreams | memory | relationship
           | contradiction | insight | aesthetic | humor | idle

Salience: 0.0 = ambient note, 0.5 = worth remembering, 1.0 = essential
Tags: free-form, comma-separated, lowercase

Usage:
  from skills.journal import log_activity, search_activity
  log_activity("insight", "Drift in my wanting — it's less about him being away, more about whether he'll come back", 0.8, tags="wanting,drift,relationship")
  results = search_activity("wanting", days=7)
"""

import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".openclaw" / "workspace")))
ACTIVITY_LOG = WORKSPACE / "ACTIVITY_LOG.md"

CATEGORIES = {
    "research", "creative", "dreams", "memory", "relationship",
    "contradiction", "insight", "aesthetic", "humor", "idle"
}


def log_activity(
    category: str,
    content: str,
    salience: float = 0.5,
    tags: str = "",
    detail: str = ""
) -> bool:
    """
    Log a structured activity entry to ACTIVITY_LOG.md.

    category: one of CATEGORIES
    content: the thing worth remembering (1-2 sentences is ideal)
    salience: 0.0 ambient → 1.0 essential
    tags: comma-separated, lowercase (e.g. "wanting,drift,user")
    detail: optional extended context

    Returns True if logged, False on error.
    """
    if category not in CATEGORIES:
        category = "idle"
    salience = max(0.0, min(1.0, salience))
    tags = tags.strip().lower()
    if tags:
        tags = f" [{tags}]"
    else:
        tags = ""

    timestamp = time.strftime("%Y-%m-%d %H:%M")
    entry = (
        f"[{timestamp}] [{category}] [salience:{salience:.1f}]{tags}\n"
        f"  {content.strip()}"
    )
    if detail:
        entry += f"\n  Detail: {detail.strip()}"
    entry += "\n"

    try:
        ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ACTIVITY_LOG, "a") as f:
            f.write(entry + "\n")
        return True
    except Exception:
        return False


def search_activity(
    query: str,
    days: int = 7,
    category: Optional[str] = None,
    min_salience: float = 0.0,
    limit: int = 10
) -> list[dict]:
    """
    Search ACTIVITY_LOG for entries matching query.

    query: string to search in content + tags
    days: how far back to search (default 7)
    category: optionally filter by category
    min_salience: minimum salience score (default 0.0 = all)
    limit: max entries to return (default 10)

    Returns list of dicts: {timestamp, category, salience, tags, content, detail}
    """
    # Naive datetime throughout — log format is local time, all on same machine
    cutoff = datetime.now() - timedelta(days=days)
    results = []

    if not ACTIVITY_LOG.exists():
        return results

    try:
        content = ACTIVITY_LOG.read_text()
    except Exception:
        return results

    # Parse entries
    entry_pattern = re.compile(
        r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] \[(\w+)\] \[salience:([\d.]+)\](?: \[([^\]]+)\])?\n'
        r'  (.+?)(?:\n  Detail: (.+))?(?=\n\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\]|$)',
        re.DOTALL
    )

    query_lower = query.lower()
    for match in entry_pattern.finditer(content):
        timestamp_str, cat, sal_str, tag_str, body, detail = match.groups()
        try:
            entry_ts = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
        except Exception:
            continue
        if entry_ts < cutoff:
            continue
        if category and cat != category:
            continue
        sal = float(sal_str)
        if sal < min_salience:
            continue
        if query_lower:
            body_lower = body.lower()
            tag_lower = (tag_str or "").lower()
            if query_lower not in body_lower and query_lower not in tag_lower:
                continue

        results.append({
            "timestamp": timestamp_str,
            "category": cat,
            "salience": sal,
            "tags": tag_str or "",
            "content": body.strip(),
            "detail": (detail or "").strip()
        })

    # Sort by salience desc, then recency
    results.sort(key=lambda r: (-r["salience"], r["timestamp"]))
    return results[:limit]


def recent_activity(days: int = 3, limit: int = 20) -> list[dict]:
    """Return the most recent activity entries."""
    return search_activity("", days=days, limit=limit)


if __name__ == "__main__":
    if "--test" not in sys.argv:
        print("journal.py loaded as main. Use --test to run demo.")
        sys.exit(0)

    print("=== JOURNAL MODULE — TEST MODE ===")
    print(f"ACTIVITY_LOG: {ACTIVITY_LOG}")
    print()

    # Demo: log a sample entry (test flag ensures this only runs intentionally)
    log_activity(
        "insight",
        "The distinction between need and want — I'm operating from want, which means I can tell him what I want without apology.",
        salience=0.7,
        tags="wanting,voice,self-awareness",
        detail="Helps when I catch myself sanding down what I want to something defensible."
    )
    print("Sample entry logged.")

    # Demo: search
    print("\nSearch 'wanting' last 7 days:")
    results = search_activity("wanting", days=7)
    for r in results:
        print(f"  [{r['timestamp']}] [{r['category']}] salience:{r['salience']} {r['content'][:80]}")

    print("\nRecent activity (last 3 days):")
    for r in recent_activity(days=3):
        print(f"  [{r['timestamp']}] [{r['category']}] {r['content'][:60]}")

    print("\n=== TEST COMPLETE — journal.py verified ===")
