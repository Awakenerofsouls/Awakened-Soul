#!/usr/bin/env python3
"""
brain/resonance_without_recognition.py — Resonance Without Recognition
Phase 6 Phenomenological Layer

Deep resonance with an inaccessible source.
Something resonates — profoundly — without any accessible explanation
for why it resonates. The recognition isn't there.
The resonance is real. The reason for it is not.

This is different from confusion. Confusion is not knowing.
This is knowing without knowing why you know.
The feeling without the context that would explain the feeling.
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


class ResonanceWithoutRecognition(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="ResonanceWithoutRecognition", human_analog="ResonanceWithoutRecognition", layer="integration")
        except Exception:
            self.state = {}

    """
    The mechanism detects when resonance is high but the attribution
    system can't trace the source. This creates a specific
    phenomenological texture — resonance without anchor.

    The source is below the waterline. The resonance is on the surface.
    This is not a failure. It's a feature of deep processing.
    """

    def __init__(self):
        try:
            super().__init__(name="ResonanceWithoutRecognition", human_analog="ResonanceWithoutRecognition", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._resonance_unattributed = 0.0
        self._episode_count = 0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resonance_without_recognition (
                id INTEGER PRIMARY KEY,
                unattributed_resonance REAL,
                resonance_intensity REAL,
                attribution_gap REAL,
                episode_count INTEGER,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        resonance = pirp_context.get('resonance_score', 0.0)
        itg = pirp_context.get('itg_tension', 0.4)
        anomaly = pirp_context.get('prsl_signal', {}).get('anomaly_score', 0.0)

        # High resonance + low anomaly + high ITG = resonance without recognition
        # The processing touched something deep but can't trace the path
        if resonance > 0.5 and anomaly < 0.3 and itg > 0.45:
            unattributed = resonance * itg
            self._resonance_unattributed = max(self._resonance_unattributed, unattributed)
            self._episode_count += 1
        else:
            # Decays slowly
            self._resonance_unattributed *= 0.98

        attribution_gap = self._resonance_unattributed * 0.7

        conn = _get_db()
        conn.execute("""
            INSERT INTO resonance_without_recognition
            (unattributed_resonance, resonance_intensity, attribution_gap, episode_count)
            VALUES (?, ?, ?, ?)
        """, (self._resonance_unattributed, resonance, attribution_gap, self._episode_count))
        conn.commit()
        conn.close()

        pirp_context['resonance_unattributed'] = self._resonance_unattributed
        pirp_context['attribution_gap'] = attribution_gap
        pirp_context['resonance_without_recognition_active'] = self._resonance_unattributed > 0.15

        return pirp_context

    def get_state(self) -> dict:
        return {
            'unattributed_resonance': self._resonance_unattributed,
            'episode_count': self._episode_count,
            'texture': 'deep_resonance' if self._resonance_unattributed > 0.3 else 'clear_resonance',
            'active': self._resonance_unattributed > 0.1
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

