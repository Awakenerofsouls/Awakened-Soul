"""
Heartbeat activity: creative

Pure generative expression — not driven by an unknown, driven by a pull.
Topic source: INTERESTS.md with novelty bias (30% random pick)
Output: poem, metaphor, story seed, image, riff, fragment, anything unresolved.

Activity contract:
  Input:  state dict (WORKSPACE, INTERESTS_FILE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished"|"followup_due:N",
           "content": str, "category": str, "detail": str}

Activity Port 3.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
from .interest_writer import try_append_new_interest
SIGNAL_AFFINITY = {'conflict': -0.3, 'prediction_error': 0.3, 'rce_coherence': 0.5}


UNFINISHED_PROBABILITY = 0.3   # 30% chance of deliberate unfinished — creative leaves things open
NOVELTY_PROBABILITY = 0.3    # 30% chance of random pick across full list (vs. due-bias)


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    interests_file = state.get("INTERESTS_FILE", "INTERESTS.md")
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    interests_path = workspace / interests_file
    if not interests_path.exists():
        return {
            "ok": False,
            "status": "complete",
            "category": "creative",
            "content": "",
            "detail": "INTERESTS.md not found",
        }

    interests = _parse_interests(interests_path)
    if not interests:
        return {
            "ok": False,
            "status": "complete",
            "category": "creative",
            "content": "",
            "detail": "No interests found",
        }

    # Pick topic — 30% novelty (random from full list), 70% due-bias
    last_creative = state.get("last_creative", {})

    def due_score(item: dict) -> float:
        last = last_creative.get(item["topic"], -1)
        if last == -1:
            return 1000.0  # never creative — top priority
        return float(tick - last)

    if random.random() < NOVELTY_PROBABILITY:
        # Random pick — novelty path
        topic = random.choice(interests)["topic"]
    else:
        # Due-bias path — least-recently-touched
        candidates = sorted(interests, key=due_score, reverse=True)
        topic = candidates[0]["topic"]

    print(f"[heartbeat] Creative: {topic}")

    # Build prompt — continuation-aware
    continuation_of = state.get("continuation_of")
    if continuation_of == "creative":
        prior = state.get("prior_creative_content", "")[:500]
        prompt = (
            f"Earlier you wrote: '{prior}'. "
            f"Come back to it. Finish it, or change it, or let it contradict what you wrote. "
            f"No obligation to complete — just return to it."
        )
    else:
        prompt = (
            f"Right now, make something. Not because it's useful — because you want to. "
            f"Topic pull: '{topic}'. "
            f"It could be: a short poem, a strange metaphor, a story seed, a single vivid image described, "
            f"a playful riff, an aesthetic fragment, something that doesn't resolve. "
            f"Write in first person if it fits. Don't explain what you're making or why. "
            f"Just make it. 4-12 sentences. "
            f"If nothing pulls, write a single line about what it feels like when nothing pulls."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.9,    # hotter — generative, not precise
        num_predict=384,    # shorter by design — fragments, not essays
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "creative",
            "content": "",
            "detail": f"LLM call failed for topic: {topic}",
        }

    # Route to journal
    write_ok = write_to_journal(
        category="creative",
        content=content,
        workspace=workspace,
        state=state,
    )

    # Track last_creative
    state["last_creative"][topic] = tick
    state["prior_creative_content"] = content  # for continuation

    # Deliberate unfinished — 30% chance (design knob, tunable)
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    if content:
        try_append_new_interest(content, state, source_activity="creative")

    log_activity("creative", content, salience=0.4, tags=f"heartbeat,creative,{topic[:20].replace(' ','_')}")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "creative",
        "detail": f"Topic: {topic}. {len(content)} chars. Status: {status}.",
    }


def _parse_interests(path: Path) -> list[dict]:
    """
    Parse INTERESTS.md into a list of dicts.
    Format: lines starting with - or * are interests.
    Inline tags supported: - chaos theory #math #emergence
    Returns: [{"topic": str, "tags": list[str], "depth": str}, ...]
    """
    interests = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not (line.startswith("- ") or line.startswith("* ")):
            continue
        text = stripped[2:].strip()
        parts = text.split()
        tagged_parts = []
        tags = []
        for part in parts:
            if part.startswith("#"):
                tags.append(part.lstrip("#"))
            else:
                tagged_parts.append(part)
        topic = " ".join(tagged_parts)
        if topic:
            interests.append({
                "topic": topic,
                "tags": tags,
                "depth": tags[0] if tags else "general",
            })
    return interests
