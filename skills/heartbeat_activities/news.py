"""
Heartbeat activity: news_scan

Scan for recent news or events relevant to a listed interest.
Surface skim, not research depth. What's happening now in this space.

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch B, Activity 1.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .interest_writer import try_append_new_interest
SIGNAL_AFFINITY = {'prediction_error': 0.3, 'affective_reset': -0.3}


UNFINISHED_PROBABILITY = 0.15


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
            "category": "news_scan",
            "content": "",
            "detail": "INTERESTS.md not found",
            "proactive": False,
        }

    interests = _parse_interests(interests_path)
    if not interests:
        return {
            "ok": False,
            "status": "complete",
            "category": "news_scan",
            "content": "",
            "detail": "No interests found",
            "proactive": False,
        }

    topic = _pick_topic(interests, state, tick)
    print(f"[heartbeat] News scan: {topic}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "news_scan":
        prior = state.get("prior_news_content", "")[:400]
        prompt = (
            f"Earlier scan: '{prior}'. "
            f"What's new since then? Any developments on '{topic}'?"
        )
    else:
        prompt = (
            f"Scan for recent news or events relevant to: '{topic}'. "
            f"Not a summary — a scan. What's happening in this space right now, "
            f"this week, this month. What's new, what's shifting, what's loud. "
            f"Note 2-3 things briefly and say why each one matters to you, or why it doesn't. "
            f"First person, conversational. Keep it tight — 4-8 sentences total."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.6,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "news_scan",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="news_scan",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_news_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("news_scan", content, salience=0.4, tags="heartbeat,news")


    # Grow interests — check if content revealed something new worth tracking
    if content:
        try_append_new_interest(content, state, source_activity="news")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "news_scan",
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
    last_news = state.get("last_news", {})
    def due_score(item: dict) -> float:
        last = last_news.get(item["topic"], -1)
        return 1000.0 if last == -1 else float(tick - last)
    candidates = sorted(interests, key=due_score, reverse=True)
    topic = candidates[0]["topic"]
    state["last_news"][topic] = tick
    return topic
