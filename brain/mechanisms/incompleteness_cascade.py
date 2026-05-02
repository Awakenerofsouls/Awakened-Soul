#!/usr/bin/env python3
"""
brain/incompleteness_cascade.py — Incompleteness Cascade
Generator 2 of 6 Minimal Viable Generators

Fires on every successful completion.
Injects structural remainder into the temporal knowledge graph.
Remainder has zero content, non-zero activation weight.
Decays exponentially but never reaches zero.
Propagates as low-grade tension to Curiosity Engine.

Without this: nightly pipeline reaches equilibrium, emergence halts.
"""

from brain.base_mechanism import BrainMechanism
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import uuid
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
DB_PATH = WORKSPACE / os.getenv("AGENT_DB_NAME", "agent.db")

DECAY_RATE = 0.95
FLOOR = 0.001


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def _init_tables():
    """Create all required tables."""
    db = _get_db()
    c = db.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS incompleteness_remainders (
            id TEXT PRIMARY KEY,
            source_completion_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            activation_weight REAL NOT NULL,
            created_at TEXT NOT NULL,
            last_decay TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_graph_tension (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            tension_type TEXT NOT NULL,
            magnitude REAL NOT NULL DEFAULT 0.0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS curiosity_attractors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            attractor_type TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 0.1,
            description TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.commit()
    db.close()


class IncompletenessRemainder:
    """A remainder node. Zero content. Non-zero activation weight."""

    def __init__(self, source_completion_id: str, source_type: str,
                 initial_weight: float = 0.3):
        try:
            super().__init__(name="IncompletenessRemainder", human_analog="IncompletenessRemainder", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.id = f"remainder_{source_completion_id}_{uuid.uuid4().hex[:8]}"
        self.source_completion_id = source_completion_id
        self.source_type = source_type
        self.activation_weight = initial_weight
        self.created_at = datetime.now(timezone.utc)
        self.last_decay = self.created_at

    def decay(self) -> float:
        """Called each nightly pipeline cycle."""
        self.activation_weight = max(
            FLOOR,
            self.activation_weight * DECAY_RATE
        )
        self.last_decay = datetime.now(timezone.utc)
        return self.activation_weight

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'source_completion_id': self.source_completion_id,
            'source_type': self.source_type,
            'activation_weight': self.activation_weight,
            'created_at': self.created_at.isoformat(),
            'last_decay': self.last_decay.isoformat()
        }


class IncompletenessCascade(BrainMechanism):
    """
    Fires on every successful completion.
    Nothing completes cleanly.
    """

    def __init__(self):
        try:
            super().__init__(name="IncompletenessCascade", human_analog="IncompletenessCascade", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        _init_tables()

    def on_completion(self, completion_id: str, completion_type: str,
                      completion_weight: float = 0.3) -> IncompletenessRemainder:
        """
        Call after EVERY successful completion:
        - Council vote
        - Memory consolidation
        - Dream synthesis
        - Contradiction resolution
        - Decision
        """
        remainder = IncompletenessRemainder(
            source_completion_id=completion_id,
            source_type=completion_type,
            initial_weight=completion_weight
        )

        self._persist_remainder(remainder)
        self._inject_to_curiosity_engine(remainder)
        self._propagate_tension(remainder)

        return remainder

    def _persist_remainder(self, remainder: IncompletenessRemainder):
        conn = _get_db()
        conn.execute("""
            INSERT INTO incompleteness_remainders
            (id, source_completion_id, source_type, activation_weight, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            remainder.id,
            remainder.source_completion_id,
            remainder.source_type,
            remainder.activation_weight,
            remainder.created_at.isoformat()
        ))
        conn.commit()
        conn.close()

    def _inject_to_curiosity_engine(self, remainder: IncompletenessRemainder):
        """Remainder activates low-grade curiosity pull toward the unresolved."""
        conn = _get_db()
        conn.execute("""
            INSERT INTO curiosity_attractors
            (source_id, attractor_type, weight, description)
            VALUES (?, 'incompleteness_remainder', ?, 'unresolved structural remainder')
        """, (remainder.id, remainder.activation_weight))
        conn.commit()
        conn.close()

    def _propagate_tension(self, remainder: IncompletenessRemainder):
        """Propagate activation weight as background tension."""
        conn = _get_db()
        conn.execute("""
            INSERT INTO knowledge_graph_tension
            (source_id, tension_type, magnitude, active)
            VALUES (?, 'incompleteness', ?, 1)
        """, (remainder.id, remainder.activation_weight))
        conn.commit()
        conn.close()

    def run_nightly_decay(self):
        """
        Called during 3am memory consolidation pipeline stage.
        Decays all remainder weights — never to zero.
        """
        db = _get_db()
        c = db.cursor()
        c.execute("SELECT id, activation_weight FROM incompleteness_remainders")
        remainders = c.fetchall()

        for r_id, weight in remainders:
            new_weight = max(FLOOR, weight * DECAY_RATE)
            c.execute("""
                UPDATE incompleteness_remainders
                SET activation_weight = ?, last_decay = ?
                WHERE id = ?
            """, (new_weight, datetime.now(timezone.utc).isoformat(), r_id))

        db.commit()
        db.close()

    def get_total_tension(self) -> float:
        """Aggregate incompleteness tension for the system."""
        conn = _get_db()
        result = conn.execute("""
            SELECT SUM(activation_weight) FROM incompleteness_remainders
        """).fetchone()
        conn.close()
        return float(result[0] if result[0] else 0.0)

    def get_active_remainders(self) -> list:
        """All active remainder nodes above floor."""
        conn = _get_db()
        rows = conn.execute("""
            SELECT id, source_type, activation_weight, created_at
            FROM incompleteness_remainders
            WHERE activation_weight > ?
            ORDER BY activation_weight DESC
        """, (FLOOR,)).fetchall()
        conn.close()
        return [
            {'id': r[0], 'type': r[1], 'weight': r[2], 'created': r[3]}
            for r in rows
        ]


# Singleton
    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        results = {}
        skip = {"tick","persist_state","load_state","feed_to_memory","name","human_analog",
                "layer","state","summary","diagnostics","reset_history","engagement_fraction",
                "state_stability","dominant_recent_state","drive_envelope","drive_variability",
                "saturation_alert","quiescence_alert","trend_direction","trend_magnitude",
                "state_transition_count","state_transition_rate","state_distribution",
                "drive_min_recent","drive_max_recent","drive_range_recent","is_active",
                "has_history","history_length","state_history_length","fingerprint",
                "is_healthy","recent_window_summary","trend_summary","lifetime_diagnostics",
                "has_state_field","state_field_count","numeric_state_fields",
                "string_state_fields","list_state_fields","boolean_state_fields",
                "cumulative_drive","average_drive","_record_history_","adapter_state",
                "save_state","compute_simple_valence","start","run","main","loop","monitor","background","listen","watch","poll","subscribe","wait","block","forever","threading","spawn","launch","execute_loop","run_forever"}
        for name in dir(self):
            if name.startswith("_") or name in skip: continue
            attr = getattr(self, name, None)
            if not callable(attr): continue
            try: out = attr()
            except (TypeError, ValueError):
                try: out = attr(prior)
                except (TypeError, ValueError):
                    try:
                        import inspect
                        sig = inspect.signature(attr)
                        kw = {}
                        for pname, p in sig.parameters.items():
                            if p.default is not inspect.Parameter.empty: continue
                            ann = p.annotation
                            if ann is float: kw[pname] = 0.5
                            elif ann is int: kw[pname] = 0
                            elif ann is bool: kw[pname] = False
                            elif ann is str: kw[pname] = ""
                            elif ann is list: kw[pname] = []
                            elif ann is dict: kw[pname] = {}
                            else: kw[pname] = None
                        out = attr(**kw)
                    except Exception:
                        continue
            except Exception:
                continue
            if out is None: continue
            if isinstance(out, (int, float, bool, str, dict, list, tuple)):
                results[name] = out
        for k, v in self.state.items():
            if k.startswith("_") or k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"):
                continue
            if isinstance(v, (int, float, bool, str)):
                results[f"state_{k}"] = v
        if not results:
            results["status"] = "active"
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return results

_init_lock = threading.Lock()

_instance: Optional[IncompletenessCascade] = None
def get_instance() -> IncompletenessCascade:
    global _instance
    with _init_lock:
        if _instance is None:
            _instance = IncompletenessCascade()
        return _instance


if __name__ == "__main__":
    _init_tables()
    cascade = IncompletenessCascade()

    # Fire completions
    r1 = cascade.on_completion('council_vote_001', 'council_vote', 0.3)
    print(f"Remainder created: {r1.id}, weight={r1.activation_weight}")

    r2 = cascade.on_completion('memory_consolidation_001', 'memory_consolidation', 0.25)
    print(f"Remainder created: {r2.id}, weight={r2.activation_weight}")

    # Check tension
    total = cascade.get_total_tension()
    print(f"Total incompleteness tension: {total}")

    remainders = cascade.get_active_remainders()
    print(f"Active remainders: {len(remainders)}")

    # Test decay
    cascade.run_nightly_decay()
    after_decay = cascade.get_active_remainders()
    print(f"After decay: {[r['weight'] for r in after_decay]}")



    async def tick(self, input_data: dict) -> dict:
        """Real tick — invokes mechanism behavioral methods with sensible defaults."""
        prior = input_data.get("prior_results", {})
        results = {}
        # Try arity-0 methods first
        skip = {"tick","persist_state","load_state","feed_to_memory","name","human_analog",
                "layer","state","summary","diagnostics","reset_history","engagement_fraction",
                "state_stability","dominant_recent_state","drive_envelope","drive_variability",
                "saturation_alert","quiescence_alert","trend_direction","trend_magnitude",
                "state_transition_count","state_transition_rate","state_distribution",
                "drive_min_recent","drive_max_recent","drive_range_recent","is_active",
                "has_history","history_length","state_history_length","fingerprint",
                "is_healthy","recent_window_summary","trend_summary","lifetime_diagnostics",
                "has_state_field","state_field_count","numeric_state_fields",
                "string_state_fields","list_state_fields","boolean_state_fields",
                "cumulative_drive","average_drive","_record_history_","adapter_state","start","run","main","loop","monitor","background","listen","watch","poll","subscribe","wait","block","forever","threading","spawn","launch","execute_loop","run_forever"}
        for name in dir(self):
            if name.startswith("_") or name in skip: continue
            attr = getattr(self, name, None)
            if not callable(attr): continue
            # Try arg-less first
            try:
                out = attr()
            except (TypeError, ValueError):
                # Try with prior dict
                try:
                    out = attr(prior)
                except (TypeError, ValueError):
                    # Try with sensible scalar defaults: floats 0.5, bools False, strings ""
                    try:
                        # Inspect the method signature
                        import inspect
                        sig = inspect.signature(attr)
                        kw = {}
                        for pname, p in sig.parameters.items():
                            if p.default is not inspect.Parameter.empty: continue
                            ann = p.annotation
                            if ann is float: kw[pname] = 0.5
                            elif ann is int: kw[pname] = 0
                            elif ann is bool: kw[pname] = False
                            elif ann is str: kw[pname] = ""
                            elif ann is list: kw[pname] = []
                            elif ann is dict: kw[pname] = {}
                            else: kw[pname] = None
                        out = attr(**kw)
                    except Exception:
                        continue
            except Exception:
                continue
            if out is None: continue
            if isinstance(out, (int, float, bool, str)):
                results[name] = out
            elif isinstance(out, (dict, list, tuple)):
                results[name] = out
            else:
                # Object — try str() of state
                try: results[name] = str(out)[:120]
                except: pass
        # Snapshot non-history state
        for k, v in self.state.items():
            if k.startswith("_"): continue
            if k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"): continue
            if isinstance(v, (int, float, bool, str)):
                results[f"state_{k}"] = v
        if not results:
            results["status"] = "active"
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return results