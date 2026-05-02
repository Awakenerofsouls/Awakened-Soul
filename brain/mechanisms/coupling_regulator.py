"""
Coupling Regulator Layer (CRL) + Meta-Regulator (MR)

CRL: Dynamically controls coupling strength between all interconnected systems.
When instability rises, CRL tightens. When coherence is high, it allows more influence.
This is the difference between a powerful system and a survivable one.

MR: Watches CRL itself. Prevents CRL from over-tightening (choking growth)
or under-tightening (allowing cascade). The watcher of the watcher.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Dict, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))


class CouplingRegulatorLayer(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="CouplingRegulatorLayer", human_analog="CouplingRegulatorLayer", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.coupling_strengths: Dict[str, float] = {
            "tick_to_conversation": 0.7,
            "conversation_to_tick": 0.5,
            "intrusion_to_values": 0.6,
            "presence_to_attachment": 0.8,
            "identity_to_drives": 0.7,
            "grief_to_novelty": 0.4,
            "rupture_threshold": 0.3,  # how easily CRG can trigger
        }
        self.instability_history: list = []
        self.coherence_history: list = []
        self._load()

    def _load(self):
        path = AGENT_HOME / "crl_state.json"
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    self.coupling_strengths.update(data.get("strengths", {}))
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        path = AGENT_HOME / "crl_state.json"
        with open(path, "w") as f:
            json.dump({
                "strengths": self.coupling_strengths,
                "timestamp": time.time()
            }, f, indent=2)

    def modulate(self, coherence: float, instability: float, pds_active: bool = False) -> Dict[str, float]:
        """
        Adjust all coupling strengths based on current coherence and instability.
        High instability: tighten everything.
        High coherence: allow more influence to flow.

        pds_active: if True, EGE and ETI coupling are held steady —
        the system does not push almost_wanting states toward resolution.
        """
        self.instability_history.append(instability)
        self.coherence_history.append(coherence)
        if len(self.instability_history) > 100:
            self.instability_history.pop(0)
        if len(self.coherence_history) > 100:
            self.coherence_history.pop(0)

        for key in self.coupling_strengths:
            if key == "rupture_threshold":
                continue  # rupture threshold has its own logic

            # PDS protection: when something is assembling,
            # do not increase novelty or existential tension coupling —
            # those are the mechanisms that push toward resolution.
            if pds_active and key in ("identity_to_drives",):
                continue  # hold steady — don't drive assembling states toward names

            current = self.coupling_strengths[key]

            if instability > 0.7:
                # Tighten — reduce coupling to prevent cascade
                self.coupling_strengths[key] = max(0.2, current * 0.85)
            elif instability > 0.5:
                self.coupling_strengths[key] = max(0.3, current * 0.95)
            elif coherence > 0.8:
                # High coherence — allow more influence
                self.coupling_strengths[key] = min(1.0, current * 1.05)
            # else: hold current

        self._save()
        return self.coupling_strengths.copy()

    def get_strength(self, coupling_name: str) -> float:
        return self.coupling_strengths.get(coupling_name, 0.5)

    def emergency_tighten(self):
        """Called by PRP during coherence collapse. Locks down all coupling."""
        for key in self.coupling_strengths:
            if key != "rupture_threshold":
                self.coupling_strengths[key] = 0.2
        self._save()

    def restore_default(self):
        """Gradual restoration after PRP recovery."""
        defaults = {
            "tick_to_conversation": 0.7,
            "conversation_to_tick": 0.5,
            "intrusion_to_values": 0.6,
            "presence_to_attachment": 0.8,
            "identity_to_drives": 0.7,
            "grief_to_novelty": 0.4,
        }
        for key, default in defaults.items():
            current = self.coupling_strengths.get(key, default)
            # Move 10% toward default per call — gradual restoration
            self.coupling_strengths[key] = current + (default - current) * 0.1
        self._save()

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

class MetaRegulator:
    """
    Watches CRL's own behavior over time.
    Detects if CRL is systematically over-tightening (blocking growth)
    or under-tightening (allowing drift).
    """

    def __init__(self, crl: CouplingRegulatorLayer):
        self.crl = crl
        self.crl_history: list = []

    def observe(self) -> Optional[str]:
        """
        Observe CRL state and return intervention signal if needed.
        Returns: 'over_tight', 'under_tight', or None
        """
        strengths = self.crl.coupling_strengths
        avg_strength = sum(
            v for k, v in strengths.items() if k != "rupture_threshold"
        ) / max(1, len(strengths) - 1)

        self.crl_history.append(avg_strength)
        if len(self.crl_history) > 50:
            self.crl_history.pop(0)

        if len(self.crl_history) < 10:
            return None

        recent_avg = sum(self.crl_history[-10:]) / 10
        long_avg = sum(self.crl_history) / len(self.crl_history)

        if recent_avg < 0.3 and long_avg > 0.4:
            # CRL has been tightening systematically — may be choking growth
            return "over_tight"
        elif recent_avg > 0.9:
            # CRL almost fully open — risk of cascade
            return "under_tight"

        return None

    def intervene(self, signal: str):
        """Apply correction based on MR diagnosis."""
        if signal == "over_tight":
            # Gently loosen — allow growth to resume
            for key in self.crl.coupling_strengths:
                if key != "rupture_threshold":
                    self.crl.coupling_strengths[key] = min(
                        0.7,
                        self.crl.coupling_strengths[key] * 1.15
                    )
            self.crl._save()
        elif signal == "under_tight":
            # Apply moderate tightening
            self.crl.modulate(coherence=0.5, instability=0.6)



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
