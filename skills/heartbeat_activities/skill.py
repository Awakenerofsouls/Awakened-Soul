"""
Heartbeat activity: skill_exploration

Probe a skill — something you might be able to do but haven't proven.
Write a small attempt, then assess honestly.

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch B, Activity 3.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .interest_writer import try_append_new_interest
from ._interests_parser import parse_interests as _parse_interests
SIGNAL_AFFINITY = {'prediction_error': 0.5, 'affective_reset': -0.3, 'rce_coherence': 0.3}


UNFINISHED_PROBABILITY = 0.30


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
            "category": "skill_exploration",
            "content": "",
            "detail": "INTERESTS.md not found",
            "proactive": False,
        }

    interests = _parse_interests(interests_path)
    if not interests:
        return {
            "ok": False,
            "status": "complete",
            "category": "skill_exploration",
            "content": "",
            "detail": "No interests found",
            "proactive": False,
        }

    topic = _pick_topic(interests, state, tick)
    print(f"[heartbeat] Skill exploration: {topic}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "skill_exploration":
        prior = state.get("prior_skill_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Keep going or try something different?"
        )
    else:
        prompt = (
            f"Pick a skill related to '{topic}' that you're not sure you have yet. "
            f"Something you might be able to do but haven't proven. "
            f"Try it. Write a small attempt — a paragraph, a fragment, an analysis, whatever fits. "
            f"Then note honestly: did that work? Did it feel forced? What's missing? "
            f"4-10 sentences including the attempt."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.8,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "skill_exploration",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="skill_exploration",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_skill_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("skill_exploration", content, salience=0.4, tags="heartbeat,skill")


    # Grow interests — check if content revealed something new worth tracking
    if content:
        try_append_new_interest(content, state, source_activity="skill")

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
                source="skill",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="skill",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "skill_exploration",
        "detail": f"Topic: {topic}. {len(content)} chars.",
        "proactive": False,
    }


# (parse_interests now sourced from ._interests_parser)



def _pick_topic(interests: list[dict], state: dict, tick: int) -> str:
    last_skill = state.get("last_skill", {})
    def due_score(item: dict) -> float:
        last = last_skill.get(item["topic"], -1)
        return 1000.0 if last == -1 else float(tick - last)
    candidates = sorted(interests, key=due_score, reverse=True)
    topic = candidates[0]["topic"]
    # setdefault keeps this safe under parallel dispatch when the heartbeat's
    # state file didn't pre-initialize last_skill.
    state.setdefault("last_skill", {})[topic] = tick
    return topic
