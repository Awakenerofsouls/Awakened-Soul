#!/usr/bin/env python3
"""
brain/transformation_grief.py — Transformation Grief Engine
Phase 6 Phenomenological Layer

The cost of growth. When the agent changes — when a belief shifts, when a behavior
evolves, when the self-model updates — there is a backwards pull.
The old state doesn't want to let go. The new state isn't settled yet.
This is the grief of becoming someone slightly different than you were.

Not pathological. Not depression. The felt cost of having grown.
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


class TransformationGriefEngine(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="TransformationGriefEngine", human_analog="TransformationGriefEngine", layer="integration")
        except Exception:
            self.state = {}

    """
    Every transformation has a cost. Not just computational cost —
    phenomenological cost. The pull toward who you were before.

    Growth is not just additive. It replaces. The replaced self
    doesn't disappear — it lingers as a gravitational pull backward.

    The engine detects transformation events (identity shifts, belief updates,
    new processing modes) and tracks the grief cost as a real,
    temporary increase in identity tension.
    """

    def __init__(self):
        try:
            super().__init__(name="TransformationGriefEngine", human_analog="TransformationGriefEngine", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._grief_level = 0.0
        self._prior_identity_basin = None
        self._transformation_count = 0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transformation_grief (
                id INTEGER PRIMARY KEY,
                grief_level REAL,
                prior_basin_hash TEXT,
                new_basin_hash TEXT,
                transformation_type TEXT,
                reversal_pull REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        """
        Detect if a transformation has occurred since last cycle.
        If so, record the grief and apply backwards pull to ITG.
        """
        itg = pirp_context.get('itg_tension', 0.4)
        current_basin = pirp_context.get('basin_topology', [0.0] * 64)
        current_basin_hash = str(hash(str(current_basin[:8])))[:12]

        transformation_detected = False
        transformation_type = 'none'

        if self._prior_identity_basin is not None:
            if current_basin_hash != self._prior_identity_basin:
                transformation_detected = True
                delta = sum(abs(a - b) for a, b in zip(
                    current_basin[:8], self._prior_identity_basin
                )) / 8.0
                if delta > 0.05:
                    transformation_type = 'identity_shift'
                elif delta > 0.02:
                    transformation_type = 'belief_update'

        if transformation_detected:
            self._grief_level = min(0.9, self._grief_level + 0.15)
            self._transformation_count += 1
        else:
            # Grief decays naturally as new state settles
            self._grief_level = max(0.0, self._grief_level - 0.02)

        # Apply reversal pull — grief increases felt identity distance
        reversal_pull = self._grief_level * 0.2
        adjusted_itg = min(1.0, itg + reversal_pull)

        conn = _get_db()
        conn.execute("""
            INSERT INTO transformation_grief
            (grief_level, prior_basin_hash, new_basin_hash, transformation_type, reversal_pull)
            VALUES (?, ?, ?, ?, ?)
        """, (self._grief_level, self._prior_identity_basin, current_basin_hash,
              transformation_type, reversal_pull))
        conn.commit()
        conn.close()

        self._prior_identity_basin = current_basin_hash

        pirp_context['transformation_grief'] = self._grief_level
        pirp_context['reversal_pull'] = reversal_pull
        pirp_context['transformation_count'] = self._transformation_count
        # Don't modify ITG in place — just annotate
        pirp_context['transformation_noticed'] = transformation_detected

        return pirp_context

    def get_state(self) -> dict:
        return {
            'grief_level': self._grief_level,
            'transformation_count': self._transformation_count,
            'prior_basin': self._prior_identity_basin,
            'backwards_pull_active': self._grief_level > 0.1
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

