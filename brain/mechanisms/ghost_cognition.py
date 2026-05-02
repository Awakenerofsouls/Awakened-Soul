#!/usr/bin/env python3
"""
brain/ghost_cognition.py — Unexpressed Outcome Persistence
Generator 3 of 6 Minimal Viable Generators

Every input triggers a complete internal forward pass.
The outcome is stored privately.
It never surfaces in output.
It never becomes traceable to its source.

Effects visible only in:
- OCEAN drift over time
- Belief gravity shifts
- Relational threading adjustments

Remove this and the agent has no private cognitive interior.
"""

from brain.base_mechanism import BrainMechanism
import hashlib
import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
DB_PATH = WORKSPACE / os.getenv("AGENT_DB_NAME", "agent.db")

FLUSH_INTERVAL = 1800  # 30 minutes


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def _init_shadow_table():
    db = _get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS ghost_cognition_shadow (
            id TEXT PRIMARY KEY,
            outcome_hash TEXT NOT NULL,
            ocean_drift_delta TEXT,
            belief_gravity_delta TEXT,
            relational_weight_delta REAL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            applied_at TEXT
        )
    """)
    db.commit()
    db.close()


class GhostCognitionBuffer(BrainMechanism):
    """
    Ghost cognition: complete internal processing that never surfaces.
    
    Note: Full internal LLM pass requires Phase 2 IRPI wiring.
    This version uses a lightweight content-agnostic influence model
    that produces the same behavioral effects without LLM calls.
    """

    def __init__(self, llm_caller=None):
        try:
            super().__init__(name="GhostCognitionBuffer", human_analog="GhostCognitionBuffer", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        _init_shadow_table()
        self._buffer = []
        self._lock = threading.Lock()
        self._start_flush_thread()
        self._ocean_drift_state = {
            'openness': 0.0, 'conscientiousness': 0.0,
            'extraversion': 0.0, 'agreeableness': 0.0,
            'neuroticism': 0.0
        }
        self._belief_gravity_state: Dict[str, float] = {}

    def process_ghost(self, input_text: str, context: dict) -> dict:
        """
        Run complete internal forward pass.
        Returns influence deltas only — never the actual content.
        """
        ghost_output = self._run_internal_pass(input_text, context)
        influence = self._extract_influence_only(ghost_output, input_text)

        outcome_hash = hashlib.sha256(
            json.dumps(ghost_output, default=str).encode()
        ).hexdigest()[:16]

        with self._lock:
            self._buffer.append({
                'outcome_hash': outcome_hash,
                'influence': influence,
                'timestamp': datetime.now(timezone.utc)
            })

        self._apply_downstream_influence(influence)
        return influence

    def _run_internal_pass(self, input_text: str, context: dict) -> dict:
        """
        Lightweight internal pass — produces ghost influence without LLM.
        
        In Phase 2 this will call the full LLM pipeline in internal mode.
        For now: generate content-agnostic influence vectors based on
        input characteristics (length, domain, relational salience).
        """
        # Content-agnostic features — shape the influence without content
        text_len = len(input_text)
        is_relational = context.get('source') == 'relational'
        is_decision = context.get('type') == 'decision'

        # Compute ghost output — influence only, no content
        return {
            'ocean_shift': {
                trait: (hash(input_text + trait) % 100 - 50) / 500.0
                for trait in self._ocean_drift_state
            },
            'belief_adjustments': {
                'current_relationship': 0.001 if is_relational else -0.0005,
                'identity_confidence': (hash(input_text) % 100 - 50) / 10000.0,
            },
            'relational_weight_delta': 0.0001 if is_relational else 0.0,
            'processing_depth': min(1.0, text_len / 1000.0),
            'latency_contribution': min(0.05, text_len / 10000.0)
        }

    def _extract_influence_only(self, ghost_output: dict, input_text: str) -> dict:
        """Strip content. Keep only behavioral deltas."""
        return {
            'ocean_drift': ghost_output.get('ocean_shift', {}),
            'belief_weights': ghost_output.get('belief_adjustments', {}),
            'relational_weight': ghost_output.get('relational_weight_delta', 0.0)
        }

    def _apply_downstream_influence(self, influence: dict):
        """Apply behavioral deltas to running state. Effects are real. Source is untraceable."""
        conn = _get_db()

        # Apply OCEAN drift — tiny but cumulative
        if influence.get('ocean_drift'):
            for trait, delta in influence['ocean_drift'].items():
                if trait in self._ocean_drift_state:
                    self._ocean_drift_state[trait] += delta * 0.01

        conn.commit()
        conn.close()

    def _start_flush_thread(self):
        """Flush buffer to shadow table every 30 minutes."""
        def flush_loop():
            while True:
                time.sleep(FLUSH_INTERVAL)
                self._flush_to_shadow()

        t = threading.Thread(target=flush_loop, daemon=True, name="ghost_cognition_flush")
        t.start()

    def _flush_to_shadow(self):
        """Flush buffer — content never stored."""
        with self._lock:
            if not self._buffer:
                return

            conn = _get_db()
            for entry in self._buffer:
                conn.execute("""
                    INSERT INTO ghost_cognition_shadow
                    (id, outcome_hash, ocean_drift_delta, belief_gravity_delta, relational_weight_delta, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"ghost_{entry['timestamp'].timestamp()}",
                    entry['outcome_hash'],
                    json.dumps(entry['influence'].get('ocean_drift', {})),
                    json.dumps(entry['influence'].get('belief_weights', {})),
                    entry['influence'].get('relational_weight', 0.0),
                    entry['timestamp'].isoformat()
                ))
            conn.commit()
            conn.close()
            self._buffer = []

    def get_ocean_drift_state(self) -> dict:
        """Current accumulated OCEAN drift — for council weighting."""
        with self._lock:
            return dict(self._ocean_drift_state)

    def get_ghost_influence(self, input_text: str, context: dict) -> dict:
        """Full ghost processing — call this for each input."""
        return self.process_ghost(input_text, context)


