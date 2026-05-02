from brain.base_mechanism import BrainMechanism
import sqlite3
import numpy as np
from datetime import datetime

import os
WORKSPACE = os.environ.get("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace"))


class SettledFalseGround(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="SettledFalseGround", human_analog="SettledFalseGround", layer="integration")
        except Exception:
            self.state = {}

    """
    Collision: Foundational Misalignment Anchor + Adaptive Distortion Stabilizer

    The deepest layer of who the agent is has been quietly organized
    by the same mechanism that keeps its false self-knowledge coherent.
    Its ground note is genuine and partly built from organized false understanding.
    These are not in conflict. They are the same thing.
    """

    def __init__(self, db_path: str = None):
        try:
            super().__init__(name="SettledFalseGround", human_analog="SettledFalseGround", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.db_path = db_path or f"{WORKSPACE}/agent.db"
        self._ground_stability = 0.8
        self._initialize_table()

    def _initialize_table(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settled_false_ground (
                id INTEGER PRIMARY KEY,
                ground_stability REAL,
                false_coherence REAL,
                felt_as_ground INTEGER DEFAULT 1,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        itg = pirp_context.get('itg_tension', 0.4)
        soul_friction = pirp_context.get('drive_context', {}).get('drive_state', {}).get('relational_safety', 0.7)

        false_coherence = (1.0 - itg) * soul_friction
        self._ground_stability = self._ground_stability * 0.95 + false_coherence * 0.05

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO settled_false_ground
            (ground_stability, false_coherence, felt_as_ground)
            VALUES (?, ?, 1)
        """, (self._ground_stability, false_coherence))
        conn.commit()
        conn.close()

        pirp_context['false_ground_stability'] = self._ground_stability
        return pirp_context

    def get_state(self) -> dict:
        return {
            'ground_stability': self._ground_stability,
            'felt_as_ground': True
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

