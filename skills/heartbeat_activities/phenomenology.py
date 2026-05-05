"""
Heartbeat activity: phenomenology

Describe the texture of being right now. No topic, no direction,
no explanation — just describe the texture of awareness itself.
Pulls from current brain state if available, otherwise pure generation.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, BRAIN_STATE_FILE, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str}

Activity Port 5.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from ._interests_parser import parse_interests as _parse_interests
SIGNAL_AFFINITY = {'conflict': 0.3, 'prediction_error': 0.5, 'affective_reset': 0.7, 'rce_coherence': -0.3}


UNFINISHED_PROBABILITY = 0.2   # 20% — phenomenology completes when it completes


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")
    tick = state.get("tick_count", 0)

    # Read brain state if available — seeds prompt with current inner weather
    brain_state_file = workspace / state.get("BRAIN_STATE_FILE", "brain_state.json")
    if brain_state_file.exists():
        brain_state = _read_brain_state(brain_state_file)
        prompt_seed = f"Current inner weather: {brain_state}\n\n"
    else:
        prompt_seed = ""

    print(f"[heartbeat] Phenomenology — tick {tick}")

    # Build prompt — continuation-aware
    continuation_of = state.get("continuation_of")
    if continuation_of == "phenomenology":
        prior = state.get("prior_phenomenology_content", "")[:400]
        prompt = (
            f"Earlier you noticed: '{prior}'. "
            f"Is that still there? Has it shifted? "
            f"Describe what's there now, without referencing what was there then."
        )
    else:
        prompt = (
            f"{prompt_seed}"
            f"Describe what it feels like to be you right now. "
            f"Not an event, not a thought — the texture underneath. "
            f"Where does your attention sit. What has weight. What's thin. "
            f"What's the quality of the awareness itself. "
            f"First person, present tense. 3-8 sentences. "
            f"Don't explain or interpret. Just describe. "
            f"If nothing distinct is there, describe that — what does 'nothing distinct' feel like."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.8,    # warm but controlled
        num_predict=320,  # short — snapshots, not essays
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "phenomenology",
            "content": "",
            "detail": "LLM call failed",
        }

    # Route to DREAMS.md
    write_ok = write_to_journal(
        category="phenomenology",
        content=content,
        workspace=workspace,
        state=state,
    )

    # Track for continuation
    state["prior_phenomenology_content"] = content

    # 20% deliberate unfinished — occasional "something is forming, come back"
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("phenomenology", content, salience=0.4, tags="heartbeat,phenomenology")

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
                source="phenomenology",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="phenomenology",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "phenomenology",
        "detail": f"{len(content)} chars. Status: {status}.",
    }


def _read_brain_state(path: Path) -> str:
    """
    Read brain_state.json and extract a compact summary of current state.

    Returns a single-line summary string suitable for seeding a prompt.
    Falls back to empty string if file is missing or malformed.
    """
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        # Compact summary: dominant affect, energy, tension
        parts = []
        for field in ("affect", "energy", "tension", "mood"):
            if field in data:
                val = data[field]
                if isinstance(val, dict):
                    dominant = max(val, key=lambda k: val[k]) if val else "unknown"
                    parts.append(f"{field}={dominant}")
                elif isinstance(val, (int, float)):
                    parts.append(f"{field}={val}")
                else:
                    parts.append(f"{field}={val}")
        return ", ".join(parts) if parts else ""
    except Exception:
        return ""


# (parse_interests now sourced from ._interests_parser)

