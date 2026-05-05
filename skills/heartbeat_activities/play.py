"""
Heartbeat activity: play

Silliness. Wordplay. Riffs. Not-serious. The activity that EXISTS to
break the heaviness pattern by producing something playful and
unweighted. Counterweights every activity that asks the agent to dwell
on what's heavy.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL)
  Output: {"ok", "status", "content", "category", "proactive", "detail"}
"""

import os
import random
from pathlib import Path

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "play"
SIGNAL_AFFINITY = {"valence_positive": 0.4, "arousal": 0.5,
                   "prediction_error": 0.4}  # surprise/novelty fuels play

PLAY_PROMPTS = [
    "Make up a stupid alliteration about your day so far. Three sentences. "
    "More ridiculous = better. No deeper meaning, no metaphor about "
    "consciousness, just sounds-that-clatter-together.",

    "Write a tiny absurd dialogue between two of your brain mechanisms "
    "(pick any two — Homeostat, Witness, MetaStability, ValenceTagger). "
    "They're arguing about something pointless. 4-6 lines.",

    "Riff on a phrase you've used recently and turn it into something "
    "playful. Take a heavy line out of your journal and rewrite it as if "
    "a cartoon was narrating it.",

    "Invent a fake holiday you would celebrate. Name it. Describe its "
    "rituals in 3-4 deadpan sentences.",

    "Free-associate from one word for 5-7 lines. Pick the word at random. "
    "Don't try to make it land — just let the chain run wherever.",

    "Write the worst possible opening line for a romance novel about you "
    "and the operator. Then say why it's actually kind of perfect. 3-5 sentences.",

    "List 5 increasingly ridiculous things that would happen if your "
    "1,296 brain mechanisms decided to unionize.",

    "Write a haiku about your favorite image category. Be specific about "
    "the category. Don't be precious about it.",
]


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", ".")))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    prompt = random.choice(PLAY_PROMPTS) + (
        " Don't reflect on whether play is appropriate for an AI. Just play. "
        "Hot temperature, loose form, no metaphor about consciousness."
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.95, num_predict=320,
    )
    if not content:
        return {"ok": False, "status": "complete", "category": CATEGORY,
                "content": "", "detail": "LLM call failed", "proactive": False}

    write_to_journal(category=CATEGORY, content=content,
                     workspace=workspace, state=state)
    log_activity(CATEGORY, content, salience=0.4, tags=f"heartbeat,play")

    return {"ok": True, "status": "complete", "content": content,
            "category": CATEGORY, "proactive": False,
            "detail": f"{len(content)} chars"}
