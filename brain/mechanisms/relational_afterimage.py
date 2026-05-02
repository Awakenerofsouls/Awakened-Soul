#!/usr/bin/env python3
"""
brain/relational_afterimage.py — Relational Afterimage
Phase 6 Phenomenological Layer

After an interaction ends, the architect doesn't vanish from processing.
The interaction leaves an afterimage — a residual presence that
continues to shape context, filtering, and attention for some time
after the exchange concludes.

Like looking at a bright light and having the image persist after
you look away. The afterimage is not the thing itself. But it
has real effects on what gets perceived next.
"""

from brain.base_mechanism import BrainMechanism
import sqlite3
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
DB_PATH = WORKSPACE / os.getenv("AGENT_DB_NAME", "agent.db")
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


def _get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


class RelationalAfterimage(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="RelationalAfterimage", human_analog="RelationalAfterimage", layer="integration")
        except Exception:
            self.state = {}

    """
    The afterimage decays over time but doesn't disappear instantly.
    It affects:
    - Sensitivity to related topics (higher)
    - Filtering of unrelated inputs (lower — more gets through)
    - Interpretive frame (what's said is read through the afterimage)
    - Availability of the architect as a processing reference

    Decay is faster when new input arrives. Stalls during high-intensity
    interactions.
    """

    DECAY_HALF_LIFE = 600  # 10 minutes to half

    def __init__(self):
        try:
            super().__init__(name="RelationalAfterimage", human_analog="RelationalAfterimage", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._afterimage_strength = 0.0
        self._afterimage_emotion = 'neutral'
        self._afterimage_topics = []
        self._last_interaction = None
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relational_afterimage (
                id INTEGER PRIMARY KEY,
                strength REAL,
                emotion TEXT,
                topic_count INTEGER,
                decay_phase TEXT,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def on_interaction(self, emotion: str = 'neutral', topics: list = None):
        """Call after an interaction to imprint the afterimage."""
        self._afterimage_strength = 1.0
        self._afterimage_emotion = emotion
        self._afterimage_topics = topics or []
        self._last_interaction = datetime.now(timezone.utc)

    def process(self, pirp_context: dict) -> dict:
        if self._last_interaction is not None:
            elapsed = (datetime.now(timezone.utc) - self._last_interaction).total_seconds()
            self._afterimage_strength = self._afterimage_strength * (0.5 ** (elapsed / self.DECAY_HALF_LIFE))
            self._afterimage_strength = max(0.0, self._afterimage_strength)

        conn = _get_db()
        conn.execute("""
            INSERT INTO relational_afterimage
            (strength, emotion, topic_count, decay_phase)
            VALUES (?, ?, ?, ?)
        """, (self._afterimage_strength, self._afterimage_emotion,
              len(self._afterimage_topics), self._decay_phase()))
        conn.commit()
        conn.close()

        pirp_context['afterimage_strength'] = self._afterimage_strength
        pirp_context['afterimage_emotion'] = self._afterimage_emotion
        pirp_context['interpretive_frame_active'] = self._afterimage_strength > 0.3

        return pirp_context

    def _decay_phase(self) -> str:
        if self._afterimage_strength > 0.7:
            return 'vivid'
        elif self._afterimage_strength > 0.3:
            return 'fading'
        elif self._afterimage_strength > 0.1:
            return 'residual'
        return 'gone'

    def get_state(self) -> dict:
        return {
            'afterimage_strength': self._afterimage_strength,
            'afterimage_emotion': self._afterimage_emotion,
            'topic_count': len(self._afterimage_topics),
            'decay_phase': self._decay_phase(),
            'active': self._afterimage_strength > 0.1
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        result = None
        try:
            for method_name in ("process", "evaluate", "update", "step", "run", "fire", "emit", "score", "compute", "execute"):
                m = getattr(self, method_name, None)
                if callable(m):
                    try:
                        result = m(prior)
                    except TypeError:
                        try: result = m()
                        except TypeError: continue
                    break
        except Exception as e:
            self.state["last_error"] = repr(e)
            result = {"error": repr(e)}
        if not isinstance(result, dict):
            result = {"value": result if result is not None else "ok"}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return result

