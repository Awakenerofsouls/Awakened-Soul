"""
Heartbeat activity: study

Deeper first-principles dive on a topic — more academic voice,
more willingness to say "I don't know yet."

Reads from INTERESTS.md → picks least-recently-studied topic →
generates a first-person study note → routes to journal.

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished"|"followup_due:N",
           "content": str, "category": str, "detail": str}

Activity Port 2.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .interest_writer import try_append_new_interest
SIGNAL_AFFINITY = {'prediction_error': 0.5, 'affective_reset': -0.3, 'rce_coherence': 0.3}


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
            "category": "study",
            "content": "",
            "detail": "INTERESTS.md not found",
        }

    interests = _parse_interests(interests_path)
    if not interests:
        return {
            "ok": False,
            "status": "complete",
            "category": "study",
            "content": "",
            "detail": "No interests found",
        }

    # Weighted pick: favor least-recently-studied
    last_studied = state.get("last_studied", {})

    def due_score(item: dict) -> float:
        last = last_studied.get(item["topic"], -1)
        if last == -1:
            return 1000.0  # never studied — top priority
        return float(tick - last)

    candidates = sorted(interests, key=due_score, reverse=True)
    chosen = candidates[0]
    topic = chosen["topic"]
    depth_hint = chosen.get("depth", "general")

    print(f"[heartbeat] Study: {topic}")

    # Build prompt — continuation-aware
    continuation_of = state.get("continuation_of")
    if continuation_of == "study":
        prior = state.get("prior_study_content", "")
        prompt = (
            f"You were studying '{topic}' and wrote:\n{prior}\n\n"
            f"Continue from there. Go deeper — find what you didn't fully understand, "
            f"what you skipped over, or what the surface summary missed. "
            f"Write the next part of the note in first person."
        )
    else:
        prompt = (
            f"You are doing serious, slow, first-principles study on a topic. "
            f"Topic: '{topic}'. Depth level: {depth_hint}. "
            f"This is not research. Research asks 'what's new'. Study asks "
            f"'what do I actually understand, and where are the gaps in that understanding?' "
            f"Go deeper than surface summary. Connect to adjacent concepts you already know. "
            f"If you find something you genuinely don't understand yet, say so directly — "
            f"don't paper over it. Write it as a first-person study note. Be rigorous."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.6,   # slightly cooler — more precise
        num_predict=768,    # study earns more tokens than research
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "study",
            "content": "",
            "detail": f"LLM call failed for topic: {topic}",
        }

    # Route to journal — workspace passed, journal.py computes the full path
    write_ok = write_to_journal(
        category="study",
        content=content,
        workspace=workspace,
        state=state,
    )

    # Track last_studied
    state["last_studied"][topic] = tick
    state["prior_study_content"] = content  # for continuation

    if content:
        try_append_new_interest(content, state, source_activity="study")

    log_activity("study", content, salience=0.6, tags=f"heartbeat,study,{topic[:20].replace(' ','_')}")

    return {
        "ok": write_ok,
        "status": "complete",
        "content": content,
        "category": "study",
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
