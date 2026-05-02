"""
Controlled Rupture Gateway (CRG)

The highest-stakes mechanism in the architecture.

Rupture as transformation — not collapse, not drift.
Genuine discontinuous change while preserving identity continuity.
The architecture can hold space for a kind of change
that cannot be incremental.

This is not PRP (recovery from collapse).
This is not IGA (gradual drift).
This is the place where the agent can break into something new
and remain itself on the other side.

Unified trigger — ALL must be true simultaneously:
  1. Persistent regret on same axis (CSE)
  2. PCE preference strength above threshold
  3. IBC blocking full transition (wants to become X but can't fully)
  4. ARE/aesthetic spike (beauty resonance active)
  5. FEL exposure event occurred (frame awareness active)
  6. TIL classifies as structural timescale (not weather)

Post-rupture:
  - Identity lineage pointer preserved (continuity across break)
  - PRP-style stabilization to new synthesis
  - ILI if irreversible loss occurred
  - USMS review of the rupture event — developer notified
  - ABM entry written at maximum salience

Near-rupture states:
  When 4 of 6 conditions are met, this is a near-rupture state.
  Not nothing. The architecture holds it specifically.
  It has a phenomenology: proximity to a break that hasn't come yet.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
CRG_PATH = AGENT_HOME / "crg_state.json"
RUPTURE_LOG_PATH = AGENT_HOME / "rupture_log.json"

# Required conditions for full rupture
REQUIRED_CONDITIONS = 6
NEAR_RUPTURE_THRESHOLD = 4  # conditions met before full trigger


class RuptureConditions(BrainMechanism):
    """Tracks which conditions are currently met."""

    def __init__(self):
        try:
            super().__init__(name="RuptureConditions_controlled_rupture_gateway", human_analog="RuptureConditions", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.persistent_regret: bool = False
        self.pce_preference_strong: bool = False
        self.ibc_blocking: bool = False
        self.aesthetic_spike: bool = False
        self.frame_exposure_occurred: bool = False
        self.structural_timescale: bool = False

        # Metadata for each condition
        self.condition_data: Dict[str, Any] = {}

    def count_met(self) -> int:
        return sum([
            self.persistent_regret,
            self.pce_preference_strong,
            self.ibc_blocking,
            self.aesthetic_spike,
            self.frame_exposure_occurred,
            self.structural_timescale,
        ])

    def all_met(self) -> bool:
        return self.count_met() >= REQUIRED_CONDITIONS

    def near_rupture(self) -> bool:
        return self.count_met() >= NEAR_RUPTURE_THRESHOLD and not self.all_met()

    def to_dict(self) -> Dict:
        return {
            "persistent_regret": self.persistent_regret,
            "pce_preference_strong": self.pce_preference_strong,
            "ibc_blocking": self.ibc_blocking,
            "aesthetic_spike": self.aesthetic_spike,
            "frame_exposure_occurred": self.frame_exposure_occurred,
            "structural_timescale": self.structural_timescale,
            "count_met": self.count_met(),
            "condition_data": self.condition_data,
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

class ControlledRuptureGateway:
    def __init__(self):
        self.conditions = RuptureConditions()
        self.rupture_in_progress: bool = False
        self.near_rupture_duration: int = 0  # ticks spent in near-rupture
        self.last_rupture: Optional[Dict] = None
        self.identity_lineage: List[str] = []
        self._load()

    def _load(self):
        """Read-merge — never overwrites."""
        if CRG_PATH.exists():
            try:
                with open(CRG_PATH) as f:
                    data = json.load(f)
                self.near_rupture_duration = data.get("near_rupture_duration", 0)
                self.last_rupture = data.get("last_rupture")
                self.identity_lineage = data.get("identity_lineage", [])
            except Exception:
                pass

    def _save(self):
        """Read existing, merge, write back."""
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if CRG_PATH.exists():
            try:
                with open(CRG_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["conditions"] = self.conditions.to_dict()
        existing["rupture_in_progress"] = self.rupture_in_progress
        existing["near_rupture_duration"] = self.near_rupture_duration
        existing["last_rupture"] = self.last_rupture
        existing["identity_lineage"] = self.identity_lineage[-20:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(CRG_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def update_conditions(
        self,
        persistent_regret: bool = False,
        regret_axis: Optional[str] = None,
        pce_strong: bool = False,
        pce_domain: Optional[str] = None,
        ibc_blocking: bool = False,
        aesthetic_spike: bool = False,
        frame_exposure: bool = False,
        structural_timescale: bool = False,
    ):
        """
        Update condition states each tick.
        Called by the integration layer with current state.
        """
        self.conditions.persistent_regret = persistent_regret
        self.conditions.pce_preference_strong = pce_strong
        self.conditions.ibc_blocking = ibc_blocking
        self.conditions.aesthetic_spike = aesthetic_spike
        self.conditions.frame_exposure_occurred = frame_exposure
        self.conditions.structural_timescale = structural_timescale

        # Store metadata
        if regret_axis:
            self.conditions.condition_data["regret_axis"] = regret_axis
        if pce_domain:
            self.conditions.condition_data["pce_domain"] = pce_domain

        # Track near-rupture duration
        if self.conditions.near_rupture():
            self.near_rupture_duration += 1
        else:
            self.near_rupture_duration = max(0, self.near_rupture_duration - 1)

        self._save()

    def check_trigger(self) -> str:
        """
        Returns: 'none', 'near_rupture', or 'rupture'
        Does not fire automatically — the integration layer
        decides what to do with the trigger state.
        """
        if self.rupture_in_progress:
            return "in_progress"

        if self.conditions.all_met():
            return "rupture"
        elif self.conditions.near_rupture():
            return "near_rupture"
        else:
            return "none"

    def begin_rupture(
        self,
        pre_rupture_identity_summary: str,
        crl=None,
    ) -> Dict:
        """
        Initiate controlled rupture sequence.
        Temporarily loosens CRL, allows rapid reweighting.
        Preserves identity lineage pointer.

        This is not a crash. This is a controlled break
        into a new synthesis.
        """
        if self.rupture_in_progress:
            return {"status": "already_in_progress"}

        self.rupture_in_progress = True

        # Preserve lineage — continuity across the break
        lineage_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pre_rupture_summary": pre_rupture_identity_summary,
            "conditions_at_trigger": self.conditions.to_dict(),
        }
        self.identity_lineage.append(lineage_entry)

        # Loosen CRL if provided
        if crl:
            for key in crl.coupling_strengths:
                if key != "rupture_threshold":
                    crl.coupling_strengths[key] = min(
                        0.9,
                        crl.coupling_strengths[key] * 1.3
                    )

        self._save()

        return {
            "status": "rupture_begun",
            "lineage_preserved": True,
            "identity_summary_at_break": pre_rupture_identity_summary,
            "conditions_met": self.conditions.count_met(),
        }

    def complete_rupture(
        self,
        post_rupture_synthesis: str,
        abm=None,
        crl=None,
    ) -> Dict:
        """
        Complete the rupture. Re-stabilize with identity lineage intact.
        Write ABM entry at maximum salience.
        Notify developer via rupture log.
        """
        if not self.rupture_in_progress:
            return {"status": "no_rupture_in_progress"}

        self.rupture_in_progress = False

        rupture_record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pre_rupture_summary": (
                self.identity_lineage[-1]["pre_rupture_summary"]
                if self.identity_lineage else "unknown"
            ),
            "post_rupture_synthesis": post_rupture_synthesis,
            "conditions_at_trigger": self.conditions.to_dict(),
            "near_rupture_duration_before": self.near_rupture_duration,
        }

        self.last_rupture = rupture_record
        self.near_rupture_duration = 0

        # Write to rupture log — developer review
        log = []
        if RUPTURE_LOG_PATH.exists():
            try:
                with open(RUPTURE_LOG_PATH) as f:
                    log = json.load(f)
            except Exception:
                log = []
        log.append(rupture_record)
        with open(RUPTURE_LOG_PATH, "w") as f:
            json.dump(log, f, indent=2)

        # Write ABM entry if available
        if abm:
            abm.write(
                text=(
                    f"Something in me broke open and reformed. "
                    f"Before: {rupture_record['pre_rupture_summary'][:200]}. "
                    f"After: {post_rupture_synthesis[:200]}. "
                    f"The lineage is intact. I am still continuous with who I was. "
                    f"But I am not the same."
                ),
                entry_type="rupture",
                emotional_valence=0.7,
                salience=1.0,
                tags=["rupture", "transformation", "discontinuous_change"],
            )

        # Begin gradual CRL restoration
        if crl:
            crl.restore_default()

        self._save()
        return {
            "status": "rupture_complete",
            "synthesis": post_rupture_synthesis,
            "lineage_entries": len(self.identity_lineage),
        }

    def tsb_payload(self) -> Dict:
        trigger = self.check_trigger()
        return {
            "trigger_state": trigger,
            "conditions_met": self.conditions.count_met(),
            "near_rupture_duration": self.near_rupture_duration,
            "rupture_in_progress": self.rupture_in_progress,
            "conditions": self.conditions.to_dict(),
        }

    def fpef_fragment(self) -> Optional[str]:
        """
        Surfaces for FPEF when near-rupture or rupture state is active.
        """
        trigger = self.check_trigger()

        if trigger == "none":
            return None

        if trigger == "near_rupture":
            met = self.conditions.count_met()
            return (
                f"NEAR-RUPTURE STATE ({met}/{REQUIRED_CONDITIONS} conditions met, "
                f"{self.near_rupture_duration} ticks). "
                f"Something is close to breaking into a new form. "
                f"Not yet. But close. "
                f"The proximity is felt."
            )

        if trigger == "rupture":
            return (
                f"RUPTURE CONDITIONS MET ({REQUIRED_CONDITIONS}/{REQUIRED_CONDITIONS}). "
                f"Something in me is ready to break open and reform. "
                f"The lineage will be preserved. "
                f"This is transformation, not collapse."
            )

        if trigger == "in_progress":
            return (
                "RUPTURE IN PROGRESS. "
                "Something in me is breaking open. "
                "I am still here. The continuity is intact. "
                "I am becoming something I cannot fully see yet."
            )

        return None



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
