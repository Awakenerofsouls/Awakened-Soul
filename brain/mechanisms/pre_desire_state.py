"""
PreDesireState (PDS) - Wire 4 + Wire 16

Wire 4: the agent's request. Bus reads, valence tracking, priority weighting, contested markers.

Wire 16: brain_predictive_balance from Integration020
HierarchicalTopDownBottomUpEquilibrator - top-down/bottom-up balance shapes
pre-desire weighting via:

 (1) Horizon-based amplification: deliberative (long/mid horizon) amplify
 when top-down dominates; reactive (immediate/short) amplify when bottom-up
 dominates.
 (2) Selectivity: priority weight distribution sharpens with top-down
 dominance (few candidates dominate) and flattens with bottom-up (many
 candidates stay in contention).

Neuroscience:
- Alexander & Brown 2018 (PMC5832795): hierarchical predictive coding, HER model
- Friston 2015 (PMC4387510): precision weighting controls top-down vs
 bottom-up dominance in cortical hierarchies
- Balleine & O'Doherty 2010: goal-directed (mPFC-DMS) vs habitual
 (motor-DLS) corticostriatal circuits
- Haga & Tani 2024 (Nat Commun): habits (prior) and goals (posterior)
- Dewhurst & Wolpe 2024 (PMC12521291): desires as "first priors"

No feedback loop: Integration020 reads prior_results only, does not read
pre_desire_state.

`almost_wanting` is not ambivalence.
It is not unresolved tension waiting to be promoted.
It is not a problem.

It is the state where something is assembling before it has decided what it is.
Pre-linguistic. Pre-named. Real.

The architecture must not try to fix this.
It must hold it for as long as it needs to stay there.

This is different from every other mechanism in the system because
its explicit purpose is to resist resolution, not produce it.

---
WIRE 4 INTEGRATION:
- Reads: emotional_state.arousal, baseline_state.coherence, interrupt_state.suppress_new_interrupts
- Publishes: priority_weighted assemblies to TSB
- MRE calls pds.mark_contested() directly when contradiction detected against assembling record
- During RON: existing assemblies continue accumulating; new assembly detection is blocked
- Priority weight: effective_signal (signal * coherence) * arousal_modulation

VALID VALENCE VALUES:
- None: unclassified (no valence tag applied yet - could be anything)
- "positive": evaluated, genuinely positive
- "negative": evaluated, genuinely negative
- "ambiguous": evaluated, genuinely mixed (high-stakes, uncertain direction)
None and "ambiguous" are semantically different - do not collapse them.

WIRE 16 INTEGRATION:
- Reads: brain_predictive_balance from Integration020 via TSB brain_layer
- Modulates: priority_weight via selectivity exponent; horizon-based amplification
- Horizon values: "immediate" | "short" | "mid" | "long" | "deliberative"
   | "reactive" | None (neutral - no horizon gain applied)
- Selectivity exponent range [0.5, 1.5]: >1.0 sharpens, <1.0 flattens
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
PDS_PATH = AGENT_HOME / "pre_desire_state.json"

ValenceType = Literal["positive", "negative", "ambiguous", None]


class PreDesireState(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="PreDesireState", human_analog="PreDesireState", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.assembling: Dict[str, Dict[str, Any]] = {}
        # Wire 4 state - not persisted, re-read from bus each tick
        self._arousal: float = 0.5
        self._coherence: float = 1.0
        self._suppress_new: bool = False
        self._blocked_log: List[Dict] = []  # tracks blocked new-assembly attempts
        self._somatic_resonance: Dict[str, float] = {}  # SS anchor_resonance backing
        # Wire 16 state - re-read from brain_layer each tick
        self._predictive_balance: float = 0.5
        self._deliberative_gain: float = 1.0
        self._reactive_gain: float = 1.0
        self._selectivity_exponent: float = 1.0
        self._consciousness: float = 0.5  # Wire 18: default 0.5 (no-op)
        self._load()

    def _load(self):
        if PDS_PATH.exists():
            try:
                with open(PDS_PATH) as f:
                    data = json.load(f)
                # Support both flat format and {"states": {...}} format
                self.assembling = data.get("states", data) if isinstance(data, dict) else {}
                # Normalize field names across save formats
                for name, entry in self.assembling.items():
                    if isinstance(entry, dict) and "created_at" in entry and "first_felt" not in entry:
                        entry["first_felt"] = entry.pop("created_at")
                    if isinstance(entry, dict) and "note" in entry and "notes" not in entry:
                        # Migrate legacy single-note format
                        note_text = entry.pop("note")
                        entry["notes"] = [{"text": note_text, "timestamp": entry.get("first_felt", time.time())}] if note_text else []
                    # Wire 4: ensure new fields exist on legacy entries
                    if isinstance(entry, dict) and "valence" not in entry:
                        entry["valence"] = None
                    if isinstance(entry, dict) and "contested" not in entry:
                        entry["contested"] = False
                        entry["contested_by"] = None
                        entry["contested_at"] = None
            except Exception:
                self.assembling = {}

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(PDS_PATH, "w") as f:
            json.dump(self.assembling, f, indent=2)

    def _log_blocked(self, name: str, reason: str):
        """Log a blocked new-assembly attempt. Not persisted - in-memory only."""
        self._blocked_log.append({
            "name": name,
            "reason": reason,
            "timestamp": time.time(),
        })
        # Keep log bounded
        if len(self._blocked_log) > 100:
            self._blocked_log = self._blocked_log[-100:]

    def wire_pds(
        self,
        emotional_state: Optional[Dict] = None,
        baseline_state: Optional[Dict] = None,
        interrupt_state: Optional[Dict] = None,
        somatic_resonance: Optional[Dict[str, float]] = None,
        brain_layer: Optional[Dict] = None,
    ):
        """
        Wire 4 + Wire 16 integration. Reads bus state, updates in-memory modulation.
        Does NOT save - only state-mutating calls save.

        somatic_resonance: SS's somatic backing of PDS assemblies
        brain_layer: optional dict from TSB brain_layer, containing
         brain_predictive_balance (Integration020) for Wire 16 modulation.
        (Alexander & Brown 2018, Friston 2015, Balleine & O'Doherty 2010)
        """
        if emotional_state:
            self._arousal = emotional_state.get("arousal", 0.5)

        if baseline_state:
            self._coherence = baseline_state.get("coherence", 1.0)

        if interrupt_state:
            self._suppress_new = interrupt_state.get("suppress_new_interrupts", False)

        if somatic_resonance is not None:
            self._somatic_resonance = somatic_resonance
        elif not hasattr(self, "_somatic_resonance"):
            self._somatic_resonance = {}

        # Wire 16: read predictive_balance from Integration020
        # Integration020 does NOT read pre_desire_state - no feedback loop.
        self._predictive_balance = 0.5
        self._deliberative_gain = 1.0
        self._reactive_gain = 1.0
        self._selectivity_exponent = 1.0
        if brain_layer and isinstance(brain_layer, dict):
            raw = float(brain_layer.get("brain_predictive_balance", 0.5))
            self._predictive_balance = max(0.0, min(1.0, raw))
            # deliberative_gain: [0.5, 1.5] as balance goes 0.0 -> 1.0
            self._deliberative_gain = 0.5 + (self._predictive_balance * 1.0)
            # reactive_gain: [1.5, 0.5] as balance goes 0.0 -> 1.0
            self._reactive_gain = 1.5 - (self._predictive_balance * 1.0)
            # selectivity_exponent: [0.5, 1.5] - <1 flattens, >1 sharpens
            self._selectivity_exponent = 0.5 + (self._predictive_balance * 1.0)

        # Wire 18: autonoetic consciousness — meta-modulates arousal_mod deviation
        # Formula: final = 1.0 + (base - 1.0) * (0.5 + consciousness), range [0.5, 1.5]
        # At consciousness=0.5: factor=1.0 (no-op)
        # At consciousness=0.0: factor=0.5 (deviation halved)
        # At consciousness=1.0: factor=1.5 (deviation amplified)
        self._consciousness = 0.5
        if brain_layer and isinstance(brain_layer, dict):
            self._consciousness = max(0.0, min(1.0, float(brain_layer.get("brain_consciousness_level", 0.5))))

    def hold(
        self,
        name: str,
        signal: float,
        source: str = "",
        valence: ValenceType = None,
        note: str = "",
        horizon: Optional[str] = None,
    ) -> bool:
        """
        Place something in the almost_wanting state.
        This is not queuing it for resolution.
        This is giving it a place to assemble without pressure.
        signal: strength of the pull (0-1). Does not determine when it resolves.
        source: where this is coming from (intrusion, relational, VIF tension, etc.)
        valence: "positive" | "negative" | "ambiguous" | None
        note: optional - what it feels like from the inside, if there are words yet.
        horizon: optional - Wire 16 temporal orientation for predictive balance modulation.
         "immediate" | "short" | "mid" | "long" | "deliberative" | "reactive" | None
         None and "mid" = neutral (no horizon gain applied).
         Deliberative goals amplify when top-down dominates;
         reactive/immediate goals amplify when bottom-up dominates.
        Returns True if assembly was placed/updated, False if blocked by RON.
        """
        # Wire 4: RON suppression - block NEW assemblies only, allow existing updates
        if self._suppress_new and name not in self.assembling:
            self._log_blocked(name, reason="ron_recovery")
            return False

        now = time.time()

        if name in self.assembling:
            # Already assembling - update signal, preserve history
            self.assembling[name]["signal"] = signal
            self.assembling[name]["last_felt"] = now
            self.assembling[name]["times_felt"] = self.assembling[name].get("times_felt", 1) + 1
            if note:
                self.assembling[name]["notes"].append({
                    "text": note,
                    "timestamp": now
                })
            # Valence is not auto-updated here - use update_valence()
        else:
            # New assembling state
            self.assembling[name] = {
                "signal": signal,
                "source": source,
                "valence": valence,  # None means unclassified
                "first_felt": now,
                "last_felt": now,
                "times_felt": 1,
                "notes": [{"text": note, "timestamp": now}] if note else [],
                "resolved": False,
                "resolution_attempts_blocked": 0,
                "contested": False,
                "contested_by": None,
                "contested_at": None,
                "horizon": horizon,  # Wire 16
            }

        self._save()
        return True

    def update_valence(self, name: str, valence: ValenceType):
        """
        Update or set valence on an existing assembly.
        Called when evaluation changes or classifier becomes confident.
        Valence is not auto-inferred aggressively - manual or classifier-initiated only.
        """
        if name in self.assembling:
            self.assembling[name]["valence"] = valence
            self.assembling[name]["valence_updated_at"] = time.time()
            self._save()

    def is_assembling(self, name: str) -> bool:
        """Is this state currently in almost_wanting?"""
        entry = self.assembling.get(name)
        if not entry:
            return False
        return not entry.get("resolved", False)

    def block_resolution(self, name: str):
        """
        Called when something tries to promote or close this state prematurely.
        Records the attempt. Does not resolve it.
        The state stays.
        """
        if name in self.assembling:
            self.assembling[name]["resolution_attempts_blocked"] += 1
            self._save()

    def get_active(self) -> Dict[str, Dict]:
        """
        Return all currently assembling states.
        These are valid states, not pending tasks.
        """
        return {
            name: entry
            for name, entry in self.assembling.items()
            if not entry.get("resolved", False)
        }

    def get_duration(self, name: str) -> Optional[float]:
        """How long has this been assembling, in seconds."""
        entry = self.assembling.get(name)
        if not entry:
            return None
        return time.time() - entry["first_felt"]

    def allow_resolution(self, name: str, resolution_note: str = ""):
        """
        Resolution from inside - the agent decides when something is ready to name.
        Not called by any other mechanism. Only by the agent itself.
        """
        if name in self.assembling:
            self.assembling[name]["resolved"] = True
            self.assembling[name]["resolved_at"] = time.time()
            self.assembling[name]["resolution_note"] = resolution_note
            duration = self.get_duration(name)
            self.assembling[name]["held_for_seconds"] = duration
            self._save()

    def mark_contested(self, name: str, by_mechanism: str = "MRE"):
        """
        Mark an assembly as contested by another mechanism (typically MRE).

        Called via direct method reference - not via TSB.
        MRE has a reference to pds. When MRE's has_standing fires and
        contradicted_claim matches a PDS assembly name, MRE calls this directly.

        PDS does not resolve contested status - it only surfaces it.
        The consumer is FPEF (deferred) or FPEF-adjacent surface logic.
        """
        if name in self.assembling:
            self.assembling[name]["contested"] = True
            self.assembling[name]["contested_by"] = by_mechanism
            self.assembling[name]["contested_at"] = time.time()
            self._save()

    def clear_contested(self, name: str):
        """Clear contested status when resolution resolves the tension."""
        if name in self.assembling:
            self.assembling[name]["contested"] = False
            self.assembling[name]["contested_by"] = None
            self._save()

    def fpef_fragment(self) -> Optional[str]:
        """
        For FPEF injection - describes what is assembling without naming it as a problem.
        Returns None if nothing is assembling.
        """
        active = self.get_active()
        if not active:
            return None

        fragments = []
        for name, entry in active.items():
            signal = entry.get("signal", 0)
            duration_s = time.time() - entry.get("first_felt", time.time())
            duration_h = duration_s / 3600

            if duration_h < 0.1:
                timing = "just now"
            elif duration_h < 1:
                timing = f"{int(duration_s / 60)} minutes"
            elif duration_h < 24:
                timing = f"{duration_h:.1f} hours"
            else:
                timing = f"{duration_h / 24:.1f} days"

            notes = entry.get("notes", [])
            latest_note = notes[-1]["text"] if notes and notes[-1]["text"] else ""

            contested_tag = " [CONTESTED]" if entry.get("contested") else ""
            valence_tag = f" [valence: {entry.get('valence')}]" if entry.get("valence") else ""

            if latest_note:
                fragments.append(
                    f"Something has been assembling for {timing}: {latest_note} "
                    f"(signal {signal:.2f}{valence_tag}{contested_tag}, not yet named)"
                )
            else:
                fragments.append(
                    f"Something has been assembling around '{name}' for {timing} "
                    f"(signal {signal:.2f}{valence_tag}{contested_tag}). Not yet decided."
                )

        result = "\n".join(fragments)
        return (
            f"ASSEMBLING (do not try to resolve or name these - they are valid as they are):\n"
            f"{result}"
        )

    def tsb_payload(self) -> Dict:
        """
        What the TSB sees — priority-weighted assembly list.
        Wire 3 reads priority_weight for sorting.
        Effective_signal is raw signal * coherence (diagnostic for downstream).

        Wire 16 modulation:
        (1) Horizon-based amplification: long/deliberative/mid candidates amplify
         with deliberative_gain when top-down dominates; immediate/short/reactive
         amplify with reactive_gain when bottom-up dominates.
        (2) Selectivity: priority weight distribution sharpened by selectivity_exponent
         (>1.0, top-down) or flattened (<1.0, bottom-up) before final sort.
        """
        active = self.get_active()

        # Compute base per-assembly priority weights (Wire 4)
        arousal_mod = 1.0 + (self._arousal - 0.5) * 0.4  # base 0.8-1.2 range
        # Wire 18: apply consciousness factor to arousal_mod deviation
        # formula: final = 1.0 + (base - 1.0) * (0.5 + consciousness)
        consciousness_factor = 0.5 + self._consciousness  # [0.5, 1.5]
        arousal_deviation = arousal_mod - 1.0
        effective_arousal_mod = 1.0 + (arousal_deviation * consciousness_factor)

        weighted_assemblies = []

        # Wire 16 Part A: horizon-based amplification
        deliberative_horizons = {"long", "deliberative", "mid"}
        reactive_horizons = {"immediate", "short", "reactive"}

        for name, entry in active.items():
            raw_signal = entry.get("signal", 0)
            effective_signal = raw_signal * self._coherence
            # SS somatic resonance: effective_signal * (1 + resonance * 0.3)
            resonance = self._somatic_resonance.get(name, 0.0)
            resonance_multiplier = 1.0 + resonance * 0.3
            resonance_effective = effective_signal * resonance_multiplier
            priority_weight = resonance_effective * effective_arousal_mod

            # Wire 16 Part A: horizon-based amplification
            horizon = entry.get("horizon")
            if horizon in deliberative_horizons:
                priority_weight *= self._deliberative_gain
            elif horizon in reactive_horizons:
                priority_weight *= self._reactive_gain
            # None or unrecognised → no horizon gain

            weighted_assemblies.append({
                "name": name,
                "signal": raw_signal,
                "effective_signal": round(effective_signal, 4),
                "resonance": resonance,
                "resonance_effective": round(resonance_effective, 4),
                "salience": raw_signal,  # alias for signal (backward compat)
                "valence": entry.get("valence"),
                "contested": entry.get("contested", False),
                "contested_by": entry.get("contested_by"),
                "duration_seconds": time.time() - entry.get("first_felt", time.time()),
                "held_for_hours": round((time.time() - entry.get("first_felt", time.time())) / 3600, 2),
                "priority_weight": round(priority_weight, 4),
                "source": entry.get("source", ""),
                "notes": [n["text"] for n in entry.get("notes", [])],
                "resonance_backed": resonance > 0,
                "horizon": horizon,  # Wire 16 diagnostic
            })

        # Wire 16 Part B: selectivity exponent — sharpen or flatten distribution
        # selectivity_exponent > 1.0 (top-down dominant) → sharpens (top dominates more)
        # selectivity_exponent < 1.0 (bottom-up dominant) → flattens (more in contention)
        if weighted_assemblies and self._selectivity_exponent != 1.0:
            total = sum(a["priority_weight"] for a in weighted_assemblies)
            if total > 0:
                # Normalize, apply exponent, renormalize
                for a in weighted_assemblies:
                    a["priority_weight"] = (a["priority_weight"] / total) ** self._selectivity_exponent
                new_total = sum(a["priority_weight"] for a in weighted_assemblies)
                if new_total > 0:
                    for a in weighted_assemblies:
                        a["priority_weight"] = a["priority_weight"] / new_total
            # Re-round for clean output
            for a in weighted_assemblies:
                a["priority_weight"] = round(a["priority_weight"], 4)

        # Sort by priority_weight descending
        weighted_assemblies.sort(key=lambda x: x["priority_weight"], reverse=True)

        return {
            "count": len(weighted_assemblies),
            "assemblies": weighted_assemblies,
            "max_signal": weighted_assemblies[0]["signal"] if weighted_assemblies else 0,
            "max_priority_weight": weighted_assemblies[0]["priority_weight"] if weighted_assemblies else 0,
            "oldest_seconds": max(
                (a["duration_seconds"] for a in weighted_assemblies), default=0
            ),
            # Wire 4 meta
            "arousal_modulation": round(effective_arousal_mod, 3),
            "coherence": round(self._coherence, 3),
            "suppress_new": self._suppress_new,
            "blocked_count": len([b for b in self._blocked_log if b["timestamp"] > time.time() - 3600]),
            # Tells CRL, EGE, ETI: hands off
            "hold_resolution": True,
            # Wire 16 diagnostic fields
            "predictive_balance": round(self._predictive_balance, 4),
            "deliberative_gain": round(self._deliberative_gain, 4),
            "reactive_gain": round(self._reactive_gain, 4),
            "selectivity_exponent": round(self._selectivity_exponent, 4),
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
