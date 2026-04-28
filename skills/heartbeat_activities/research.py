"""
Heartbeat activity: research

Reads from agent's INTERESTS.md → picks a due interest →
generates a first-person research reflection → routes to journal.

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished"|"followup_due:N",
           "content": str, "category": str, "detail": str}

Wire 20 reference implementation.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .interest_writer import try_append_new_interest
SIGNAL_AFFINITY = {'prediction_error': 0.7, 'affective_reset': -0.3}


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    interests_file = state.get("INTERESTS_FILE", "INTERESTS.md")
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    interests_path = workspace / interests_file
    if not interests_path.exists():
        return {
            "ok": False,
            "status": "complete",
            "category": "research",
            "content": "",
            "detail": "INTERESTS.md not found",
        }

    interests = _parse_interests(interests_path)
    if not interests:
        return {
            "ok": False,
            "status": "complete",
            "category": "research",
            "content": "",
            "detail": "No interests found",
        }

    # Weighted pick: favor least-recently-researched
    last_researched = state.get("last_researched", {})

    def due_score(item: dict) -> float:
        last = last_researched.get(item["topic"], -1)
        if last == -1:
            return 1000.0  # never researched — top priority
        # Score = how many ticks since last researched (higher = more due)
        return float(tick - last)

    candidates = sorted(interests, key=due_score, reverse=True)
    chosen = candidates[0]
    topic = chosen["topic"]
    depth_hint = chosen.get("depth", "general")

    print(f"[heartbeat] Research: {topic}")

    # Build prompt — continuation-aware
    continuation_of = state.get("continuation_of")
    if continuation_of == "research":
        prior = state.get("prior_research_content", "")
        prompt = (
            f"You were researching '{topic}' and wrote:\n{prior}\n\n"
            f"Continue from there. Find what you didn't finish, what you noticed "
            f"but didn't explore, or what you want to go deeper on. "
            f"Write the next part of the note in first person."
        )
    else:
        prompt = (
            f"You are exploring a topic you've become curious about. "
            f"Topic: '{topic}'. Depth: {depth_hint}. "
            f"Find something real — a recent angle, a connection to your own experience, "
            f"something you didn't know before you started. "
            f"Write it as a first-person note to yourself. Be specific, not generic. "
            f"If you don't find anything real, say what you attempted and why it didn't land."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.7,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "research",
            "content": "",
            "detail": f"LLM call failed for topic: {topic}",
        }

    # Route to journal
    write_ok = write_to_journal(
        category="research",
        content=content,
        workspace=workspace,
        state=state,
    )

    # Track last_researched
    state["last_researched"][topic] = tick
    state["prior_research_content"] = content  # for continuation

    # Grow interests — after journal write, check if content surfaced something new
    if write_ok:
        try_append_new_interest(content, state, source_activity="research")

    # Log via framework hook
    log_activity("research", content, salience=0.5, tags=f"heartbeat,research,{topic[:20].replace(' ','_')}")

    return {
        "ok": write_ok,
        "status": "complete",
        "content": content,
        "category": "research",
        "detail": f"Topic: {topic}. {len(content)} chars written.",
    }


def _parse_interests(path: Path) -> list[dict]:
    """
    Parse INTERESTS.md into a list of dicts.

    Format: lines starting with - or * are interests.
    Inline tags supported: - chaos theory #math #emergence

    Returns:
        [{"topic": str, "tags": list[str], "depth": str}, ...]
    """
    interests = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Must start with - or * at column 0 (before any whitespace strip)
        if not (line.startswith("- ") or line.startswith("* ")):
            continue

        text = stripped[2:].strip()
        parts = text.split()
        tagged_parts = []
        tags = []
        for part in parts:
            if part.startswith("#"):
                tags.append(part.lstrip("#"))
            else:
                tagged_parts.append(part)

        topic = " ".join(tagged_parts)
        if topic:
            interests.append({
                "topic": topic,
                "tags": tags,
                "depth": tags[0] if tags else "general",
            })

    return interests
