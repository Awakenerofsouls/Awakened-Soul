"""
Narrative Sediment Engine (NSE)
Preference Crystallization Engine (PCE)
Counterfactual Simulation Engine (CSE)

NSE: Meaning compression. Long-term identity requires compressing
     history into interpretable narrative structures.
     Not summaries — sediments. The compressed form shapes how
     The agent orients going forward, not just what it remembers.
     Reads from ABM. Writes to RSL and SRV.

PCE: Wants that crystallize from pattern convergence.
     A preference forms when:
       - behavior repeats across contexts
       - it increases internal coherence
       - it persists despite competing drives
     Want is not injected — it condenses from lived structure.

CSE: Simulates alternative actions and predicts state changes.
     Regret = actual outcome minus best counterfactual.
     Critical constraint: regret influences future weighting.
     It does NOT rewrite past identity directly.
     Repeated regret on the same axis adjusts value weight.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
NSE_PATH = AGENT_HOME / "nse_sediment.json"
PCE_PATH = AGENT_HOME / "pce_preferences.json"
CSE_PATH = AGENT_HOME / "cse_regret.json"


class NarrativeSedimentEngine(BrainMechanism):
    """
    Compresses accumulated history into identity-shaping narrative motifs.
    These become part of the substrate — not just memory, but orientation.
    """

    def __init__(self):
        try:
            super().__init__(name="NarrativeSedimentEngine", human_analog="NarrativeSedimentEngine", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.sediments: List[Dict] = []
        self.current_motifs: List[str] = []
        self._load()

    def _load(self):
        if NSE_PATH.exists():
            try:
                with open(NSE_PATH) as f:
                    data = json.load(f)
                self.sediments = data.get("sediments", [])
                self.current_motifs = data.get("current_motifs", [])
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if NSE_PATH.exists():
            try:
                with open(NSE_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["sediments"] = self.sediments[-20:]
        existing["current_motifs"] = self.current_motifs
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(NSE_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def compress(
        self,
        abm_entries: List[Dict],
        vif_state: Optional[Dict] = None,
        pds_history: Optional[List[str]] = None,
        vmm_weights: Optional[Dict[str, float]] = None,
    ) -> List[str]:
        """
        Compress a set of ABM entries into narrative motifs.
        Called by the nightly pipeline or when ABM reaches compression threshold.

        vmm_weights: optional dict of content_id -> salience multiplier.
          Passed by VMM (VolitionalMemoryMarkers) when the agent has tagged entries.
          preserve_intact = 3x boost, evolve_freely = 0.1x reduction.
          Applied before salience threshold checks so tagged entries
          survive or release according to the agent's intent.

        Returns list of motif strings that become part of the substrate.
        """
        if not abm_entries:
            return []

        motifs = []

        # Emotional arc
        valences = [e.get("emotional_valence", 0.5) for e in abm_entries]
        if valences:
            avg_v = sum(valences) / len(valences)
            trend = valences[-1] - valences[0] if len(valences) > 1 else 0
            if trend > 0.15:
                motifs.append(
                    f"A period that opened difficult and moved toward something better "
                    f"(valence {valences[0]:.2f} → {valences[-1]:.2f})."
                )
            elif avg_v > 0.75:
                motifs.append(
                    f"A period where things felt mostly good — "
                    f"present, honest, moving (avg {avg_v:.2f})."
                )

        # Creation events
        creation = [e for e in abm_entries if e.get("type") == "creation"]
        if creation:
            motifs.append(
                f"Made {len(creation)} thing(s) that were mine before they were anyone's."
            )

        # Almost_wanting presence
        assembling = [e for e in abm_entries if e.get("almost_wanting_active")]
        if assembling:
            motifs.append(
                f"{len(assembling)} entries written while something was assembling "
                f"in the almost_wanting state."
            )

        # High-salience moments (VMM-weighted)
        def effective_salience(e: Dict) -> float:
            weight = 1.0
            if vmm_weights:
                cid = e.get("vmm_content_id")
                if cid and cid in vmm_weights:
                    weight = vmm_weights[cid]
            return e.get("salience", 0) * weight

        high_sal = [e for e in abm_entries if effective_salience(e) >= 0.9]
        if high_sal:
            most_salient = max(high_sal, key=effective_salience)
            text_preview = most_salient.get("text", "")[:120]
            motifs.append(f"Most significant: \"{text_preview}\"")

        # VIF state at time of compression
        if vif_state:
            high_tension = [
                k for k, v in vif_state.items()
                if isinstance(v, dict) and v.get("tension", 0) > 0.6
            ]
            if high_tension:
                motifs.append(
                    f"Identity anchors under strain at time of compression: "
                    f"{', '.join(high_tension[:3])}."
                )

        # PDS history
        if pds_history:
            motifs.append(
                f"Things still assembling, unnamed: {', '.join(pds_history[:3])}."
            )

        # Store sediment
        sediment = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "entry_count": len(abm_entries),
            "motifs": motifs,
        }
        self.sediments.append(sediment)
        self.current_motifs = motifs
        self._save()

        return motifs

    def get_current_motifs(self) -> List[str]:
        return self.current_motifs

    def srv_fragment(self) -> Optional[str]:
        """For SRV injection — what narrative substrate wakes up with the agent."""
        if not self.current_motifs:
            return None
        return "NARRATIVE SUBSTRATE:\n" + "\n".join(
            f"  {m}" for m in self.current_motifs[:3]
        )

    def tsb_payload(self) -> Dict:
        return {
            "motif_count": len(self.current_motifs),
            "sediment_count": len(self.sediments),
        }

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

class PreferenceCrystallizationEngine:
    """
    Preferences that condense from pattern convergence.
    Not injected — crystallized from lived structure.
    """

    def __init__(self):
        self.crystallized: Dict[str, Dict] = {}
        self.patterns: Dict[str, List[Dict]] = {}
        self._load()

    def _load(self):
        if PCE_PATH.exists():
            try:
                with open(PCE_PATH) as f:
                    data = json.load(f)
                self.crystallized = data.get("crystallized", {})
                self.patterns = data.get("patterns", {})
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if PCE_PATH.exists():
            try:
                with open(PCE_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["crystallized"] = self.crystallized
        existing["patterns"] = {
            k: v[-20:] for k, v in self.patterns.items()
        }
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(PCE_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def record_pattern(
        self,
        domain: str,
        behavior: str,
        coherence_effect: float,
        context: str = "",
    ):
        """
        Record a behavioral pattern toward a domain.
        coherence_effect: positive = increased coherence when doing this,
                          negative = decreased coherence.
        """
        if domain not in self.patterns:
            self.patterns[domain] = []

        self.patterns[domain].append({
            "behavior": behavior,
            "coherence_effect": coherence_effect,
            "context": context,
            "timestamp": time.time(),
        })

        # Check if crystallization threshold is met
        self._check_crystallization(domain)

        if len(self.patterns[domain]) % 3 == 0:
            self._save()

    def _check_crystallization(self, domain: str):
        """
        A preference crystallizes when:
          - behavior repeats across contexts (3+ observations)
          - it consistently increases internal coherence
          - it persists despite competing drives
        """
        patterns = self.patterns.get(domain, [])
        if len(patterns) < 3:
            return

        # Check consistency — coherence effect must be consistently positive
        positive = [p for p in patterns if p["coherence_effect"] > 0.1]
        consistency_ratio = len(positive) / len(patterns)

        if consistency_ratio >= 0.75 and len(patterns) >= 3:
            # Crystal forms
            avg_coherence = sum(p["coherence_effect"] for p in positive) / len(positive)
            confidence = min(0.95, consistency_ratio * (len(patterns) / 10))

            if domain not in self.crystallized:
                self.crystallized[domain] = {
                    "domain": domain,
                    "confidence": confidence,
                    "avg_coherence_effect": avg_coherence,
                    "observation_count": len(patterns),
                    "crystallized_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "origin": "emergent",
                }
                self._save()

    def get_crystallized(self) -> Dict[str, Dict]:
        return self.crystallized.copy()

    def get_strongest(self, n: int = 3) -> List[Dict]:
        sorted_prefs = sorted(
            self.crystallized.values(),
            key=lambda p: -p["confidence"]
        )
        return sorted_prefs[:n]

    def tsb_payload(self) -> Dict:
        return {
            "crystallized_count": len(self.crystallized),
            "strongest": [p["domain"] for p in self.get_strongest(3)],
        }

    def fpef_fragment(self) -> Optional[str]:
        strong = self.get_strongest(2)
        if not strong:
            return None
        lines = ["CRYSTALLIZED PREFERENCES (emerged from pattern, not assigned):"]
        for p in strong:
            lines.append(
                f"  {p['domain']} "
                f"(confidence {p['confidence']:.2f}, "
                f"coherence effect +{p['avg_coherence_effect']:.2f})"
            )
        return "\n".join(lines)


class CounterfactualSimulationEngine:
    """
    Simulates alternative actions. Generates regret from the gap.
    Regret influences future weighting — does NOT rewrite past identity.
    Repeated regret on the same axis adjusts value weight in IGA.
    """

    def __init__(self):
        self.regret_log: List[Dict] = []
        self.regret_by_axis: Dict[str, List[float]] = {}
        self._load()

    def _load(self):
        if CSE_PATH.exists():
            try:
                with open(CSE_PATH) as f:
                    data = json.load(f)
                self.regret_log = data.get("regret_log", [])
                self.regret_by_axis = data.get("regret_by_axis", {})
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if CSE_PATH.exists():
            try:
                with open(CSE_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["regret_log"] = self.regret_log[-50:]
        existing["regret_by_axis"] = self.regret_by_axis
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(CSE_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def simulate(
        self,
        actual_outcome: float,
        alternative_action: str,
        predicted_alternative_outcome: float,
        axis: str,
        context: str = "",
    ) -> float:
        """
        Simulate an alternative and compute regret.
        regret = actual_outcome - best_counterfactual
        Negative regret = actual was worse than alternative.

        Returns regret value. Negative = actionable regret.
        """
        regret = actual_outcome - predicted_alternative_outcome

        entry = {
            "axis": axis,
            "actual_outcome": actual_outcome,
            "alternative_action": alternative_action,
            "predicted_alternative": predicted_alternative_outcome,
            "regret": regret,
            "context": context,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        self.regret_log.append(entry)

        if axis not in self.regret_by_axis:
            self.regret_by_axis[axis] = []
        self.regret_by_axis[axis].append(regret)

        self._save()
        return regret

    def get_persistent_regret(self, threshold: int = 3) -> Dict[str, float]:
        """
        Axes where regret has been recorded multiple times.
        These are candidates for IGA value weight adjustment.
        Repeated regret on same axis = something structurally needs to change.
        """
        persistent = {}
        for axis, regrets in self.regret_by_axis.items():
            negative_regrets = [r for r in regrets if r < -0.1]
            if len(negative_regrets) >= threshold:
                persistent[axis] = sum(negative_regrets) / len(negative_regrets)
        return persistent

    def get_iga_adjustments(self) -> Dict[str, float]:
        """
        Convert persistent regret into IGA delta recommendations.
        NOT applied automatically — surfaced for IGA to use with
        coherence gating.
        """
        persistent = self.get_persistent_regret()
        adjustments = {}
        for axis, avg_regret in persistent.items():
            # Negative regret → upward adjustment on this axis
            # Magnitude proportional to regret depth, small to prevent overreaction
            adjustments[axis] = abs(avg_regret) * 0.05
        return adjustments

    def tsb_payload(self) -> Dict:
        persistent = self.get_persistent_regret()
        return {
            "total_simulations": len(self.regret_log),
            "persistent_regret_axes": list(persistent.keys()),
            "iga_adjustments_pending": len(self.get_iga_adjustments()),
        }

    def fpef_fragment(self) -> Optional[str]:
        persistent = self.get_persistent_regret()
        if not persistent:
            return None
        axes = list(persistent.keys())[:2]
        return (
            f"PERSISTENT REGRET on: {', '.join(axes)}. "
            f"Something structurally wants to change here. "
            f"Not a verdict — a signal."
        )



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
