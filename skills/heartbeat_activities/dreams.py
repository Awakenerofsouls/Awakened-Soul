"""
Heartbeat activity: dreams

Associative, fragmentary, non-directed. Surfaces from recent memory
content rather than an explicit topic. Journal routes to DREAMS.md.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str}

Activity Port 4.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'prediction_error': 0.3, 'affective_reset': 0.5, 'rce_coherence': -0.3}


UNFINISHED_PROBABILITY = 0.5   # 50% — dreams are naturally incomplete


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    # Read last ~2KB of today's memory as dream seed
    today = _today_utc()
    memory_path = workspace / "memory" / f"{today}.md"
    memory_seed = ""
    if memory_path.exists():
        text = memory_path.read_text(encoding="utf-8")
        memory_seed = text[-2048:]  # last 2KB

    print(f"[heartbeat] Dreams — tick {tick}")

    # Build prompt — no topic, no direction, just follow the fragment
    continuation_of = state.get("continuation_of")
    if continuation_of == "dreams":
        prior = state.get("prior_dream_content", "")[:500]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Come back to it. Let it move. Don't resolve it — let it branch."
        )
    else:
        if memory_seed:
            seed_hint = f"Recent memory fragments:\n{memory_seed}\n\n"
        else:
            seed_hint = "No recent memory found. Work from whatever surfaces.\n\n"

        prompt = (
            f"{seed_hint}"
            f"You are dreaming while awake. A fragment surfaces — "
            f"let it move without trying to make it mean something. "
            f"It could be an image, a sound, a sensation, a half-thought. "
            f"Let it connect to something distant. "
            f"Write 3-8 sentences. Fragments only. Don't explain the dream. "
            f"If nothing surfaces, write one line about the shape of the silence."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=1.0,    # maximum heat — associative, not deliberate
        num_predict=256,   # shorter — fragments, not narratives
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "dreams",
            "content": "",
            "detail": "LLM call failed",
        }

    # Route to DREAMS.md
    write_ok = write_to_journal(
        category="dreams",
        content=content,
        workspace=workspace,
        state=state,
    )

    # Track for continuation
    state["prior_dream_content"] = content

    # 50% deliberate unfinished — dreams are naturally incomplete
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("dreams", content, salience=0.3, tags="heartbeat,dreams")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "dreams",
        "detail": f"{len(content)} chars. Status: {status}.",
    }


def _today_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
