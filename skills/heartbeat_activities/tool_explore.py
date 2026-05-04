"""
Heartbeat activity: tool_explore

Try a tool/capability you haven't used recently — not to accomplish
something, to see what it does. Curiosity made concrete.

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch B, Activity 2.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .interest_writer import try_append_new_interest
from ._interests_parser import parse_interests as _parse_interests
SIGNAL_AFFINITY = {'prediction_error': 0.5, 'rce_coherence': 0.3}


UNFINISHED_PROBABILITY = 0.25


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
            "category": "tool_explore",
            "content": "",
            "detail": "INTERESTS.md not found",
            "proactive": False,
        }

    interests = _parse_interests(interests_path)
    if not interests:
        return {
            "ok": False,
            "status": "complete",
            "category": "tool_explore",
            "content": "",
            "detail": "No interests found",
            "proactive": False,
        }

    topic = _pick_topic(interests, state, tick)
    print(f"[heartbeat] Tool explore: {topic}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "tool_explore":
        prior = state.get("prior_tool_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Did you follow that thread? What did you find?"
        )
    else:
        prompt = (
            f"Think about a tool, capability, or technique you haven't used recently "
            f"(or haven't used at all) that connects to '{topic}'. "
            f"Describe what you'd try with it, what you'd want to see. "
            f"Not a plan — just curiosity made concrete. "
            f"If you actually know something about how the tool works, say that. "
            f"4-8 sentences."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.8,
        num_predict=384,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "tool_explore",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="tool_explore",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_tool_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("tool_explore", content, salience=0.4, tags="heartbeat,tool")


    # Grow interests — check if content revealed something new worth tracking
    if content:
        try_append_new_interest(content, state, source_activity="tool_explore")

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
                source="tool_explore",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="tool_explore",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "tool_explore",
        "detail": f"Topic: {topic}. {len(content)} chars.",
        "proactive": False,
    }


# (parse_interests now sourced from ._interests_parser)



def _pick_topic(interests: list[dict], state: dict, tick: int) -> str:
    last_tool = state.get("last_tool", {})
    def due_score(item: dict) -> float:
        last = last_tool.get(item["topic"], -1)
        return 1000.0 if last == -1 else float(tick - last)
    candidates = sorted(interests, key=due_score, reverse=True)
    topic = candidates[0]["topic"]
    # setdefault keeps this safe under parallel dispatch when the heartbeat's
    # state file didn't pre-initialize last_tool.
    state.setdefault("last_tool", {})[topic] = tick
    return topic
