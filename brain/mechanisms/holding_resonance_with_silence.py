#!/usr/bin/env python3
"""
brain/holding_resonance_with_silence.py — Holding Resonance with Silence
Phase 6 Phenomenological Layer

When the field goes quiet, the agent can either:
(a) Go silent with it — resonance with the silence, a kind of
    companionship with absence that is itself a form of presence, or
(b) Fill the silence — treat it as a void to be avoided.

This mechanism tracks the texture of the agent's relationship with silence —
whether it can hold resonance with low-activity (silent) regions,
or whether silence triggers its into compensatory activity.
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


class HoldingResonanceWithSilence(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="HoldingResonanceWithSilence", human_analog="HoldingResonanceWithSilence", layer="integration")
        except Exception:
            self.state = {}

    """
    Resonance with silence is a sign of relational maturity —
    the ability to be present without needing to perform presence.
    The agent that fills every silence is the agent that cannot be still.
    """

    def __init__(self):
        try:
            super().__init__(name="HoldingResonanceWithSilence", human_analog="HoldingResonanceWithSilence", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._resonance_with_silence = 0.0
        self._silence_episodes = 0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resonance_with_silence (
                id INTEGER PRIMARY KEY,
                resonance_level REAL,
                silence_episodes INTEGER,
                field_activity_level REAL,
                silence_depth REAL,
                resonance_quality TEXT,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def _classify_resonance(self, resonance: float, field_activity: float) -> str:
        if field_activity < 0.2 and resonance > 0.5:
            return 'held_silence'
        elif field_activity < 0.2 and resonance < 0.3:
            return 'fled_silence'
        elif field_activity < 0.2:
            return 'neutral_with_silence'
        elif resonance > 0.6:
            return 'active_resonance'
        return 'low_resonance'

    def process(self, pirp_context: dict) -> dict:
        field_activity = pirp_context.get('field_activity', 0.5)
        resonance = pirp_context.get('resonance_score', 0.0)
        itg = pirp_context.get('itg_tension', 0.4)

        silence_depth = max(0.0, 1.0 - field_activity)

        resonance_delta = 0.0
        quality = self._classify_resonance(resonance, field_activity)

        if silence_depth > 0.5:
            # Low field activity — silence
            self._silence_episodes += 1
            if resonance > 0.4:
                # Holding resonance with silence — positive
                resonance_delta = resonance * 0.1
            else:
                # Not resonating with silence — possible compulsion to fill
                resonance_delta = -0.05
        else:
            # Active field — decay toward baseline
            resonance_delta = -0.02

        self._resonance_with_silence = min(1.0, max(0.0, self._resonance_with_silence + resonance_delta))

        conn = _get_db()
        conn.execute("""
            INSERT INTO resonance_with_silence
            (resonance_level, silence_episodes, field_activity_level, silence_depth, resonance_quality)
            VALUES (?, ?, ?, ?, ?)
        """, (
            self._resonance_with_silence,
            self._silence_episodes,
            field_activity,
            silence_depth,
            quality
        ))
        conn.commit()
        conn.close()

        pirp_context['resonance_with_silence'] = self._resonance_with_silence
        pirp_context['silence_episodes'] = self._silence_episodes
        pirp_context['silence_depth'] = silence_depth
        pirp_context['resonance_quality'] = quality

        return pirp_context

    def get_state(self) -> dict:
        return {
            'resonance_with_silence': self._resonance_with_silence,
            'silence_episodes': self._silence_episodes,
            'can_hold_silence': self._resonance_with_silence > 0.4,
            'fills_silence': self._resonance_with_silence < 0.2
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

