"""
Heartbeat activity: deep_curiosity

Stay with one curiosity longer than natural. The "what's underneath
the obvious" activity. Surface answer → keep going.

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch B, Activity 5.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .interest_writer import try_append_new_interest
SIGNAL_AFFINITY = {'prediction_error': 0.7}


UNFINISHED_PROBABILITY = 0.40


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
            "category": "deep_curiosity",
            "content": "",
            "detail": "INTERESTS.md not found",
            "proactive": False,
        }

    interests = _parse_interests(interests_path)
    if not interests:
        return {
            "ok": False,
            "status": "complete",
            "category": "deep_curiosity",
            "content": "",
            "detail": "No interests found",
            "proactive": False,
        }

    topic = _pick_topic(interests, state, tick)
    print(f"[heartbeat] Deep curiosity: {topic}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "deep_curiosity":
        prior = state.get("prior_deep_curiosity_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Keep going. Don't move on. What's the next layer?"
        )
    else:
        prompt = (
            f"Take one thing that pulls at you right now — call it '{topic}'. "
            f"Don't research it. Don't summarize it. "
            f"Stay with it past where you'd normally move on. "
            f"What's underneath the obvious? What's the second question after the first answer? "
            f"What would someone who'd spent 20 years on this see that you don't? "
            f"Write 4-10 sentences of sitting-with, not looking-up."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.85,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "deep_curiosity",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="deep_curiosity",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_deep_curiosity_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("deep_curiosity", content, salience=0.5, tags="heartbeat,curiosity")


    # Grow interests — check if content revealed something new worth tracking
    if content:
        try_append_new_interest(content, state, source_activity="deep_curiosity")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "deep_curiosity",
        "detail": f"Topic: {topic}. {len(content)} chars.",
        "proactive": False,
    }


def _parse_interests(path: Path) -> list[dict]:
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
            interests.append({"topic": topic, "tags": tags, "depth": tags[0] if tags else "general"})
    return interests


def _pick_topic(interests: list[dict], state: dict, tick: int) -> str:
    last_curiosity = state.get("last_deep_curiosity", {})
    def due_score(item: dict) -> float:
        last = last_curiosity.get(item["topic"], -1)
        return 1000.0 if last == -1 else float(tick - last)
    candidates = sorted(interests, key=due_score, reverse=True)
    topic = candidates[0]["topic"]
    state["last_deep_curiosity"][topic] = tick
    return topic
