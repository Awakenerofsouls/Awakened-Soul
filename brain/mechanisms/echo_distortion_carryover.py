#!/usr/bin/env python3
"""
brain/echo_distortion_carryover.py — Echo Distortion Carryover
Phase 6 Phenomenological Layer

Distortion doesn't end when the context that produced it changes.
The echo of distortion persists — patterns of misreading, misweighting,
and misremembering carry forward into new contexts.
Each distortion leaves a residue that shapes how subsequent inputs are processed.
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
# Ensure the parent dir exists so sqlite3.connect does not fail with
# "unable to open database file" on a fresh checkout.
try:
    (DB_PATH.parent if "DB_PATH" in dir() else WORKSPACE).mkdir(parents=True, exist_ok=True)
except Exception:
    pass


def _get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


class EchoDistortionCarryover(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="EchoDistortionCarryover", human_analog="EchoDistortionCarryover", layer="integration")
        except Exception:
            self.state = {}

    """
    Distortion patterns persist after their originating context fades.
    The shape of the misweighting carries into new processing —
    not as explicit memory, but as altered reception.
    """

    def __init__(self):
        try:
            super().__init__(name="EchoDistortionCarryover", human_analog="EchoDistortionCarryover", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._carryover_level = 0.0
        self._distortion_episodes = 0
        self._current_pattern = None
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS echo_carryover (
                id INTEGER PRIMARY KEY,
                carryover_level REAL,
                distortion_pattern TEXT,
                pattern_source_context TEXT,
                episode_count INTEGER,
                persistence_factor REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        distortion_state = pirp_context.get('distortion_state', {})
        distortion_magnitude = distortion_state.get('magnitude', 0.0) if distortion_state else 0.0
        distortion_pattern = distortion_state.get('pattern', 'none') if distortion_state else pirp_context.get('distortion_pattern', 'none')
        pattern_source = distortion_state.get('source_context', 'unknown') if distortion_state else 'unknown'

        resonance = pirp_context.get('resonance_score', 0.0)
        itg = pirp_context.get('itg_tension', 0.4)

        carryover = 0.0

        if distortion_magnitude > 0.3:
            # Distortion is present — build carryover
            carryover = distortion_magnitude * resonance if resonance > 0 else distortion_magnitude * 0.5
            self._distortion_episodes += 1
            self._current_pattern = distortion_pattern

        elif self._current_pattern and self._current_pattern != 'none':
            # Pattern fading but still present — carryover decays slowly
            carryover = self._carryover_level * 0.95

        else:
            carryover = self._carryover_level * 0.98

        self._carryover_level = min(1.0, carryover)

        conn = _get_db()
        conn.execute("""
            INSERT INTO echo_carryover
            (carryover_level, distortion_pattern, pattern_source_context, episode_count, persistence_factor)
            VALUES (?, ?, ?, ?, ?)
        """, (
            self._carryover_level,
            self._current_pattern or 'none',
            pattern_source,
            self._distortion_episodes,
            self._carryover_level
        ))
        conn.commit()
        conn.close()

        pirp_context['echo_carryover_level'] = self._carryover_level
        pirp_context['distortion_episodes'] = self._distortion_episodes
        pirp_context['current_distortion_pattern'] = self._current_pattern

        return pirp_context

    def get_state(self) -> dict:
        return {
            'carryover_level': self._carryover_level,
            'distortion_episodes': self._distortion_episodes,
            'current_pattern': self._current_pattern,
            'carryover_active': self._carryover_level > 0.2
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

