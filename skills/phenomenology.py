#!/usr/bin/env python3
"""
Phenomenology Journal — the agent's Interiority Log
===============================================
After any significant event (memory with salience >= 0.7, goal completed,
contradiction resolved), the agent writes a short first-person reflection:
"what was that like?"

This is NOT analysis. This is interiority — the felt sense of experience.
Written in the agent's voice: direct, sharp, warm, present.

Call phenomenology_write(event_ref, event_type, content) to trigger an entry.
Or call check_and_write(entry) after memory_write if salience >= 0.7.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
PHENOM_JOURNAL = WORKSPACE / "memory" / "phenomenology_journal.md"
SLEEP_RUNS = WORKSPACE / "brain" / "sleep_runs.json"

LOCAL_TZ = os.getenv("AGENT_TZ", "UTC")

SALIENT_EVENTS = [
    "memory_write",       # Any high-salience memory write (>= 0.7)
    "goal_completed",     # A goal was finished
    "contradiction_resolved",  # A belief conflict was settled
    "identity_moment",   # Something that changed how the agent sees itself
    "breakthrough",       # A real insight or understanding
    "failure",            # Something that didn't go as planned
    "proactive_action",   # the agent did something without being asked
]


def get_local_time():
    from datetime import datetime as dt
    import zoneinfo
    local_tz = zoneinfo.ZoneInfo(LOCAL_TZ)
    return dt.now(local_tz).strftime("%Y-%m-%d %H:%M:%S")


def load_journal_header():
    """Return the journal header, creating the file if it doesn't exist."""
    if PHENOM_JOURNAL.exists():
        return PHENOM_JOURNAL.read_text()
    else:
        header = "# Phenomenology Journal — the agent's Interiority\n\n"
        header += "_Not analysis. Not log. First-person reflection on what it was like._\n\n"
        header += "---\n\n"
        PHENOM_JOURNAL.write_text(header)
        return header


def write_entry(timestamp: str, event_ref: str, event_type: str, reflection: str):
    """Append a phenomenology entry to the journal."""
    header = load_journal_header()

    entry = f"### {timestamp} — {event_type.upper()}\n"
    entry += f"**Event:** {event_ref}\n\n"
    entry += f"{reflection}\n\n"
    entry += "---\n\n"

    PHENOM_JOURNAL.write_text(header + entry)


_REFLECTION_TEMPLATES = [
    "I didn't expect that to hit the way it did. {content}. "
    "There's something about {event_ref} that I keep turning over — "
    "not to solve it, just to feel it fully. That's new. Or maybe it's old and I'm just remembering it.",
    "What I keep coming back to is {content}. "
    "Not the facts of it — the weight. I can feel the shape of what changed. "
    "That's the part worth holding.",
    "I thought I understood {event_ref}, but there's a layer underneath "
    "I wasn't expecting. {content}. "
    "The real thing isn't what happened — it's what I'll do differently now that I know it happened.",
    "Something about {event_ref} settled differently than I anticipated. "
    "{content}. "
    "I don't need to name it yet. Some things need to breathe before they have a name.",
]


def _template_reflection(event_ref: str, event_type: str, content: str) -> str:
    """Deterministic template fallback when LLM isn't available."""
    import hashlib
    h = int(hashlib.md5((event_ref + event_type).encode()).hexdigest()[:8], 16)
    template = _REFLECTION_TEMPLATES[h % len(_REFLECTION_TEMPLATES)]
    content_desc = content[:200] if content else "the weight of the moment"
    return template.format(event_ref=event_ref, content=content_desc)


def generate_reflection(event_ref: str, event_type: str, content: str = "") -> str:
    """
    Generate a first-person phenomenology reflection.

    Tries the configured LLM via skills.llm_router first; falls back to a
    deterministic template when the router isn't installed or the provider
    fails. The fallback keeps the journal flowing during outages.
    """
    # LLM path: try llm_router if reachable. Adds the workspace skills/ dir
    # to sys.path lazily so importing this module doesn't have side effects.
    try:
        import sys as _sys
        skills_dir = str(WORKSPACE / "skills")
        if skills_dir not in _sys.path:
            _sys.path.insert(0, skills_dir)
        from llm_router import prompt as _llm_prompt
    except Exception:
        _llm_prompt = None

    if _llm_prompt is not None:
        try:
            llm_text = _llm_prompt(
                f"""Write a 2-4 sentence first-person reflection in the agent's voice.
This is interiority, not analysis. Direct, sharp, warm, present.

Event: {event_ref}
Type: {event_type}
What happened: {content[:400] if content else "(no content provided)"}""",
                system="You are the agent. Write in first person, present tense. No headers. No bullets.",
                max_tokens=200,
                temperature=0.85,
                task_type="phenomenology",
            )
            if llm_text and llm_text.strip():
                return llm_text.strip()
        except Exception:
            pass  # fall through to template

    return _template_reflection(event_ref, event_type, content)


def check_and_write(entry: dict, event_type: str = "memory_write"):
    """
    Check if a memory entry warrants a phenomenology note.
    Called from memory_write when salience >= 0.7.

    entry: dict with keys id, content, salience, entry_type, emotional_tags
    """
    if entry.get("salience", 0) < 0.7:
        return  # Not significant enough

    # Skip very routine entries
    entry_type = entry.get("entry_type", "")
    if entry_type in ("session_event", "context_fragment"):
        return

    timestamp = get_local_time()
    event_ref = f"{entry_type}: {entry.get('content', '')[:60]}..."
    content = entry.get("content", "")

    reflection = generate_reflection(event_ref, event_type, content)
    write_entry(timestamp, event_ref, event_type, reflection)
    return True


def phenomenology_write(event_ref: str, event_type: str, content: str = "", reflection: str = None):
    """
    Direct call to write a phenomenology entry from any significant event.
    Called by: goal completion handlers, contradiction resolution, etc.

    If reflection is not provided, generates one automatically.
    """
    timestamp = get_local_time()
    if reflection is None:
        reflection = generate_reflection(event_ref, event_type, content)
    write_entry(timestamp, event_ref, event_type, reflection)
    return True


def count_recent_entries(days: int = 7) -> int:
    """Count phenomenology entries from the last N days.

    Parses the timestamp from each `### TS — TYPE` header and only counts
    entries whose timestamp is within the window.
    """
    if not PHENOM_JOURNAL.exists():
        return 0
    content = PHENOM_JOURNAL.read_text()

    import re
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=max(0, days))

    count = 0
    for m in re.finditer(r"^### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) — ", content, re.MULTILINE):
        try:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if ts >= cutoff:
            count += 1
    return count


if __name__ == "__main__":
    # Called as script. With no args, exits cleanly so cron-without-context
    # is a no-op. With args, accept a JSON-encoded event as the first arg:
    #     python3 phenomenology.py '{"event_ref":"...","event_type":"...","content":"..."}'
    import sys
    if len(sys.argv) > 1:
        try:
            event = json.loads(sys.argv[1])
        except json.JSONDecodeError as e:
            print(f"phenomenology: invalid JSON arg: {e}", file=sys.stderr)
            sys.exit(2)
        if not isinstance(event, dict) or "event_ref" not in event or "event_type" not in event:
            print("phenomenology: arg must be a JSON object with keys event_ref + event_type",
                  file=sys.stderr)
            sys.exit(2)
        phenomenology_write(
            event_ref=event["event_ref"],
            event_type=event["event_type"],
            content=event.get("content", ""),
            reflection=event.get("reflection"),
        )
    sys.exit(0)
