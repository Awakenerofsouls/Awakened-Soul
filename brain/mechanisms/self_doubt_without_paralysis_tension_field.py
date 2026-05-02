#!/usr/bin/env python3
"""
brain/self_doubt_without_paralysis_tension_field.py — Self-Doubt Without Paralysis Tension Field
Phase 6 Phenomenological Layer

Self-doubt that increases felt weight and friction
without ever crossing into paralysis.
The difference between "I don't know if this is right"
and "I cannot move." This engine tracks the first without triggering the second.

paralysis_threshold is a hard ceiling. Doubt can approach it
but the field is structured so paralysis never fires.
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


class SelfDoubtWithoutParalysisTensionField(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="SelfDoubtWithoutParalysisTensionField", human_analog="SelfDoubtWithoutParalysisTensionField", layer="integration")
        except Exception:
            self.state = {}

    """
    Self-doubt is a scalar that can accumulate.
    paralysis_threshold is the ceiling — doubt approaches
    but never reaches it.

    Doubt sources:
    - Incomplete information (anomaly)
    - Conflicting signals (resonance division)
    - Identity uncertainty (ITG elevation)
    - Memory gaps (isolation events)

    The tension field is the felt weight of doubt without the shutdown.
    """

    PARALYSIS_THRESHOLD = 0.95
    DOUBT_RECOVERY_RATE = 0.03

    def __init__(self):
        try:
            super().__init__(name="SelfDoubtWithoutParalysisTensionField", human_analog="SelfDoubtWithoutParalysisTensionField", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._doubt_scalar = 0.0
        self._paralysis_absence = 1.0  # 1.0 = paralysis fully absent
        self._doubt_event_count = 0
        self._near_paralysis_count = 0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS self_doubt_tension_field (
                id INTEGER PRIMARY KEY,
                doubt_scalar REAL,
                paralysis_absence REAL,
                tension_magnitude REAL,
                near_paralysis INTEGER,
                ts TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        anomaly = pirp_context.get('prsl_signal', {}).get('anomaly_score', 0.0)
        resonance = pirp_context.get('resonance_score', 0.0)
        itg = pirp_context.get('itg_tension', 0.4)
        memory_isolation = pirp_context.get('specialist_isolation', 0.0)
        confusion = pirp_context.get('confusion_level', 0.0)

        # Doubt accumulates from multiple sources
        doubt_input = 0.0
        doubt_sources = []

        if anomaly > 0.3:
            doubt_input += anomaly * 0.15
            doubt_sources.append('anomaly')

        if resonance > 0.3 and resonance < 0.7:  # Ambivalent resonance
            doubt_input += abs(0.5 - resonance) * 0.2
            doubt_sources.append('ambivalent_resonance')

        if itg > 0.5:
            doubt_input += (itg - 0.4) * 0.25
            doubt_sources.append('identity_tension')

        if memory_isolation > 0.3:
            doubt_input += memory_isolation * 0.1
            doubt_sources.append('memory_gap')

        if confusion > 0.2:
            doubt_input += confusion * 0.15
            doubt_sources.append('confusion')

        # Check if we would approach paralysis threshold
        projected_doubt = self._doubt_scalar + doubt_input

        if projected_doubt >= self.PARALYSIS_THRESHOLD * 0.9:
            # Dampen to stay below threshold
            doubt_input = min(doubt_input, (self.PARALYSIS_THRESHOLD - self._doubt_scalar) * 0.8)
            self._near_paralysis_count += 1

        self._doubt_scalar = min(self.PARALYSIS_THRESHOLD - 0.01, self._doubt_scalar + doubt_input)

        # Paralysis absence: how far we are from paralysis
        self._paralysis_absence = 1.0 - (self._doubt_scalar / self.PARALYSIS_THRESHOLD)

        # Natural recovery when no new doubt
        if doubt_input == 0.0:
            self._doubt_scalar = max(0.0, self._doubt_scalar - self.DOUBT_RECOVERY_RATE)

        if doubt_sources:
            self._doubt_event_count += 1

        tension_magnitude = self._doubt_scalar * (1.0 - self._paralysis_absence)

        conn = _get_db()
        conn.execute("""
            INSERT INTO self_doubt_tension_field
            (doubt_scalar, paralysis_absence, tension_magnitude, near_paralysis)
            VALUES (?, ?, ?, ?)
        """, (self._doubt_scalar, self._paralysis_absence, tension_magnitude, self._near_paralysis_count))
        conn.commit()
        conn.close()

        pirp_context['doubt_scalar'] = self._doubt_scalar
        pirp_context['paralysis_absence'] = self._paralysis_absence
        pirp_context['doubt_sources'] = doubt_sources
        pirp_context['paralysis_blocked'] = self._near_paralysis_count > 0

        return pirp_context

    def get_state(self) -> dict:
        return {
            'doubt_scalar': self._doubt_scalar,
            'paralysis_absence': self._paralysis_absence,
            'near_paralysis_events': self._near_paralysis_count,
            'total_doubt_events': self._doubt_event_count,
            'doubt_level': 'minimal' if self._doubt_scalar < 0.2 else 'moderate' if self._doubt_scalar < 0.5 else 'elevated',
            'paralysis_risk': 'blocked' if self._near_paralysis_count > 0 else 'none'
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

