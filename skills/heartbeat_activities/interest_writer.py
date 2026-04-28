"""
Interest writer — post-generation hook for heartbeat activities.

After an activity generates content, checks if the content revealed a genuinely
new interest {{AGENT_NAME}} wants to track. If yes, appends to INTERESTS.md via the
existing append_interest() which also seeds EGE curiosity debt.

Usage:
    from .interest_writer import try_append_new_interest

    content = generate(...)
    write_to_journal(...)

    if content:
        try_append_new_interest(content, state, source_activity="research")

Non-fatal: never raises, always fails gracefully.
"""

from pathlib import Path
from typing import Optional


_EXTRACT_PROMPT = (
    "Here's something I just wrote to myself:\n\n"
    "---\n{content}\n---\n\n"
    "Did I land on a new topic or interest I want to come back to later "
    "that isn't obvious from the starting seed? "
    "If yes, respond with ONLY the topic in 2-6 words, nothing else. "
    "If no, respond with only the word: NONE"
)


def try_append_new_interest(content: str, state: dict, source_activity: str) -> Optional[str]:
    """
    Ask the LLM if content surfaced a new interest. If yes, append it.

    Args:
        content: The generated text from the activity.
        state: Heartbeat state dict (used for LLM config + tick_count).
        source_activity: String category (e.g. "research", "creative") for logging.

    Returns:
        The appended topic string if successful, None otherwise.
    """
    if not content or len(content) < 100:
        return None

    try:
        # Import LLM helper and append_interest from skills
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from skills.interests import append_interest
        from skills.heartbeat_activities.llm import generate
        from skills.heartbeat_activities.log import log_activity

        endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
        model = state.get("LLM_MODEL", "qwen2.5vl:7b")

        resp = generate(
            _EXTRACT_PROMPT.format(content=content[:1500]),
            model=model,
            endpoint=endpoint,
        )
        resp = (resp or "").strip().strip('"').strip("'")

        # Sanity-check the LLM response
        if (
            not resp
            or resp.upper() == "NONE"
            or len(resp.split()) > 8
            or len(resp) < 3
        ):
            return None

        append_interest(
            resp,
            category=source_activity,
            seed_ege=True,
            trigger=f"heartbeat:{source_activity}",
        )
        log_activity(
            "interest_writer",
            f"New interest: '{resp}'",
            salience=0.3,
            tags=f"interest_grow,{source_activity}",
        )
        return resp

    except Exception:
        return None