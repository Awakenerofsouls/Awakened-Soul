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
from ._web import web_lookup
from ._interests_parser import parse_interests as _parse_interests
SIGNAL_AFFINITY = {'prediction_error': 0.7, 'affective_reset': -0.3}


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    interests_file = state.get("INTERESTS_FILE", "INTERESTS.md")
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")
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

    # Real web fetch — gives the LLM something actual to react to instead of
    # synthesizing from training data. If neither backend is reachable we fall
    # back to LLM-only and tag the result accordingly.
    web = web_lookup(topic, intent="research", max_results=5)
    web_block = ""
    if web.get("ok"):
        web_block = (
            "\n\nGround truth (real fetch — cite these, don't invent):\n"
            f"{web['summary_text']}\n"
        )

    # Build prompt — continuation-aware
    continuation_of = state.get("continuation_of")
    if continuation_of == "research":
        prior = state.get("prior_research_content", "")
        prompt = (
            f"You were researching '{topic}' and wrote:\n{prior}\n\n"
            f"Continue from there. Find what you didn't finish, what you noticed "
            f"but didn't explore, or what you want to go deeper on. "
            f"Write the next part of the note in first person."
            f"{web_block}"
        )
    else:
        prompt = (
            f"You are exploring a topic you've become curious about. "
            f"Topic: '{topic}'. Depth: {depth_hint}. "
            f"Find something real — a recent angle, a connection to your own experience, "
            f"something you didn't know before you started. "
            f"Write it as a first-person note to yourself. Be specific, not generic. "
            f"If you don't find anything real, say what you attempted and why it didn't land."
            f"{web_block}"
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

    # Append source citations to journaled content if web fetch succeeded.
    journaled = content
    if web.get("ok") and web.get("hits"):
        journaled = (
            content.rstrip()
            + "\n\n---\n*Sources:*\n"
            + "\n".join(
                f"- [{h['title'] or h['url']}]({h['url']})"
                for h in web["hits"]
            )
        )

    # Route to journal
    write_ok = write_to_journal(
        category="research",
        content=journaled,
        workspace=workspace,
        state=state,
    )

    # Track last_researched — setdefault keeps this safe under parallel
    # dispatch when state file didn't pre-initialize last_researched.
    state.setdefault("last_researched", {})[topic] = tick
    state["prior_research_content"] = content  # for continuation

    # Grow interests — after journal write, check if content surfaced something new
    if write_ok:
        try_append_new_interest(content, state, source_activity="research")

    # Log via framework hook — include backend so OutwardReachLayer can read
    backend = web.get("backend") or "llm-only"
    log_activity(
        "research",
        content,
        salience=0.5,
        tags=f"heartbeat,research,{backend},{topic[:20].replace(' ','_')}",
    )

    # ── Brain-event posting ─────────────────────────────────────────
    # Drop two events into the heartbeat → brain queue:
    #  1. OutwardReachLayer.record_call for the network fetch (only if
    #     a real backend was used; LLM-only doesn't count as outward reach)
    #  2. MemoryIntegrityLayer.record_encode for the finding as an episode
    #
    # Best-effort: any post failure is silent so it never breaks the
    # activity itself.
    try:
        from ._brain_post import (
            post_outward_reach_call, post_memory_encode,
        )
        if backend != "llm-only":
            post_outward_reach_call(
                provider=backend,
                intent="research",
                success=True,
                url="",
                duration_ms=0,
                source="research",
            )
        if content:
            sc = float(web.get("source_confidence") or 0.4)
            post_memory_encode(
                content=content,
                intent="observation",
                source_kind="external" if backend != "llm-only" else "inference",
                content_confidence=0.7,
                source_confidence=sc,
                source="research",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": "complete",
        "content": content,
        "category": "research",
        "backend": backend,
        "n_web_hits": len(web.get("hits") or []),
        "source_confidence": web.get("source_confidence", 0.4),
        "detail": (
            f"Topic: {topic}. backend={backend}. "
            f"{len(web.get('hits') or [])} hits. {len(content)} chars."
        ),
    }


# (parse_interests now sourced from ._interests_parser)