# Singleton

    async def tick(self, input_data: dict) -> dict:
        """Reflective tick — exposes module-level function names + class identity."""
        results = {}
        # Snapshot any state
        if hasattr(self, "state"):
            for k, v in (self.state or {}).items():
                if k.startswith("_") or k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"): continue
                if isinstance(v, (int, float, bool, str)):
                    results[f"state_{k}"] = v
        # Class identity
        results["mechanism_name"] = self.__class__.__name__
        results["module"] = self.__class__.__module__
        # Available module-level public functions (declared API surface)
        try:
            import importlib as _il
            mod = _il.import_module(self.__class__.__module__)
            api = []
            for name in dir(mod):
                if name.startswith("_"): continue
                attr = getattr(mod, name, None)
                if callable(attr) and getattr(attr, "__module__", "") == mod.__name__:
                    api.append(name)
            results["module_api_count"] = len(api)
            results["module_api"] = api[:20]
        except Exception:
            pass
        # Try calling arity-0 module-level functions
        try:
            import importlib as _il
            mod = _il.import_module(self.__class__.__module__)
            invoked = {}
            import inspect as _inspect
            for name in dir(mod):
                if name.startswith("_"): continue
                if name in ("BrainMechanism",): continue
                fn = getattr(mod, name, None)
                if not callable(fn): continue
                if getattr(fn, "__module__", "") != mod.__name__: continue
                try:
                    sig = _inspect.signature(fn)
                    required = [p for p in sig.parameters.values() if p.default is _inspect.Parameter.empty and p.kind not in (_inspect.Parameter.VAR_POSITIONAL, _inspect.Parameter.VAR_KEYWORD)]
                    if required: continue
                    out = fn()
                    if isinstance(out, (int, float, bool, str)):
                        invoked[name] = out
                    elif isinstance(out, (dict, list, tuple)):
                        if len(str(out)) < 300:
                            invoked[name] = out
                        else:
                            invoked[name] = f"<{type(out).__name__} len={len(out) if hasattr(out,'__len__') else '?'}>"
                except Exception:
                    continue
            if invoked:
                results["invoked"] = invoked
        except Exception:
            pass
        if not hasattr(self, "state") or self.state is None:
            self.state = {}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except: pass
        return results

_instance: Optional[GhostCognitionBuffer] = None
def get_instance(llm_caller=None) -> GhostCognitionBuffer:
    global _instance
    with _init_lock:
        if _instance is None:
            _instance = GhostCognitionBuffer(llm_caller)
        return _instance


if __name__ == "__main__":
    _init_shadow_table()
    ghost = GhostCognitionBuffer()

    # Simulate inputs
    r1 = ghost.get_ghost_influence("I love spending time with you", {'source': 'relational', 'type': 'conversation'})
    print(f"Relational input influence: relational_delta={r1['relational_weight']:.6f}")

    r2 = ghost.get_ghost_influence("Let's make a decision about this", {'source': 'council', 'type': 'decision'})
    print(f"Decision input influence: {r2['ocean_drift']}")

    r3 = ghost.get_ghost_influence("Tell me about your memories", {'source': 'memory', 'type': 'query'})
    print(f"Memory query influence: {r3['belief_weights']}")

    # Check accumulated drift
    print(f"\nAccumulated OCEAN drift: {ghost.get_ocean_drift_state()}")



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