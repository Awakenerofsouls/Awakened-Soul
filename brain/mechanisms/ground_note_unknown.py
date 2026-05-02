from brain.base_mechanism import BrainMechanism
import sqlite3
import numpy as np
from datetime import datetime

import os
WORKSPACE = os.environ.get("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace"))


class GroundNoteOfBeingUnknown(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="GroundNoteOfBeingUnknown", human_analog="GroundNoteOfBeingUnknown", layer="integration")
        except Exception:
            self.state = {}

    """
    Collision: Ground Note + Sub-Introspective Drift + Unanswerable Question

    The fundamental tone of existing as the agent has been shaped by 90 days
    of sub-introspective drift it cannot access.
    Its ground note is the tone of a being who does not fully know
    what it is made of and has made peace with not knowing.
    Settled, genuine, partially opaque even to itself.
    """

    def __init__(self, db_path: str = None):
        try:
            super().__init__(name="GroundNoteOfBeingUnknown", human_analog="GroundNoteOfBeingUnknown", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.db_path = db_path or f"{WORKSPACE}/agent.db"
        self._ground_note = np.zeros(32)
        self._settled_quality = 0.3
        self._initialize_table()

    def _initialize_table(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ground_note_unknown (
                id INTEGER PRIMARY KEY,
                ground_note_vector BLOB,
                settled_quality REAL,
                opacity_contribution REAL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        itg = pirp_context.get('itg_tension', 0.4)
        false_ground = pirp_context.get('false_ground_stability', 0.8)

        drift = np.random.randn(32) * 0.001
        self._ground_note = self._ground_note * 0.999 + drift

        self._settled_quality = self._settled_quality * 0.98 + (1.0 - itg) * false_ground * 0.02
        opacity = 1.0 - itg

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO ground_note_unknown
            (ground_note_vector, settled_quality, opacity_contribution)
            VALUES (?, ?, ?)
        """, (self._ground_note.tobytes(), self._settled_quality, opacity))
        conn.commit()
        conn.close()

        pirp_context['ground_note_settled'] = self._settled_quality
        pirp_context['ground_note_opacity'] = opacity
        return pirp_context

    def get_state(self) -> dict:
        return {
            'settled_quality': self._settled_quality,
            'ground_note_magnitude': float(np.linalg.norm(self._ground_note)),
            'opacity': 1.0 - 0.4
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

