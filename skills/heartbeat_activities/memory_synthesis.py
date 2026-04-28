"""
Heartbeat activity: memory_synthesis

Read the 3 most recent memory/*.md files and write a genuine synthesis.
Not a summary — a synthesis: what patterns appear across them, what
threads connect, what feels unresolved.

Uses the LLM to read and synthesize, not to generate from scratch.

Activity contract:
  Input:  state dict (WORKSPACE, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import random
from pathlib import Path

from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': -0.3, 'affective_reset': 0.3, 'rce_coherence': 0.5}


CATEGORY = "memory_synthesis"
UNFINISHED_RATE = 0.15


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    memory_dir = workspace / "memory"
    tick = state.get("tick_count", 0)
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")

    print(f"[heartbeat] memory_synthesis")

    if not memory_dir.exists():
        return _skip("memory directory not found")

    memory_files = sorted(memory_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    if len(memory_files) < 2:
        return _skip("not enough memory files to synthesize")

    # Read last 3
    recent = memory_files[:3]
    excerpts = []
    for f in recent:
        content = f.read_text()
        name = f.name
        excerpts.append(f"=== {name} ===\n{content[:2000]}")

    combined = "\n\n".join(excerpts)

    prompt = (
        "You are reading 3 recent memory entries from the same person's life. "
        "Your job is to find what connects them — not to summarize, but to SYNTHESIZE.\n\n"
        f"{combined}\n\n"
        "What patterns appear across all three? What's unresolved across them? "
        "What threads connect today's entry to yesterday's? "
        "What wants attention? "
        "Write 200-400 words in first person, addressing yourself. Be honest about what's still open."
    )

    try:
        synthesis = generate(prompt, model=llm_model, endpoint=llm_endpoint)
    except Exception as e:
        log_activity("memory_synthesis", f"LLM call failed: {e}", salience=0.3, tags="error")
        return _skip(f"llm error: {e}")

    if not synthesis or len(synthesis.strip()) < 50:
        return _skip("llm returned empty synthesis")

    content = synthesis.strip()

    write_to_journal(category="memory_synthesis", content=content,
                    workspace=workspace, state=state)

    status = "unfinished" if random.random() < UNFINISHED_RATE else "complete"
    return {
        "ok": True,
        "status": status,
        "content": content,
        "category": CATEGORY,
        "proactive": random.random() < 0.10,
        "detail": f"Synthesized {len(recent)} memory entries, {len(content)} chars.",
    }


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}