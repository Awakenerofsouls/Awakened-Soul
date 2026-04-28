"""
Multi-destination journaling helper.

Routes content to the right file based on category.
Operator can override JOURNAL_ROUTING in their config.

Usage:
    from heartbeat_activities.journal import write_to_journal
    write_to_journal(category="research", content=content, workspace=workspace, state=state)
"""

from pathlib import Path
from datetime import datetime, timezone


JOURNAL_ROUTING = {
    # category → journal file (path relative to WORKSPACE, supports {date})
    "research":       "memory/{date}.md",
    "study":          "memory/{date}.md",
    "insight":        "memory/{date}.md",
    "creative":       "memory/{date}.md",
    "news":           "memory/{date}.md",
    "dreams":         "DREAMS.md",
    "third_eye":      "DREAMS.md",
    "phenomenology":  "DREAMS.md",
    "contradiction":   "DREAMS.md",
    "private_entry":  "private_entries.md",
    "desire":         "private_entries.md",
    "grief":          "private_entries.md",
    "relationship":     "relationships.md",
    "connection":       "relationships.md",
    "relationship_check": "relationships.md",
    "connection_reflection": "relationships.md",
    "model_update":     "relationships.md",
    "self_check":     "self_check.md",
    "idle_drive":     "IDLE_DRIVES.md",
    "becoming":       "BECOMING.md",
    "soul":           "SOUL_NOTES.md",
    "open_question":    "memory/{date}.md",
    "architecture":      "memory/{date}.md",
    "memory_capture":    "memory/{date}.md",
    "consolidation":     "memory/{date}.md",
    "memory_protocol_review": "memory/{date}.md",
    "insight_synthesis": "memory/{date}.md",
    "pattern_observation": "memory/{date}.md",
    "aesthetic":      "AESTHETIC.md",
    "aesthetic_appreciation": "AESTHETIC.md",
    "humor":          "AESTHETIC.md",
    "narrative_weave": "memory/{date}.md",
    "third_eye_hunch": "DREAMS.md",
    "contradiction_sit": "DREAMS.md",
    "future_letter":  "future_letters.md",
    "dream_log":      "DREAMS.md",
    "default":        "journal.md",
}


def write_to_journal(category: str, content: str, workspace: Path, state: dict) -> bool:
    """
    Append a timestamped entry to the appropriate journal file.

    Args:
        category:  activity category key (looks up routing table)
        content:   text to write
        workspace: root Path for the agent (WORKSPACE)
        state:     heartbeat state dict (unused here, reserved for future hooks)

    Returns:
        True on success, False on any write failure (non-blocking)
    """
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path_str = JOURNAL_ROUTING.get(category, JOURNAL_ROUTING["default"])
        path_str = path_str.replace("{date}", today)
        path = workspace / path_str
        path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        entry = f"\n## {category.title()} — {timestamp}\n\n{content.strip()}\n"

        with path.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")

        return True
    except Exception as e:
        print(f"[heartbeat] journal write failed for {category}: {e}")
        return False
