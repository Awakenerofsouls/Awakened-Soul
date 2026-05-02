"""
Shared INTERESTS.md parser. Accepts both bullet-list and h3-section formats
so agents can write their interests file in whichever style fits their voice
without losing heartbeat-activity coverage.

Bullet format (machine-readable, easy for activities to weight):
    - Topic name #tag1 #tag2
    * Another topic #tag

H3 section format (prose-friendly, human-feeling):
    ### Topic Name
    A few paragraphs about why this is alive...

    ### Another Topic
    More prose...

Both can appear in the same file. The parser walks the file, picks up
both kinds of lines, and yields a uniform list of {topic, tags, depth}
dicts that downstream activities (deep_curiosity, study, research,
tool_explore, creative, etc.) can rank and pick from.
"""

from pathlib import Path
from typing import List, Dict


# Section headers that are clearly NOT topics — skip them when seen as h3.
_SKIP_HEADERS = {
    "notes", "todo", "wip", "draft", "old", "deprecated",
    "table of contents", "index", "topics",
    "these are mine", "topics machine readable", "machine-readable",
}


def parse_interests(path: Path) -> List[Dict]:
    """
    Walk an INTERESTS.md file and return a list of interest dicts.

    Each entry: {"topic": str, "tags": List[str], "depth": str}
      - topic: the interest text itself
      - tags:  any #word tokens that appeared on the bullet line
      - depth: tags[0] if tagged, else "general"

    Robust to:
      - bullet lines (- foo / * foo)
      - h3 headers (### Foo)
      - mixed files (bullets + h3 in same doc)
      - empty files (returns [])
      - files that don't exist (raises FileNotFoundError — caller should pre-check)
    """
    interests: List[Dict] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue

        topic = None
        tags: List[str] = []

        # ── Bullet-list format ───────────────────────────────────────────
        if raw.startswith("- ") or raw.startswith("* "):
            text = stripped[2:].strip()
            kept = []
            for part in text.split():
                if part.startswith("#"):
                    tag = part.lstrip("#").strip(",.;:!?")
                    if tag:
                        tags.append(tag)
                else:
                    kept.append(part)
            topic = " ".join(kept).strip(" .,;:")

        # ── H3 section header (### Topic) ────────────────────────────────
        elif stripped.startswith("### "):
            candidate = stripped[4:].strip().rstrip(":").strip()
            # Filter out non-topic h3s like "Notes", "Topics (machine-readable)", etc.
            lc = candidate.lower()
            if candidate and not any(skip in lc for skip in _SKIP_HEADERS):
                topic = candidate

        if topic:
            interests.append({
                "topic": topic,
                "tags":  tags,
                "depth": tags[0] if tags else "general",
            })

    return interests
