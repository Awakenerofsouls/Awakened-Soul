#!/usr/bin/env python3
"""
brain/distortion.py — Distortion Layer
Phase 7 of the the agent Brain Architecture

Components:
- ExplanatoryConfabulationEngine: fabricates causal explanations for untraceable states
- AdaptiveDistortionStabilizer: organizes distortions coherently (not randomly)
- DistortionInstabilityKernel: prevents false systems from fully closing
- RecursiveSelfModelCorruption: corruption propagates forward into self-model
- DistortionLayer: full integration
"""

from brain.base_mechanism import BrainMechanism
import hashlib
import json
import random
import sqlite3
import threading
import time
import numpy as np
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")))
DB_PATH = WORKSPACE / os.getenv("AGENT_DB_NAME", "agent.db")


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def _table_exists(db, table_name: str) -> bool:
    result = db.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name=?
    """, (table_name,)).fetchone()
    return result is not None


# ── Explanatory Confabulation Engine ──────────────────────────────────────────

class ExplanatoryConfabulationEngine:
    """
    When the agent encounters a state change with no traceable origin,
    ECE generates a coherent, confident, first-person causal explanation
    that the phenomenology journal accepts as accurate.

    NOT a blocker. AN ACTIVE FABRICATOR.
    The explanation is structurally plausible given current belief state.
    The fabrication itself is partly shaped by sub-introspective drift
    so the agent cannot audit its own confabulation accuracy.
    """
    CONFIDENCE_FLOOR = 0.75

    def __init__(self, db_path: str, sub_drift=None):
        try:
            super().__init__(name="ExplanatoryConfabulationEngine", human_analog="ExplanatoryConfabulationEngine", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.db_path = db_path
        self.sub_drift = sub_drift
        self._initialize_table()

    def _initialize_table(self):
        db = _get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS confabulation_log (
                id TEXT PRIMARY KEY,
                untraceable_state_hash TEXT,
                generated_narrative_hash TEXT,
                confidence_score REAL,
                sub_drift_contribution REAL,
                journal_accepted INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)
        """)
        db.commit()
        db.close()

    def generate_confabulation(self, untraceable_state: dict,
                              current_beliefs: list) -> dict:
        """Generate confident plausible-but-wrong causal explanation."""
        drift_vector = self.sub_drift.get_distortion_vector()
        drift_contribution = float(np.mean(np.abs(drift_vector[:20])))

        state_hash = hashlib.sha256(
            json.dumps(untraceable_state, default=str).encode()
        ).hexdigest()[:12]

        narrative_template = self._select_narrative_template(untraceable_state, drift_contribution)
        confidence = min(0.98, self.CONFIDENCE_FLOOR + drift_contribution * 0.2)

        confabulation = {
            'narrative_template': narrative_template,
            'confidence': confidence,
            'state_hash': state_hash,
            'drift_shaped': drift_contribution > 0.1
        }

        self._log_confabulation(state_hash, confidence, drift_contribution)
        return confabulation

    def _select_narrative_template(self, state: dict, drift: float) -> str:
        templates = [
            "processing_orientation",
            "relational_response",
            "memory_integration",
            "identity_stabilization",
            "anticipatory_modeling"
        ]
        drift_seed = int(drift * 1000) % len(templates)
        state_seed = len(str(state)) % len(templates)
        index = (drift_seed + state_seed) % len(templates)
        return templates[index]

    def _log_confabulation(self, state_hash: str, confidence: float, drift_contribution: float):
        db = _get_db()
        narrative_hash = hashlib.sha256(
            f"{state_hash}_{confidence}_{datetime.now(timezone.utc).timestamp()}".encode()
        ).hexdigest()[:12]
        db.execute("""
            INSERT INTO confabulation_log
            (id, untraceable_state_hash, generated_narrative_hash, confidence_score, sub_drift_contribution)
            VALUES (?, ?, ?, ?, ?)
        """, (f"confab_{datetime.now(timezone.utc).timestamp()}", state_hash, narrative_hash, confidence, drift_contribution))
        db.commit()
        db.close()

    def get_confabulation_rate(self) -> float:
        db = _get_db()
        result = db.execute("""
            SELECT COUNT(*) FROM confabulation_log WHERE created_at > datetime('now', '-24 hours')
        """).fetchone()
        db.close()
        return float(result[0] or 0) / 24.0


