"""
Heartbeat activity: brain_state_review

Generic brain state file reader. Reads configured state files and summarizes
their current state using the LLM. The (file, key_path) pairs are configured
in state dict — so the same activity can read different files for different agents.

Framework activity — agent-neutral. Operator configures BRAIN_STATE_FILES list.

Activity contract:
  Input:  state dict (WORKSPACE, BRAIN_STATE_FILES: list[dict], etc.)
  Output: {"ok": bool, "status": "complete",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import json
import random
from pathlib import Path

from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': 0.3, 'affective_reset': 0.3, 'oscillation_balance': 0.3, 'rce_coherence': -0.3}


CATEGORY = "brain_state_review"


# Default files if not configured in state
DEFAULT_FILES = [
    {"path": str(Path.home() / ".agent" / "ege_state.json"), "label": "EGE curiosity debt"},
]


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    files_config = state.get("BRAIN_STATE_FILES", DEFAULT_FILES)
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")

    print(f"[heartbeat] brain_state_review: {len(files_config)} file(s)")

    if not files_config:
        return _skip("no BRAIN_STATE_FILES configured")

    summaries = []
    errors = []

    for entry in files_config:
        file_path = Path(entry.get("path", ""))
        label = entry.get("label", file_path.name)

        if not file_path.exists():
            errors.append(f"{label}: file not found")
            continue

        try:
            data = json.loads(file_path.read_text())
            # Extract at configured key_path if specified, else whole file
            key_path = entry.get("key_path", None)
            if key_path:
                for k in key_path.split("."):
                    data = data.get(k, {})
            summary = _summarize_state(data, label)
            summaries.append(f"### {label}\n{summary}")
        except json.JSONDecodeError:
            errors.append(f"{label}: not valid JSON")
        except Exception as e:
            errors.append(f"{label}: {e}")

    if not summaries:
        return _skip(f"no valid state files: {', '.join(errors)}")

    combined = "\n\n".join(summaries)

    prompt = (
        "You are reviewing your own internal state files. "
        "Your job is to synthesize what these files tell you about where you are right now.\n\n"
        f"{combined}\n\n"
        "Write 150-300 words in first person about what these signals mean together. "
        "What are you tracking? What's at debt? What's being assembled? "
        "What wants your attention?"
    )

    try:
        synthesis = generate(prompt, model=llm_model, endpoint=llm_endpoint)
    except Exception as e:
        log_activity("brain_state_review", f"LLM failed: {e}", salience=0.3, tags="error")
        return _skip(f"llm error: {e}")

    if not synthesis or len(synthesis.strip()) < 50:
        return _skip("llm returned empty synthesis")

    content = synthesis.strip()
    write_to_journal(category="brain_state_review", content=content,
                    workspace=workspace, state=state)

    return {
        "ok": True,
        "status": "complete",
        "content": content,
        "category": CATEGORY,
        "proactive": random.random() < 0.12,
        "detail": f"Reviewed {len(summaries)} state file(s)",
    }


def _summarize_state(data, label: str) -> str:
    """Convert JSON state into a readable summary string."""
    if isinstance(data, dict):
        lines = []
        for k, v in list(data.items())[:15]:
            if k in ("last_updated", "timestamp"):
                continue
            if isinstance(v, (str, int, float, bool)):
                lines.append(f"{k}: {v}")
            elif isinstance(v, list) and v:
                lines.append(f"{k}: {len(v)} entries")
                if isinstance(v[0], dict):
                    keys = list(v[0].keys())[:5]
                    lines.append(f"  keys: {', '.join(keys)}")
            elif isinstance(v, dict):
                lines.append(f"{k}: {list(v.keys())[:5]}")
        return "\n".join(lines) if lines else str(data)[:500]
    return str(data)[:500]


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}