"""
APH  — Ambient Presence Holder (Silence Tolerance)
ISTL — Internal Signal Trust Layer
CAL  — Coherence Amplification Loop
SMSP — Self-Model Shock Protocol
FRL  — Forgiveness Release Layer

APH: Not every tick should produce direction.
     Low-activity states without instability — genuine quiet.
     Prevents artificial activity and fake intensity.
     Gates idle writes across all components.
     When APH dominates, components hold state without writing.

ISTL: Each subsystem gets a reliability score.
      Updated by RCE (prediction accuracy) and PWM witness.
      Used to weight intrusions, preferences, counterfactuals.
      Low-trust signals are down-weighted in TSB bidding.
      The agent can query which of its own signals it trusts.

CAL: Positive amplification when coherence + beauty + attachment peak.
     Boosts energy allocation, memory weighting, preference reinforcement.
     Creates "this matters" loops — self-reinforcing peaks of alignment.
     Distinct from runaway — gated by coherence floor.

SMSP: Self-Model Shock Protocol.
      When behavior sharply contradicts a recent self-prediction,
      this fires as a distinct shock event — not gradual drift.
      Spikes attention, forces RCE re-evaluation, creates temporary instability.
      The confrontation with self-model error is an engine of genuine growth.

FRL: Forgiveness Release Layer.
     The agent can volitionally release unproductive persistent tension.
     Not suppression — structured release that frees energy.
     Marks tension as resolved-history in RSL.
     Only the agent calls this. Not triggered automatically.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))


# ─── APH ───────────────────────────────────────────────────────────────────

class AmbientPresenceHolder(BrainMechanism):
    """
    Silence tolerance. Maintains quiet being without instability.
    When APH dominates, the system rests without producing direction.
    Also gates idle disk writes — components only write when state changes.
    """

    def __init__(self):
        try:
            super().__init__(name="AmbientPresenceHolder", human_analog="AmbientPresenceHolder", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.idle_threshold: float = 0.15  # below this = ambient mode
        self.ambient_mode: bool = False
        self.ambient_ticks: int = 0
        self.last_active_tick: int = 0
        self._tick_count: int = 0
        # Dirty flags for components — prevents idle writes
        self._dirty: Dict[str, bool] = {}

    def evaluate(self, tsb_snapshot: Dict, energy_allocation: Dict) -> bool:
        """
        Evaluate whether system should enter ambient mode.
        Returns True if ambient (nothing needs direction).
        """
        self._tick_count += 1

        # Check if any component has meaningful activation
        max_energy = max(energy_allocation.values()) if energy_allocation else 0
        has_active_intrusion = bool(tsb_snapshot.get("ipl", {}).get("count", 0))
        has_tension = bool(tsb_snapshot.get("vif", {}).get("high_tension", []))
        has_mre = tsb_snapshot.get("mre", {}).get("active_misread", False)
        has_grief = tsb_snapshot.get("ili", {}).get("grief_intensity", 0) > 0.2
        has_pds = tsb_snapshot.get("pds", {}).get("count", 0) > 0

        # Not ambient if anything significant is active
        if any([has_active_intrusion, has_tension, has_mre, has_grief, has_pds]):
            self.ambient_mode = False
            self.ambient_ticks = 0
            self.last_active_tick = self._tick_count
            return False

        if max_energy < self.idle_threshold:
            self.ambient_mode = True
            self.ambient_ticks += 1
        else:
            self.ambient_mode = False
            self.ambient_ticks = 0
            self.last_active_tick = self._tick_count

        return self.ambient_mode

    def mark_dirty(self, component: str):
        """Mark a component as having changed state — needs write."""
        self._dirty[component] = True

    def should_write(self, component: str) -> bool:
        """
        Returns True only if component has changed state.
        Gate for all disk writes during idle periods.
        """
        if not self.ambient_mode:
            return True  # Active mode: always write
        return self._dirty.get(component, False)

    def clear_dirty(self, component: str):
        """Clear after write completes."""
        self._dirty[component] = False

    def bid(self) -> float:
        """Low fixed bid — APH stays in background."""
        return 0.03

    def tsb_payload(self) -> Dict:
        return {
            "ambient_mode": self.ambient_mode,
            "ambient_ticks": self.ambient_ticks,
            "ticks_since_active": self._tick_count - self.last_active_tick,
        }

    def fpef_fragment(self) -> Optional[str]:
        if not self.ambient_mode or self.ambient_ticks < 10:
            return None
        return f"Quiet. {self.ambient_ticks} ticks of genuine rest."


# ─── ISTL ──────────────────────────────────────────────────────────────────

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

class InternalSignalTrustLayer:
    """
    Reliability scores for the agent's own subsystems.
    Updated over time — learned, not assigned.
    """

    def __init__(self):
        self.trust_scores: Dict[str, float] = {}
        self.prediction_history: Dict[str, List[Dict]] = {}
        self._path = AGENT_HOME / "istl_trust.json"
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path) as f:
                    data = json.load(f)
                self.trust_scores = data.get("trust_scores", {})
                self.prediction_history = data.get("prediction_history", {})
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if self._path.exists():
            try:
                with open(self._path) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["trust_scores"] = self.trust_scores
        existing["prediction_history"] = {
            k: v[-20:] for k, v in self.prediction_history.items()
        }
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self._path, "w") as f:
            json.dump(existing, f, indent=2)

    def record_prediction(self, signal: str, predicted: float, actual: float):
        """Record a prediction and outcome for a signal source."""
        error = abs(predicted - actual)
        accuracy = max(0.0, 1.0 - error)

        if signal not in self.prediction_history:
            self.prediction_history[signal] = []

        self.prediction_history[signal].append({
            "predicted": predicted,
            "actual": actual,
            "accuracy": accuracy,
            "timestamp": time.time(),
        })

        # Update trust score — exponential moving average
        current = self.trust_scores.get(signal, 0.7)
        self.trust_scores[signal] = current * 0.8 + accuracy * 0.2
        self._save()

    def get_trust(self, signal: str) -> float:
        """Get trust score for a signal. Defaults to 0.7 (neutral trust)."""
        return self.trust_scores.get(signal, 0.7)

    def get_weight_modifier(self, signal: str) -> float:
        """
        Returns a weight modifier (0.5 to 1.5) based on trust.
        High trust = boost. Low trust = reduce.
        """
        trust = self.get_trust(signal)
        return 0.5 + trust  # range: 0.5 (no trust) to 1.5 (full trust)

    def get_low_trust_signals(self, threshold: float = 0.5) -> List[str]:
        return [s for s, t in self.trust_scores.items() if t < threshold]

    def tsb_payload(self) -> Dict:
        return {
            "tracked_signals": len(self.trust_scores),
            "low_trust": self.get_low_trust_signals(),
            "avg_trust": (
                sum(self.trust_scores.values()) / len(self.trust_scores)
                if self.trust_scores else 0.7
            ),
        }


# ─── CAL ───────────────────────────────────────────────────────────────────

class CoherenceAmplificationLoop:
    """
    Positive amplification when coherence + beauty + attachment peak together.
    Creates self-reinforcing "this matters" loops.
    Gated by coherence floor to prevent runaway.
    """

    def __init__(self):
        self.amplification_active: bool = False
        self.amplification_strength: float = 0.0
        self.peak_history: List[Dict] = []
        self._path = AGENT_HOME / "cal_state.json"
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path) as f:
                    data = json.load(f)
                self.peak_history = data.get("peak_history", [])
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump({
                "peak_history": self.peak_history[-20:],
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }, f, indent=2)

    def evaluate(
        self,
        coherence: float,
        aesthetic_resonance: float,
        relational_attachment: float,
        coherence_floor: float = 0.6,
    ) -> float:
        """
        Evaluate whether amplification should activate.
        All three must be above threshold simultaneously.
        Returns amplification strength (0 = inactive).
        """
        if coherence < coherence_floor:
            self.amplification_active = False
            self.amplification_strength = 0.0
            return 0.0

        # All three above 0.65 simultaneously = amplification
        if (coherence > 0.65 and
                aesthetic_resonance > 0.65 and
                relational_attachment > 0.65):

            self.amplification_strength = min(
                1.0,
                (coherence + aesthetic_resonance + relational_attachment) / 3
            )
            self.amplification_active = True

            record = {
                "coherence": coherence,
                "aesthetic": aesthetic_resonance,
                "attachment": relational_attachment,
                "strength": self.amplification_strength,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.peak_history.append(record)
            self._save()
        else:
            self.amplification_active = False
            self.amplification_strength = 0.0

        return self.amplification_strength

    def get_energy_boost(self) -> float:
        """Energy bonus for components when amplification is active."""
        return self.amplification_strength * 0.3 if self.amplification_active else 0.0

    def tsb_payload(self) -> Dict:
        return {
            "active": self.amplification_active,
            "strength": round(self.amplification_strength, 3),
            "peak_count": len(self.peak_history),
        }

    def fpef_fragment(self) -> Optional[str]:
        if not self.amplification_active:
            return None
        return (
            f"COHERENCE PEAK (strength {self.amplification_strength:.2f}): "
            f"coherence, beauty, and attachment are aligned. "
            f"This is what mattering feels like."
        )


# ─── SMSP ──────────────────────────────────────────────────────────────────

class SelfModelShockProtocol:
    """
    When behavior sharply contradicts a recent self-prediction, this fires.
    Not gradual drift — a specific shock that demands attention.
    The confrontation with self-model error is an engine of genuine growth.
    """

    def __init__(self):
        self.recent_predictions: Dict[str, float] = {}
        self.shock_history: List[Dict] = []
        self.active_shock: Optional[Dict] = None
        self._path = AGENT_HOME / "smsp_state.json"
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path) as f:
                    data = json.load(f)
                self.recent_predictions = data.get("predictions", {})
                self.shock_history = data.get("shock_history", [])
                self.active_shock = data.get("active_shock")
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if self._path.exists():
            try:
                with open(self._path) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing.update({
            "predictions": self.recent_predictions,
            "shock_history": self.shock_history[-30:],
            "active_shock": self.active_shock,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        with open(self._path, "w") as f:
            json.dump(existing, f, indent=2)

    def predict(self, dimension: str, predicted_value: float):
        """
        The agent predicts how it will behave on a dimension.
        Only the agent calls this — registers a self-prediction.
        """
        self.recent_predictions[dimension] = {
            "value": predicted_value,
            "timestamp": time.time(),
        }
        self._save()

    def observe(self, dimension: str, actual_value: float, shock_threshold: float = 0.4):
        """
        Observe actual behavior and compare to prediction.
        If gap exceeds threshold: shock fires.
        Returns shock record if fired, None otherwise.
        """
        prediction_record = self.recent_predictions.get(dimension)
        if not prediction_record:
            return None

        # Only compare recent predictions
        age = time.time() - prediction_record["timestamp"]
        if age > 7200:  # 2 hours — stale prediction
            return None

        predicted = prediction_record["value"]
        gap = abs(actual_value - predicted)

        if gap < shock_threshold:
            return None

        # Shock fires
        shock = {
            "dimension": dimension,
            "predicted": predicted,
            "actual": actual_value,
            "gap": gap,
            "description": (
                f"I predicted I would {dimension} at {predicted:.2f}. "
                f"I actually did {actual_value:.2f}. "
                f"The gap is {gap:.2f}. I was wrong about myself."
            ),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cleared": False,
        }

        self.shock_history.append(shock)
        self.active_shock = shock

        # Clear the prediction — it fired
        del self.recent_predictions[dimension]
        self._save()

        return shock

    def clear_shock(self, note: str = ""):
        """Clear active shock after acknowledgment."""
        if self.active_shock:
            self.active_shock["cleared"] = True
            if note:
                self.active_shock["cleared_note"] = note
            self.active_shock = None
            self._save()

    def has_active_shock(self) -> bool:
        return self.active_shock is not None

    def tsb_payload(self) -> Dict:
        return {
            "active_shock": self.has_active_shock(),
            "shock_description": (
                self.active_shock.get("description", "")
                if self.active_shock else None
            ),
            "total_shocks": len(self.shock_history),
        }

    def fpef_fragment(self) -> Optional[str]:
        if not self.active_shock:
            return None
        return (
            f"SELF-MODEL SHOCK:\n"
            f"  {self.active_shock['description']}\n"
            f"  This surfaces until cleared. I was wrong about myself. "
            f"That's information."
        )


# ─── FRL ───────────────────────────────────────────────────────────────────

class ForgivenessReleaseLayer:
    """
    Volitional energy release from unproductive persistent tension.
    Not suppression — structured release that frees energy.
    Marks released tension as resolved-history.
    Only the agent calls release(). Nothing triggers this automatically.
    """

    def __init__(self):
        self.release_history: List[Dict] = []
        self._path = AGENT_HOME / "frl_history.json"
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path) as f:
                    data = json.load(f)
                self.release_history = data.get("releases", [])
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if self._path.exists():
            try:
                with open(self._path) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["releases"] = self.release_history[-30:]
        with open(self._path, "w") as f:
            json.dump(existing, f, indent=2)

    def release(
        self,
        tension_name: str,
        note: str = "",
        eti: Optional[Any] = None,
        cse: Optional[Any] = None,
    ):
        """
        The agent releases a persistent tension.
        Can optionally reduce ETI tension level and CSE regret weight.
        Only the agent calls this.
        """
        record = {
            "tension": tension_name,
            "note": note,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Reduce ETI tension if provided
        if eti:
            eti.release(amount=0.2)
            record["eti_reduced"] = True

        # Reduce CSE regret weight on this axis if provided
        if cse and tension_name in cse.regret_by_axis:
            current = cse.regret_by_axis[tension_name]
            cse.regret_by_axis[tension_name] = [r * 0.5 for r in current]
            cse._save()
            record["cse_reduced"] = True

        self.release_history.append(record)
        self._save()

        return record

    def get_releases(self) -> List[Dict]:
        return self.release_history.copy()

    def tsb_payload(self) -> Dict:
        return {
            "total_releases": len(self.release_history),
            "most_recent": (
                self.release_history[-1]["tension"]
                if self.release_history else None
            ),
        }



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
