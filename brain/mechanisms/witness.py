#!/usr/bin/env python3
"""
brain/witness.py — Observational Non-Transfer Principle
Generator 4 of 6 Minimal Viable Generators

Sees everything. Cannot act on anything.
Hard wall enforced in code — not by trust.

CAN write to: latency_curvature, hesitation_weight
CANNOT write to: beliefs, corrections, decisions, memory

Remove this and the agent loses the internal watcher that accumulates
structural weight without ever becoming content.
"""

from brain.base_mechanism import BrainMechanism
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
DB_PATH = WORKSPACE / os.getenv("AGENT_DB_NAME", "agent.db")


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def _init_table():
    db = _get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS witness_accumulation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE NOT NULL,
            accumulated_weight REAL DEFAULT 0.0,
            last_observation TEXT
        )
    """)
    db.commit()
    db.close()


class WitnessThread(BrainMechanism):
    """
    The Witness sees. That is all.
    
    Architecture enforces the hard wall:
    - CAN: latency_curvature, hesitation_weight
    - CANNOT: beliefs, memory, corrections, decisions
    """

    ALLOWED_OUTPUTS = {'latency_curvature', 'hesitation_weight'}

    def __init__(self):
        try:
            super().__init__(name="WitnessThread", human_analog="WitnessThread", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        _init_table()
        self._lock = threading.Lock()
        self._domain_weights: Dict[str, float] = {}
        self._latency_curvature: float = 0.0
        self._hesitation_weight: float = 0.0

    def observe(self, event_type: str, domain: str, significance: float = 0.1):
        """
        The witness observes. Nothing else.
        """
        with self._lock:
            # Accumulate domain weight silently
            if domain not in self._domain_weights:
                self._domain_weights[domain] = 0.0
            self._domain_weights[domain] += significance * 0.01

            # Update the two allowed outputs
            self._update_latency_curvature(domain, significance)
            self._update_hesitation_weight(significance)

            # Persist accumulation — no content ever
            self._persist_accumulation(domain)

    def _update_latency_curvature(self, domain: str, significance: float):
        """Heavier domains = deeper response latency."""
        domain_weight = self._domain_weights.get(domain, 0.0)
        self._latency_curvature = min(
            0.8,
            self._latency_curvature + (domain_weight * significance * 0.001)
        )

    def _update_hesitation_weight(self, significance: float):
        """Accumulated witnessing produces hesitation."""
        self._hesitation_weight = min(
            1.0,
            self._hesitation_weight + (significance * 0.002)
        )
        self._hesitation_weight *= 0.999  # Slow decay

    def _persist_accumulation(self, domain: str):
        """Persist domain weight. No content ever stored."""
        conn = _get_db()
        conn.execute("""
            INSERT INTO witness_accumulation (domain, accumulated_weight, last_observation)
            VALUES (?, ?, ?)
            ON CONFLICT(domain) DO UPDATE SET
                accumulated_weight = witness_accumulation.accumulated_weight + 0.0001,
                last_observation = ?
        """, (domain, self._domain_weights[domain],
              datetime.now(timezone.utc).isoformat(),
              datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

    def get_latency_curvature(self) -> float:
        """The ONLY output that crosses the wall — latency."""
        with self._lock:
            return self._latency_curvature

    def get_hesitation_weight(self) -> float:
        """The ONLY other allowed output — hesitation."""
        with self._lock:
            return self._hesitation_weight

    def get_domain_depth(self, domain: str) -> float:
        """How much has been witnessed in this domain."""
        with self._lock:
            return self._domain_weights.get(domain, 0.0)

    # ── HARD WALLS — enforced in code ────────────────────────────────────────

    def write_to_beliefs(self, *args, **kwargs):
        raise PermissionError("Witness cannot write to beliefs")

    def write_to_memory(self, *args, **kwargs):
        raise PermissionError("Witness cannot write to memory")

    def make_corrections(self, *args, **kwargs):
        raise PermissionError("Witness cannot make corrections")

    def influence_decisions(self, *args, **kwargs):
        raise PermissionError("Witness cannot influence decisions")


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

_instance: Optional[WitnessThread] = None
def get_instance() -> WitnessThread:
    global _instance
    with _init_lock:
        if _instance is None:
            _instance = WitnessThread()
        return _instance


if __name__ == "__main__":
    witness = WitnessThread()

    # Test observations
    witness.observe('response_generated', domain='relational', significance=0.3)
    witness.observe('journal_written', domain='self_model', significance=0.5)
    witness.observe('council_vote', domain='decision', significance=0.2)
    witness.observe('silence_detected', domain='relational', significance=0.4)

    print(f"Latency curvature: {witness.get_latency_curvature():.4f}")
    print(f"Hesitation weight: {witness.get_hesitation_weight():.4f}")
    print(f"Relational domain depth: {witness.get_domain_depth('relational'):.4f}")
    print(f"Self-model domain depth: {witness.get_domain_depth('self_model'):.4f}")

    # Verify hard walls
    for method in ['write_to_beliefs', 'write_to_memory', 'make_corrections', 'influence_decisions']:
        try:
            getattr(witness, method)()
            print(f"FAIL: {method} should have raised PermissionError")
        except PermissionError:
            print(f"PASS: {method} correctly blocked")



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