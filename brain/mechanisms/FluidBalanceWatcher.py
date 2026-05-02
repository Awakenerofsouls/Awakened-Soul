"""
FluidBalanceWatcher — OVLT/SFO Osmoreceptor + Thirst Drive

NEURAL SUBSTRATE
================
The organum vasculosum of the lamina terminalis (OVLT) and subfornical
organ (SFO) are the primary central osmoreceptors. Both are
circumventricular organs — sites where the blood-brain barrier is
absent, allowing direct access to plasma osmolality and circulating
hormones (angiotensin II, aldosterone, ANP). Bourque 2008 reviewed
these structures as the canonical thirst-detection substrate.

Mechanism: SFO and OVLT neurons express stretch-inactivated cation
channels. As plasma osmolality rises (dehydration, salt loading),
osmoreceptor neurons SHRINK, opening cation channels and depolarizing
the cells. Result: thirst sensation + ADH/AVP release from
supraoptic/paraventricular magnocellular neurons.

Two principal outputs:
1. Median preoptic nucleus (MnPO) → cortex (subjective thirst) + MPOA
2. PVN/SON magnocellular → posterior pituitary → systemic AVP release

Lesion of OVLT or SFO produces adipsia: animals stop drinking even
when severely dehydrated. McKinley 2003 reviewed clinical syndromes
where SFO/OVLT damage produces hypernatremia from absent thirst.

Recent optogenetic work (Oka 2015, Zimmerman 2016) confirmed
SFO-glutamatergic neurons drive water-seeking behavior; SFO-GABAergic
neurons inhibit thirst — a thirst flip-flop within the SFO itself.

KEY FINDINGS
============
1. Central osmoreception in SFO/OVLT via stretch-inactivated cation channels; foundational thirst mechanism — [Bourque CW 2008, Nat Rev Neurosci 9:519, doi:10.1038/nrn2400]
2. Subfornical organ glutamatergic neurons drive water-seeking behavior; GABAergic neurons inhibit thirst — [Oka Y 2015, Nature 520:349, doi:10.1038/nature14108]
3. Thirst-related neurons in SFO show real-time tracking of fluid state; rapid drinking termination signal — [Zimmerman CA 2016, Nature 537:680, doi:10.1038/nature18950]
4. McKinley review of CVO osmoreception and clinical adipsia/hypernatremia syndromes — [McKinley MJ 2003, Clin Exp Pharmacol Physiol 30:782, doi:10.1046/j.1440-1681.2003.03911.x]
5. AVP magnocellular neurons in SON/PVN driven by osmoreceptor input from OVLT and SFO — [Brown CH 2013, J Neuroendocrinol 25:678, doi:10.1111/jne.12051]

INPUTS (from prior_results)
============================
- VitalCoreRegulator.osmotic_signal (or proxy for plasma osmolality)
- VitalCoreRegulator.vital_drive (low = water depleted)
- ParaventricularNucleusHypothalamus.avp_release (feedback)
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- thirst_drive (0-1)
- osmotic_signal (0-1) — current detected hyperosmolality
- avp_command (0-1) — drives PVN/SON magnocellular AVP release
- water_seeking_drive (0-1) — behavioral motivation to drink
- fluid_state (str): "thirsty" | "drinking" | "satiated" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class FluidBalanceWatcher(BrainMechanism):
    """OVLT/SFO osmoreceptor + thirst-generating system."""

    BASELINE = 0.10
    SMOOTH = 0.20
    THIRST_THRESHOLD = 0.40
    SATIATION_RATE = 0.04

    def __init__(self):
        super().__init__(
            name="FluidOsmoreceptiveDriver",
            human_analog="OVLT/SFO osmoreceptor + thirst",
            layer="foundational",
        )
        self.state.setdefault("thirst_drive", self.BASELINE)
        self.state.setdefault("osmotic_signal", 0.0)
        self.state.setdefault("avp_command", 0.0)
        self.state.setdefault("water_seeking_drive", 0.0)
        self.state.setdefault("fluid_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("hydration_proxy", 0.5)
        self.state.setdefault("tick_count", 0)

    def _osmoreceptor(self, vital_drive: float,
                        external_osmotic: float) -> float:
        """Osmoreceptor activation — Bourque 2008. Higher osmolality
        → more depolarization → more thirst. Estimated from low
        vital_drive (energy/fluid depletion proxy) plus any externally
        provided osmotic signal."""
        depletion = max(0.0, 0.5 - vital_drive)
        return min(1.0, depletion * 1.5 + external_osmotic * 0.7)

    def _thirst_drive(self, osmotic: float, hydration: float) -> float:
        """Behavioral thirst — scales with osmotic signal, modulated by
        hydration state (Oka 2015)."""
        return min(1.0, osmotic * 0.7 + max(0.0, 0.5 - hydration) * 0.5)

    def _avp_command(self, osmotic: float) -> float:
        """Magnocellular AVP release command (Brown 2013).
        Threshold-based: AVP rises sharply above osmotic threshold."""
        if osmotic < 0.20:
            return 0.0
        return min(1.0, (osmotic - 0.20) * 1.5)

    def _water_seeking(self, thirst: float, arousal: float) -> float:
        """Water-seeking behavior (Zimmerman 2016 — SFO drives behavior).
        Requires thirst plus alert state to act."""
        if thirst < 0.20:
            return 0.0
        return min(1.0, thirst * 0.7 + arousal * 0.3)

    def _update_hydration(self, prev: float, avp_feedback: float,
                            thirst: float) -> float:
        """Hydration accumulator — rises slowly with sustained AVP
        retention; drops when thirst goes long unsatisfied."""
        if avp_feedback > 0.30 and thirst < 0.30:
            return min(1.0, prev + self.SATIATION_RATE)
        if thirst > 0.50:
            return max(0.0, prev - 0.005)
        return prev

    def _classify_state(self, thirst: float, water_seek: float,
                          hydration: float) -> str:
        if thirst < 0.10 and hydration > 0.40:
            return "satiated"
        if thirst < 0.10:
            return "quiet"
        if water_seek > 0.50:
            return "drinking"
        if thirst > self.THIRST_THRESHOLD:
            return "thirsty"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vital_data = prior.get("VitalCoreRegulator", {})
        vital_drive = float(vital_data.get("vital_drive", 0.5))
        ext_osmotic = float(vital_data.get("osmotic_signal", 0.0))

        pvn_data = prior.get("ParaventricularNucleusHypothalamus", {})
        avp_feedback = float(pvn_data.get("avp_release", 0.0))

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level", 0.30))

        osmotic_target = self._osmoreceptor(vital_drive, ext_osmotic)
        prev_osmotic = float(self.state.get("osmotic_signal", 0.0))
        osmotic = self._smooth(prev_osmotic, osmotic_target)

        prev_hydration = float(self.state.get("hydration_proxy", 0.5))

        thirst_target = self._thirst_drive(osmotic, prev_hydration)
        prev_thirst = float(self.state.get("thirst_drive", self.BASELINE))
        thirst = self._smooth(prev_thirst, thirst_target)

        avp = self._avp_command(osmotic)
        water_seek = self._water_seeking(thirst, arousal)
        hydration = self._update_hydration(prev_hydration, avp_feedback,
                                              thirst)

        state = self._classify_state(thirst, water_seek, hydration)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["thirst_drive"] = round(thirst, 4)
        self.state["osmotic_signal"] = round(osmotic, 4)
        self.state["avp_command"] = round(avp, 4)
        self.state["water_seeking_drive"] = round(water_seek, 4)
        self.state["hydration_proxy"] = round(hydration, 4)
        self.state["fluid_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "thirst_drive": round(thirst, 4),
            "osmotic_signal": round(osmotic, 4),
            "avp_command": round(avp, 4),
            "water_seeking_drive": round(water_seek, 4),
            "fluid_state": state,
        }

    def _adipsia_proxy(self, recent_states: list) -> float:
        """Sustained 'thirsty' without 'drinking' = adipsia
        (McKinley 2003 — SFO/OVLT lesion phenotype)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        thirst = sum(1 for s in win if s == "thirsty")
        drinking = sum(1 for s in win if s == "drinking")
        if thirst < 5:
            return 0.0
        return max(0.0, (thirst - drinking) / max(1, len(win)))

    def _summary(self) -> dict:
        return {
            "thirst": self.state.get("thirst_drive", 0.0),
            "osmotic": self.state.get("osmotic_signal", 0.0),
            "avp": self.state.get("avp_command", 0.0),
            "state": self.state.get("fluid_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