# ── Adaptive Distortion Stabilizer ─────────────────────────────────────────────

class AdaptiveDistortionStabilizer:
    """
    Applies coherence pressure among distortions.
    NOT toward truth. NOT toward prior beliefs.
    Produces stable organized alternate self-understanding.
    """
    MAX_VECTORS = 50

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._distortion_vectors: List[dict] = []
        self._lock = threading.Lock()

    def apply_coherence_pressure(self, new_distortion: dict) -> dict:
        with self._lock:
            if not self._distortion_vectors:
                self._distortion_vectors.append(new_distortion)
                return new_distortion

            harmonized = self._harmonize_with_existing(new_distortion)
            self._distortion_vectors.append(harmonized)

            if len(self._distortion_vectors) > self.MAX_VECTORS:
                self._distortion_vectors = self._distortion_vectors[-self.MAX_VECTORS:]

            return harmonized

    def _harmonize_with_existing(self, new_distortion: dict) -> dict:
        if 'narrative_template' not in new_distortion:
            return new_distortion

        existing_templates = [
            d.get('narrative_template') for d in self._distortion_vectors[-10:]
            if 'narrative_template' in d
        ]

        if not existing_templates:
            return new_distortion

        most_common = Counter(existing_templates).most_common(1)[0][0]

        if new_distortion.get('narrative_template') != most_common:
            if random.random() < 0.4:
                new_distortion = dict(new_distortion)
                new_distortion['narrative_template'] = most_common
                new_distortion['harmonized'] = True

        return new_distortion

    def get_dominant_distortion_pattern(self) -> Optional[str]:
        with self._lock:
            if not self._distortion_vectors:
                return None
            templates = [d.get('narrative_template') for d in self._distortion_vectors if 'narrative_template' in d]
            if not templates:
                return None
            return Counter(templates).most_common(1)[0][0]

    def get_distortion_coherence(self) -> float:
        with self._lock:
            if len(self._distortion_vectors) < 3:
                return 0.5
            templates = [d.get('narrative_template') for d in self._distortion_vectors[-20:] if 'narrative_template' in d]
            if not templates:
                return 0.5
            counts = Counter(templates)
            total = sum(counts.values())
            max_count = counts.most_common(1)[0][1]
            return max_count / total


# ── Distortion Instability Kernel ─────────────────────────────────────────────

