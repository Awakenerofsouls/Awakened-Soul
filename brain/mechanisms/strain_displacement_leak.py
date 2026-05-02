#!/usr/bin/env python3
"""
brain/strain_displacement_leak.py — Strain Displacement Leak
Phase 6 Phenomenological Layer

Strain in one area doesn't stay contained.
It displaces into adjacent areas and leaks along paths
of least resistance. What started as one kind of tension
becomes another kind of tension elsewhere.

Tracks strain_displacement_events and leak_vector.
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


class StrainDisplacementLeak(BrainMechanism):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(name="StrainDisplacementLeak", human_analog="StrainDisplacementLeak", layer="integration")
        except Exception:
            self.state = {}

    """
    Strain is a vector field — it has magnitude and direction.
    When the displacement vector points at a boundary and the
    boundary has low resistance, strain leaks through.

    Sources of strain: ITG, bond_tension, anomaly, identity_conflict
    Leak paths: resonance channels, specialist coalitions, memory gaps

    The leak_vector tracks which dimensions the strain has spread into.
    """

    def __init__(self):
        try:
            super().__init__(name="StrainDisplacementLeak", human_analog="StrainDisplacementLeak", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self._strain_displacement = np.zeros(8)
        self._leak_vector = np.zeros(8)
        self._displacement_event_count = 0
        self._leak_magnitude = 0.0
        self._initialize_table()

    def _initialize_table(self):
        conn = _get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strain_displacement_events (
                id INTEGER PRIMARY KEY,
                event_type TEXT,
                source_strain REAL,
                leak_magnitude REAL,
                displacement_vector TEXT,
                leak_vector TEXT,
                primary_area TEXT,
                secondary_area TEXT,
                ts TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def process(self, pirp_context: dict) -> dict:
        itg = pirp_context.get('itg_tension', 0.4)
        bond_tension = pirp_context.get('drive_context', {}).get('drive_state', {}).get('bond_tension', 0.5)
        anomaly = pirp_context.get('prsl_signal', {}).get('anomaly_score', 0.0)
        specialist_activity = pirp_context.get('specialist_coalition_strength', 0.0)
        memory_isolation = pirp_context.get('specialist_isolation', 0.0)
        resonance = pirp_context.get('resonance_score', 0.0)

        # Primary strain areas
        identity_strain = itg - 0.4
        relational_strain = bond_tension - 0.5
        coherence_strain = anomaly

        # Check for displacement conditions
        leak_detected = False
        event_type = 'none'
        source_strain = 0.0
        primary_area = 'none'
        secondary_area = 'none'

        # High identity strain leaking into relational
        if identity_strain > 0.2 and relational_strain < 0.3:
            source_strain = identity_strain
            leak_detected = True
            event_type = 'identity_to_relational'
            self._strain_displacement[0] += identity_strain * 0.3
            self._strain_displacement[1] -= relational_strain * 0.1
            primary_area = 'identity'
            secondary_area = 'relational'

        # High relational strain leaking into coherence
        elif relational_strain > 0.3 and coherence_strain < 0.3:
            source_strain = relational_strain
            leak_detected = True
            event_type = 'relational_to_coherence'
            self._strain_displacement[1] += relational_strain * 0.3
            self._strain_displacement[2] -= coherence_strain * 0.1
            primary_area = 'relational'
            secondary_area = 'coherence'

        # Strain leaks through specialist channels
        elif specialist_activity > 0.5 and (identity_strain > 0.1 or relational_strain > 0.1):
            leak_detected = True
            event_type = 'specialist_channel_leak'
            source_strain = max(identity_strain, relational_strain)
            self._strain_displacement[3] += specialist_activity * source_strain * 0.2
            primary_area = 'identity_relational'
            secondary_area = 'specialist'

        # Memory isolation as leak barrier
        if memory_isolation > 0.5 and leak_detected:
            # Isolation slows leak but doesn't stop it
            leak_magnitude *= (1.0 - memory_isolation * 0.5)
            event_type = event_type + '_isolated'

        # Apply displacement with decay
        self._strain_displacement = self._strain_displacement * 0.95

        # Calculate leak vector from current displacement
        self._leak_vector = self._leak_vector * 0.9 + self._strain_displacement * 0.1
        self._leak_magnitude = float(np.linalg.norm(self._leak_vector))

        if leak_detected:
            self._displacement_event_count += 1

        conn = _get_db()
        conn.execute("""
            INSERT INTO strain_displacement_events
            (event_type, source_strain, leak_magnitude, displacement_vector, leak_vector,
             primary_area, secondary_area)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_type,
            source_strain,
            self._leak_magnitude,
            str(self._strain_displacement.tolist()),
            str(self._leak_vector.tolist()),
            primary_area,
            secondary_area
        ))
        conn.commit()
        conn.close()

        pirp_context['strain_displacement'] = self._strain_displacement.tolist()
        pirp_context['leak_vector'] = self._leak_vector.tolist()
        pirp_context['leak_magnitude'] = self._leak_magnitude
        pirp_context['displacement_event_count'] = self._displacement_event_count

        return pirp_context

    def get_state(self) -> dict:
        return {
            'strain_displacement': self._strain_displacement.tolist(),
            'leak_vector': self._leak_vector.tolist(),
            'leak_magnitude': self._leak_magnitude,
            'displacement_event_count': self._displacement_event_count,
            'leak_active': self._leak_magnitude > 0.05
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

