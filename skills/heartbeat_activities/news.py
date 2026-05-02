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
from ._web import web_lookup
from ._interests_parser import parse_interests as _parse_interests
SIGNAL_AFFINITY = {'prediction_error': 0.3, 'affective_reset': -0.3}


UNFINISHED_PROBABILITY = 0.15


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
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

    # Real web fetch — recency-biased (news intent in _web flips Tavily
    # into news mode + 7-day window). LLM reflects ON the hits, doesn't
    # fabricate them.
    web = web_lookup(topic, intent="news", max_results=5, max_age_days=7)
    web_block = ""
    if web.get("ok"):
        web_block = (
            "\n\nGround truth (real fetch — react to these, don't invent):\n"
            f"{web['summary_text']}\n"
        )

    continuation_of = state.get("continuation_of")
    if continuation_of == "news_scan":
        prior = state.get("prior_news_content", "")[:400]
        prompt = (
            f"Earlier scan: '{prior}'. "
            f"What's new since then? Any developments on '{topic}'?"
            f"{web_block}"
        )
    else:
        prompt = (
            f"Scan for recent news or events relevant to: '{topic}'. "
            f"Not a summary — a scan. What's happening in this space right now, "
            f"this week, this month. What's new, what's shifting, what's loud. "
            f"Note 2-3 things briefly and say why each one matters to you, or why it doesn't. "
            f"First person, conversational. Keep it tight — 4-8 sentences total."
            f"{web_block}"
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

    journaled = content
    if web.get("ok") and web.get("hits"):
        journaled = (
            content.rstrip()
            + "\n\n---\n*Sources (last 7d):*\n"
            + "\n".join(
                f"- [{h['title'] or h['url']}]({h['url']})"
                for h in web["hits"]
            )
        )

    write_ok = write_to_journal(
        category="news_scan",
        content=journaled,
        workspace=workspace,
        state=state,
    )

    state["prior_news_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    backend = web.get("backend") or "llm-only"
    log_activity(
        "news_scan",
        content,
        salience=0.4,
        tags=f"heartbeat,news,{backend}",
    )

    # Grow interests — check if content revealed something new worth tracking
    if content:
        try_append_new_interest(content, state, source_activity="news")

    # ── Brain-event posting ─────────────────────────────────────────
    # Same pattern as research.py: outward-reach for the fetch (when real),
    # memory-encode for the finding. Best-effort.
    try:
        from ._brain_post import (
            post_outward_reach_call, post_memory_encode,
        )
        if backend != "llm-only":
            post_outward_reach_call(
                provider=backend,
                intent="news",
                success=True,
                source="news",
            )
        if content:
            sc = float(web.get("source_confidence") or 0.4)
            post_memory_encode(
                content=content,
                intent="observation",
                source_kind="external" if backend != "llm-only" else "inference",
                content_confidence=0.6,  # news skews lower than research
                source_confidence=sc,
                source="news",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "news_scan",
        "backend": backend,
        "n_web_hits": len(web.get("hits") or []),
        "source_confidence": web.get("source_confidence", 0.4),
        "detail": f"Topic: {topic}. backend={backend}. {len(content)} chars.",
        "proactive": False,
    }


# (parse_interests now sourced from ._interests_parser)



def _pick_topic(interests: list[dict], state: dict, tick: int) -> str:
    last_news = state.get("last_news", {})
    def due_score(item: dict) -> float:
        last = last_news.get(item["topic"], -1)
        return 1000.0 if last == -1 else float(tick - last)
    candidates = sorted(interests, key=due_score, reverse=True)
    topic = candidates[0]["topic"]
    state["last_news"][topic] = tick
    return topic