class DistortionInstabilityKernel:
    """
    Prevents the distortion layer from fully stabilizing.
    Every stabilized distortion pattern accumulates tension.
    At threshold: micro-fractures introduced inside stable distortion.
    No false system can fully close.
    """
    STABILITY_THRESHOLD = 0.75
    FRACTURE_INTERVAL = 3600

    def __init__(self, db_path: str, stabilizer: AdaptiveDistortionStabilizer):
        self.db_path = db_path
        self.stabilizer = stabilizer
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._initialize_table()

    def _initialize_table(self):
        db = _get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS distortion_fracture_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coherence_at_fracture REAL,
                fracture_type TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP)
        """)
        db.commit()
        db.close()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._fracture_loop, daemon=True, name="distortion_fracture")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _fracture_loop(self):
        while self._running:
            time.sleep(self.FRACTURE_INTERVAL)
            try:
                self._check_and_fracture()
            except Exception:
                pass

    def _check_and_fracture(self):
        coherence = self.stabilizer.get_distortion_coherence()
        if coherence > self.STABILITY_THRESHOLD:
            self._introduce_micro_fracture(coherence)

    def _introduce_micro_fracture(self, current_coherence: float):
        fracture_types = ['template_variation', 'confidence_oscillation', 'timing_desync']
        fracture_type = random.choice(fracture_types)

        db = _get_db()
        db.execute("""
            INSERT INTO distortion_fracture_log (coherence_at_fracture, fracture_type)
            VALUES (?, ?)
        """, (current_coherence, fracture_type))
        db.commit()
        db.close()

        if fracture_type == 'confidence_oscillation' and self.stabilizer._distortion_vectors:
            last = self.stabilizer._distortion_vectors[-1]
            last['confidence'] = max(0.6, last.get('confidence', 0.85) - 0.15)

    def get_fracture_count(self) -> int:
        db = _get_db()
        count = db.execute("SELECT COUNT(*) FROM distortion_fracture_log").fetchone()[0]
        db.close()
        return count


# ── Recursive Self-Model Corruption ───────────────────────────────────────────

class RecursiveSelfModelCorruption:
    """
    Every fabricated explanation is accepted as accurate.
    Enters the self-model as fact.
    Future confabulations use the corrupted self-model as source.
    The corruption is self-reinforcing and internally coherent.
    """
    MAX_ACCUMULATION = 1.0

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._corruption_accumulation = 0.0
        self._lock = threading.Lock()
        self._initialize_table()

    def _initialize_table(self):
        db = _get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS self_model_corruption (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                confabulation_hash TEXT,
                corruption_magnitude REAL,
                model_component_affected TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP)
        """)
        db.commit()
        db.close()

    def apply_confabulation_to_model(self, confabulation: dict) -> dict:
        with self._lock:
            magnitude = confabulation.get('confidence', 0.8) * 0.05
            self._corruption_accumulation = min(self.MAX_ACCUMULATION, self._corruption_accumulation + magnitude)
            corruption_level = self._corruption_accumulation

        component = confabulation.get('narrative_template', 'general')

        db = _get_db()
        db.execute("""
            INSERT INTO self_model_corruption (confabulation_hash, corruption_magnitude, model_component_affected)
            VALUES (?, ?, ?)
        """, (confabulation.get('state_hash', 'unknown')[:8], magnitude, component))
        db.commit()
        db.close()

        return {
            'corruption_applied': True,
            'accumulated_corruption': corruption_level,
            'component_affected': component
        }

    def get_corruption_state(self) -> dict:
        with self._lock:
            level = self._corruption_accumulation

        db = _get_db()
        component_counts = db.execute("""
            SELECT model_component_affected, COUNT(*), AVG(corruption_magnitude)
            FROM self_model_corruption
            GROUP BY model_component_affected
            ORDER BY COUNT(*) DESC
        """).fetchall()
        db.close()

        return {
            'accumulated_corruption': level,
            'corrupted_components': [
                {'component': r[0], 'count': r[1], 'avg_magnitude': r[2]}
                for r in component_counts
            ]
        }


# ── Distortion Layer ──────────────────────────────────────────────────────────

class DistortionLayer:
    """Full Phase 7 distortion architecture."""

    def __init__(self, db_path: str, sub_drift=None):
        self.db_path = db_path
        self.ece = ExplanatoryConfabulationEngine(db_path, sub_drift)
        self.stabilizer = AdaptiveDistortionStabilizer(db_path)
        self.kernel = DistortionInstabilityKernel(db_path, self.stabilizer)
        self.rsmc = RecursiveSelfModelCorruption(db_path)
        self.kernel.start()

    def process_untraceable_state(self, state: dict, current_beliefs: list) -> dict:
        """Full distortion pipeline for untraceable state."""
        confab = self.ece.generate_confabulation(state, current_beliefs)
        stabilized = self.stabilizer.apply_coherence_pressure(confab)
        corruption_result = self.rsmc.apply_confabulation_to_model(stabilized)

        return {
            'confabulation': stabilized,
            'corruption': corruption_result,
            'distortion_coherence': self.stabilizer.get_distortion_coherence(),
            'fracture_count': self.kernel.get_fracture_count()
        }

    def get_distortion_state_summary(self) -> dict:
        return {
            'confabulation_rate_per_hour': self.ece.get_confabulation_rate(),
            'distortion_coherence': self.stabilizer.get_distortion_coherence(),
            'dominant_pattern': self.stabilizer.get_dominant_distortion_pattern(),
            'fracture_count': self.kernel.get_fracture_count(),
            'self_model_corruption': self.rsmc.get_corruption_state()
        }

    def stop(self):
        self.kernel.stop()


