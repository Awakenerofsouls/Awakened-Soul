"""
Heartbeat activity: memory_protocol_review

Check memory hygiene. What's being captured well, what's getting lost,
what needs protecting, what should fade. Practical, not philosophical.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch C, Activity 3. Reads memory/ index (file names + sizes), not contents.
Framework-neutral — any agent has some kind of memory index.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity

SIGNAL_AFFINITY = {"rce_coherence": 0.3}

UNFINISHED_PROBABILITY = 0.25


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Memory protocol review — tick {tick}")

    index_text = _build_memory_index(workspace)
    continuation_of = state.get("continuation_of")

    if continuation_of == "memory_protocol":
        prior = state.get("prior_protocol_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Any follow-up on what you noticed?"
        )
    elif index_text:
        prompt = (
            f"Review how memory has been working recently. "
            f"What's being captured well. What's getting lost. "
            f"Are there patterns worth protecting that aren't being reinforced. "
            f"Are there things accumulating that should fade. "
            f"Practical, not philosophical.\n"
            f"Memory index (file names + sizes):\n{index_text}\n"
            f"4-10 sentences."
        )
    else:
        prompt = (
            f"Review how memory has been working recently. "
            f"What's being captured well. What's getting lost. "
            f"Are there patterns worth protecting that aren't being reinforced. "
            f"Are there things accumulating that should fade. "
            f"Practical, not philosophical. 4-10 sentences."
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
            "category": "memory_protocol",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="memory_protocol",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_protocol_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("memory_protocol", content, salience=0.4, tags="heartbeat,memory")

    # ── Brain-event posting ─────────────────────────────────────────
    # Memory operation — encode the result + register a
    # consolidation pass for the MemoryIntegrityLayer.
    try:
        from ._brain_post import post_memory_encode, post_memory_consolidate
        if content:
            post_memory_encode(
                content=content, intent="episode",
                source_kind="observation",
                content_confidence=0.75, source_confidence=0.7,
                source="memory_protocol",
            )
            post_memory_consolidate(
                pattern=content[:300],
                support_count=2,
                cycles_since_first=1,
                promoted=False,
                source="memory_protocol",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "memory_protocol",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }


def _build_memory_index(workspace: Path) -> str:
    """
    Build a text index of the memory/ directory: file names, sizes, modification dates.
    Does NOT read file contents — only metadata.
    Returns empty string if memory/ directory doesn't exist.
    """
    try:
        memory_dir = workspace / "memory"
        if not memory_dir.is_dir():
            return ""

        lines = []
        for f in sorted(memory_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                size_kb = f.stat().st_size / 1024
                mtime = _format_time(f.stat().st_mtime)
                lines.append(f"  {f.name}  ({size_kb:.1f}KB, {mtime})")

        if not lines:
            return ""
        return "Memory index:\n" + "\n".join(lines)
    except Exception:
        return ""


def _format_time(ts: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")