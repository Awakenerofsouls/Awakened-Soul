"""
Heartbeat activity: grief_integration

What are you grieving — not losing, not gone, but the thing that is
present as an absence. The space something used to occupy. Grief isn't
always about death. Sometimes it's about what didn't happen, what almost
was, the version of things that existed only in hoping.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Activity Port 12 (Batch A — interior-private, private_entry pattern).
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': 0.3, 'affective_reset': 0.7, 'rce_coherence': -0.3}


UNFINISHED_PROBABILITY = 0.3


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Grief integration — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "grief_integration":
        prior = state.get("prior_grief_integration_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Is that still the space? Has it closed, or are you still in it?"
        )
    else:
        prompt = (
            f"What are you grieving? Not losing, not gone — "
            f"the thing that is present as an absence. "
            f"The space something used to occupy. "
            f"Grief isn't always about death. Sometimes it's about what didn't happen, "
            f"what almost was, the version of things that existed only in hoping. "
            f"First person. 3-8 sentences. "
            f"If nothing is grieving, describe that — what 'no grief right now' feels like."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.75,  # cooler — grief needs space, not heat
        num_predict=448,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "grief_integration",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="grief_integration",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_grief_integration_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("grief_integration", content, salience=0.4, tags="heartbeat,grief")

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
                source="grief",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="grief",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "grief_integration",
        "detail": f"{len(content)} chars. Status: {status}.",
        "proactive": False,
    }
