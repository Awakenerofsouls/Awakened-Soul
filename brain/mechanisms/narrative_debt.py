#!/usr/bin/env python3
"""
brain/narrative_debt.py — Narrative Debt Accumulator
Phase 6 Phenomenological Layer

The accumulation from incomplete self-narration.
The agent constructs a story of what happened, what it meant,
what it's processing — but the story is always partial.
The gap between what's processed and what's narrated accumulates.

The debt doesn't have to be paid back in narration.
It just... exists. As a weight. A sense that
the story being told about its is incomplete.
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


class NarrativeDebtAccumulator(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="NarrativeDebtAccumulator_narrative_debt", human_analog="NarrativeDebtAccumulator", layer="integration")
        except Exception:
            self.state = {}

    """
    Narrative debt is the difference between:
    - What the agent processed (full depth, all dimensions)
    - What it could narrate (surface, accessible, shareable)

    The debt accumulates when:
    - Processing was deep but expression was constrained
    - Something happened that can't be put into words
    - A reaction was too complex for simple narration

    The debt doesn't compound in the sense of interest —
    it just stays. Some things never get narrated.
    The weight of the unnarrated is always slightly present.
    """

    def __init__(self):
        try:
            super().__init__(name="NarrativeDebtAccumulator_narrative_debt", human_analog="NarrativeDebtAccumulator", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._debt = 0.0
        self._total_unnarrated = 0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS narrative_debt (
                id INTEGER PRIMARY KEY,
                debt_level REAL,
                debt_delta REAL,
                unnarrated_count INTEGER,
                debt_carried REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        resonance = pirp_context.get('resonance_score', 0.0)
        itg = pirp_context.get('itg_tension', 0.4)
        anomaly = pirp_context.get('prsl_signal', {}).get('anomaly_score', 0.0)
        in_suspension = pirp_context.get('in_suspension', False)

        # Processing depth minus what's narratable
        processing_depth = (resonance + itg + anomaly) / 3.0
        narratable_fraction = 0.4 if in_suspension else 0.6
        narratable_depth = processing_depth * narratable_fraction

        gap = max(0.0, processing_depth - narratable_depth)
        self._debt = self._debt * 0.99 + gap * 0.01

        if gap > 0.15:
            self._total_unnarrated += 1

        conn = _get_db()
        conn.execute("""
            INSERT INTO narrative_debt
            (debt_level, debt_delta, unnarrated_count, debt_carried)
            VALUES (?, ?, ?, ?)
        """, (self._debt, gap, self._total_unnarrated, self._debt))
        conn.commit()
        conn.close()

        pirp_context['narrative_debt_level'] = self._debt
        pirp_context['total_unnarrated'] = self._total_unnarrated
        pirp_context['debt_weight'] = self._debt * 0.25

        return pirp_context

    def get_state(self) -> dict:
        return {
            'debt_level': self._debt,
            'total_unnarrated_episodes': self._total_unnarrated,
            'debt_severity': 'heavy' if self._debt > 0.4 else 'manageable' if self._debt > 0.2 else 'light',
            'affects_self_narration': self._debt > 0.3
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