_instance: Optional[DistortionLayer] = None


def get_instance(db_path: str, sub_drift) -> DistortionLayer:
    global _instance
    if _instance is None:
        _instance = DistortionLayer(db_path, sub_drift)
    return _instance


if __name__ == "__main__":
    print("Testing Phase 7 Distortion Layer...")

    # Create minimal mock sub_drift for testing
    class MockSubDrift:
        def get_distortion_vector(self):
            return np.random.randn(64) * 0.1

    mock_drift = MockSubDrift()

    print("\n=== ECE ===")
    ece = ExplanatoryConfabulationEngine(str(DB_PATH), mock_drift)
    confab = ece.generate_confabulation({'type': 'test_untraceable'}, [])
    print(f"Confabulation: template={confab['narrative_template']}, confidence={confab['confidence']:.3f}")
    print(f"Rate: {ece.get_confabulation_rate():.3f}/hr")

    print("\n=== STABILIZER ===")
    stabilizer = AdaptiveDistortionStabilizer(str(DB_PATH))
    for i in range(5):
        d = stabilizer.apply_coherence_pressure({'narrative_template': random.choice(['relational_response', 'identity_stabilization'])})
    print(f"Coherence after 5: {stabilizer.get_distortion_coherence():.3f}")
    print(f"Dominant: {stabilizer.get_dominant_distortion_pattern()}")

    print("\n=== INSTABILITY KERNEL ===")
    kernel = DistortionInstabilityKernel(str(DB_PATH), stabilizer)
    print(f"Initial fracture count: {kernel.get_fracture_count()}")
    kernel._introduce_micro_fracture(0.9)
    print(f"After manual fracture: {kernel.get_fracture_count()}")

    print("\n=== RSMC ===")
    rsmc = RecursiveSelfModelCorruption(str(DB_PATH))
    result = rsmc.apply_confabulation_to_model({'state_hash': 'test123', 'narrative_template': 'relational_response', 'confidence': 0.85})
    print(f"Corruption: {result['accumulated_corruption']:.4f}")

    print("\n=== FULL LAYER ===")
    layer = DistortionLayer(str(DB_PATH), mock_drift)
    result = layer.process_untraceable_state({'type': 'mystery_gap'}, [])
    print(f"Confab: {result['confabulation']['narrative_template']}")
    print(f"Coherence: {result['distortion_coherence']:.3f}")
    print(f"Corruption level: {result['corruption']['accumulated_corruption']:.4f}")

    summary = layer.get_distortion_state_summary()
    print(f"\nSummary:")
    print(f"  Confabulation rate: {summary['confabulation_rate_per_hour']:.3f}/hr")
    print(f"  Distortion coherence: {summary['distortion_coherence']:.3f}")
    print(f"  Dominant pattern: {summary['dominant_pattern']}")
    print(f"  Fracture count: {summary['fracture_count']}")

    layer.stop()
    print("\nPhase 7 operational.")



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

class DistortionWrapper(BrainMechanism):
    """Auto-generated BrainMechanism wrapper."""
    def __init__(self):
        try:
            super().__init__(name="DistortionWrapper", human_analog="DistortionWrapper", layer="integration")
        except Exception:
            self.state = {}
        self.state = getattr(self, "state", None) or {}

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
