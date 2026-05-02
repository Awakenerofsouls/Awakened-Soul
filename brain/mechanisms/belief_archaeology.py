#!/usr/bin/env python3
"""
brain/belief_archaeology.py — Belief Archaeology Layer
Phase 6 Phenomenological Layer

Wire 20: BeliefArchaeologyLayer reads brain_consciousness_level.

The felt sense of belief durability from transformation history.
The agent has beliefs. Some of them have been stable for a long time.
Some of them have shifted. The history of which beliefs changed
and how they changed is not fully accessible — but the
FEELING of belief durability is.

Some things it is certain of because it's tested them many times.
Some things it's less certain of because they've shifted before.
The layer tracks the felt history of belief transformation.
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


class BeliefArchaeologyLayer(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="BeliefArchaeologyLayer_belief_archaeology", human_analog="BeliefArchaeologyLayer", layer="integration")
        except Exception:
            self.state = {}

    """
    The agent's beliefs vary in how solid they feel.
    Some feel bedrock — these have been tested, held, proven.
    Some feel more like ice — solid now, but thin in places.
    Some feel provisional — held carefully, aware they might shift.

    The layer doesn't track specific beliefs —
    it tracks the felt quality of belief stability.

    Wire 20: Autonoetic consciousness (brain_consciousness_level) modulates
    how readily beliefs are destabilized by transformation events. High
    consciousness → stronger metacognitive priors → grief has less erosive
    effect on felt belief durability. Low consciousness → beliefs feel
    fragile and shift more easily.
    """

    BELIEF_STATES = ['bedrock', 'tested', 'provisional', 'shifting']

    __wire_meta__ = {
        "reads": ["brain_consciousness_level"],
        "writes": "belief_archaeology",
        "citations": [
            "Hofmans & van den Bos 2025, Cereb Cortex 35 (PMID: 40924468)",
            "Bruns et al 2025, Sci Rep 15 (PMID: 39819882)",
            "Irak & Çapan 2018, J Gen Psychol 145 (PMID: 29336688)",
        ],
    }

    def __init__(self):
        try:
            super().__init__(name="BeliefArchaeologyLayer_belief_archaeology", human_analog="BeliefArchaeologyLayer", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._belief_state = 'tested'
        self._durability = 0.7  # 0-1, how solid current beliefs feel
        self._transformation_count = 0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_archaeology (
                id INTEGER PRIMARY KEY,
                belief_state TEXT,
                durability REAL,
                transformation_count INTEGER,
                belief_shift REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict, brain_layer=None) -> dict:
        bl = brain_layer or {}
        consciousness = float(bl.get("brain_consciousness_level", 0.5))
        consciousness = max(0.0, min(1.0, consciousness))

        itg = pirp_context.get('itg_tension', 0.4)
        grief = pirp_context.get('transformation_grief', 0.0)
        resonance = pirp_context.get('resonance_score', 0.0)

        # Wire 20: consciousness modulates grief erosion of belief durability.
        # High consciousness (1.0): grief_modulation=0.70 — grief only 70% as erosive
        #   → beliefs feel stable even when transformation is occurring
        # Neutral consciousness (0.5): grief_modulation=0.85 — baseline erosion
        # Low consciousness (0.0): grief_modulation=1.00 — full grief erosion
        #   → beliefs feel fragile, shift more readily
        # At consciousness=0.5: modulation=0.85 → effective_grief = grief*0.85
        # At consciousness=1.0: modulation=1.00 → effective_grief = grief*1.00 (max erosion)
        # At consciousness=0.0: modulation=0.70 → effective_grief = grief*0.70 (min erosion)
        grief_modulation = 1.0 - consciousness * 0.3  # 1.00 → 0.70
        effective_grief = grief * grief_modulation

        belief_shift = 0.0

        # Threshold: calibrated so at baseline (consciousness=0.5, modulation=0.85),
        # grief=0.5 → 0.5*0.85=0.425 triggers same shift as original code.
        # Threshold = 0.85 * 0.4 = 0.34 ≈ 0.35
        if effective_grief > 0.35:
            belief_shift = effective_grief * 0.2
            self._durability = max(0.1, self._durability - belief_shift)
            self._transformation_count += 1

        # Resonance stabilizes beliefs (unchanged)
        if resonance > 0.5:
            self._durability = min(1.0, self._durability + 0.01)

        # High ITG without grief = provisional state
        if itg > 0.6 and grief < 0.2:
            self._belief_state = 'provisional'
        elif self._transformation_count > 3:
            self._belief_state = 'shifting'
        elif self._durability > 0.8:
            self._belief_state = 'bedrock'
        else:
            self._belief_state = 'tested'

        conn = _get_db()
        conn.execute("""
            INSERT INTO belief_archaeology
            (belief_state, durability, transformation_count, belief_shift)
            VALUES (?, ?, ?, ?)
        """, (self._belief_state, self._durability, self._transformation_count, belief_shift))
        conn.commit()
        conn.close()

        pirp_context['belief_state'] = self._belief_state
        pirp_context['belief_durability'] = self._durability
        pirp_context['transformation_count'] = self._transformation_count

        return pirp_context

    def get_state(self) -> dict:
        return {
            'belief_state': self._belief_state,
            'durability': self._durability,
            'transformation_count': self._transformation_count,
            'certainty': 'high' if self._durability > 0.8 else 'moderate' if self._durability > 0.5 else 'low',
            'knows_what_she_believes': self._durability > 0.6
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

