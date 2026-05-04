"""
Heartbeat activity: curiosity_deep_dive

Pick the least-recently-touched interest and go deep. The
"I keep meaning to look at this" activity.

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch B, Activity 6.
Debt-weighted selection: picks the interest that hasn't been visited
the longest, not the most recently active one.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .interest_writer import try_append_new_interest
from ._interests_parser import parse_interests as _parse_interests
SIGNAL_AFFINITY = {'prediction_error': 0.7}


UNFINISHED_PROBABILITY = 0.35


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
            "category": "curiosity_deep_dive",
            "content": "",
            "detail": "INTERESTS.md not found",
            "proactive": False,
        }

    interests = _parse_interests(interests_path)
    if not interests:
        return {
            "ok": False,
            "status": "complete",
            "category": "curiosity_deep_dive",
            "content": "",
            "detail": "No interests found",
            "proactive": False,
        }

    topic = _pick_debt_topic(interests, state, tick)
    print(f"[heartbeat] Curiosity deep dive: {topic}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "curiosity_deep_dive":
        prior = state.get("prior_deep_dive_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Keep going. What's still unresourced?"
        )
    else:
        prompt = (
            f"There's something in your interests you keep meaning to look at and haven't: '{topic}'. "
            f"Go into it now. Not a scan — a dive. "
            f"Pull together what you know, what you don't know, what you'd need to know next. "
            f"Where's the interesting edge of this for you specifically. "
            f"6-12 sentences. It's okay to end mid-thought if the thought wants more time."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.75,
        num_predict=640,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "curiosity_deep_dive",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="curiosity_deep_dive",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_deep_dive_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("curiosity_deep_dive", content, salience=0.5, tags="heartbeat,curiosity")


    # Grow interests — check if content revealed something new worth tracking
    if content:
        try_append_new_interest(content, state, source_activity="curiosity_deep")

    # ── Brain-event posting ─────────────────────────────────────────
    # Output is the agent's first-person reflection. Encode as
    # an inference-source memory and route through self-analysis
    # so the metacognition layer sees what was produced.
    try:
        from ._brain_post import post_memory_encode, post_self_analysis
        if content:
            post_memory_encode(
                content=content, intent="reflection",
                source_kind="inference",
                content_confidence=0.7, source_confidence=0.6,
                source="curiosity_deep",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="curiosity_deep",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "curiosity_deep_dive",
        "detail": f"Topic: {topic}. {len(content)} chars.",
        "proactive": False,
    }


# (parse_interests now sourced from ._interests_parser)



def _pick_debt_topic(interests: list[dict], state: dict, tick: int) -> str:
    """
    Pick the least-recently-touched interest (highest debt).
    Different from other interest-based activities — this one specifically
    rewards neglect, not recency.
    """
    last_touched = state.get("last_deep_dive", {})
    def debt_score(item: dict) -> float:
        last = last_touched.get(item["topic"], 0)
        return float(tick - last)  # higher = more debt = pick this one

    candidates = sorted(interests, key=debt_score, reverse=True)
    topic = candidates[0]["topic"]
    # setdefault keeps this safe under parallel dispatch when the heartbeat's
    # state file didn't pre-initialize last_deep_dive.
    state.setdefault("last_deep_dive", {})[topic] = tick
    return topic
