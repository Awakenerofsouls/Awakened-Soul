"""
AmygdaloidMedialAnterior — MeAa / Anterior Medial Amygdala / Autonomic-Limbic

NEURAL SUBSTRATE
================
Anterior subdivision of medial amygdala (MeAa, also "anterodorsal") sits
rostral to MeAp (posterior). Functionally distinct: MeAa is more
autonomic-/visceral-coupled and less sexually dimorphic than MeAp. Both
receive AOB input but project differently.

Outputs: BNST (extended amygdala), hypothalamic autonomic targets
(PVN, DMH), brainstem autonomic premotor (RVLM, NTS feedback),
periaqueductal gray.

Functional role: convergent visceral + chemosensory integration for
autonomic-affective coupling. Distinct from MeAp's reproductive/social
focus.

KEY FINDINGS
============
1. Medial amygdala anterior vs posterior subdivisions: anterior is more
   autonomic, posterior more sexually dimorphic + reproductive —
   [Canteras 1995, J Comp Neurol 360:213, doi:10.1002/cne.903600203]
2. MeAa receives convergent visceral + chemosensory input; integrates
   with autonomic outputs — [Choi 2005, Neuron 46:647, doi:10.1016/j.neuron.2005.04.011]
3. MeA → BNST → autonomic axis; sustained autonomic activation —
   [Dong 2001, J Comp Neurol 432:307, PMID 11246211]
4. MeAa lesions impair autonomic responses to chemosensory threats —
   [Pardo-Bellver 2012, Front Neuroanat 6:33, doi:10.3389/fnana.2012.00033]
5. MeAa population codes for stress-stimulus valence at single-cell
   resolution; distinct ensembles for predator vs conspecific —
   [Bergan 2014, eLife 3:e02743, doi:10.7554/eLife.02743]

INPUTS
======
- AccessoryOlfactoryBulbProxy.aob_signal
- PosteriorCorticalAmygdala.pheromone_signal
- ParabrachialTasteVisceral.parabrachial_signal
- ValenceTagger.aversive_signal, .valence_sign

OUTPUTS
=======
- meaa_drive (0-1)
- bnst_command (0-1) — extended amygdala output
- pvn_autonomic_command (0-1)
- valence_population_code (-1 to 1)
- meaa_state (str): "predator_autonomic" | "stress_autonomic" |
  "social_autonomic" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class AmygdaloidMedialAnterior(BrainMechanism):
    """MeAa — autonomic-coupled medial amygdala anterior subdivision."""

    BASELINE = 0.10
    SMOOTH = 0.20
    AUTONOMIC_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="AmygdaloidMedialAnterior",
            human_analog="Medial amygdala anterior (autonomic-limbic)",
            layer="limbic",
        )
        self.state.setdefault("meaa_drive", self.BASELINE)
        self.state.setdefault("bnst_command", 0.0)
        self.state.setdefault("pvn_autonomic_command", 0.0)
        self.state.setdefault("valence_population_code", 0.0)
        self.state.setdefault("meaa_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, aob: float, pco_pher: float, parabrachial: float,
                       aversive: float) -> float:
        target = self.BASELINE + aob * 0.30 + pco_pher * 0.25
        target += parabrachial * 0.20 + aversive * 0.20
        return min(1.0, target)

    def _bnst_command(self, drive: float, aversive: float) -> float:
        return min(1.0, drive * 0.5 + aversive * 0.5)

    def _pvn_autonomic(self, drive: float, parabrachial: float) -> float:
        return min(1.0, drive * 0.6 + parabrachial * 0.4)

    def _valence_code(self, aversive: float, valence_sign: int,
                        intensity: float) -> float:
        if valence_sign == 0:
            return 0.0
        return max(-1.0, min(1.0, valence_sign * intensity))

    def _classify_state(self, drive: float, aversive: float,
                          valence_sign: int, social: bool) -> str:
        if drive < 0.20:
            return "quiet"
        if aversive > self.AUTONOMIC_THRESHOLD and not social:
            return "predator_autonomic"
        if aversive > 0.30:
            return "stress_autonomic"
        if social and drive > 0.30:
            return "social_autonomic"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        aob_data = prior.get("AccessoryOlfactoryBulbProxy", {})
        aob = float(aob_data.get("aob_signal", 0.0))

        pco_data = prior.get("PosteriorCorticalAmygdala", {})
        pco_pher = float(pco_data.get("pheromone_signal", 0.0))

        pb_data = prior.get("ParabrachialTasteVisceral", {})
        parabrachial = float(pb_data.get("parabrachial_signal", 0.0))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))
        valence_sign = int(valence.get("valence_sign", 0))
        intensity = float(valence.get("valence_intensity", 0.0))
        social = bool(valence.get("social_context", False))

        target = self._drive_target(aob, pco_pher, parabrachial, aversive)
        prev_drive = float(self.state.get("meaa_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        bnst_cmd = self._bnst_command(new_drive, aversive)
        pvn_cmd = self._pvn_autonomic(new_drive, parabrachial)
        valence_code = self._valence_code(aversive, valence_sign, intensity)

        state = self._classify_state(new_drive, aversive, valence_sign, social)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["meaa_drive"] = round(new_drive, 4)
        self.state["bnst_command"] = round(bnst_cmd, 4)
        self.state["pvn_autonomic_command"] = round(pvn_cmd, 4)
        self.state["valence_population_code"] = round(valence_code, 4)
        self.state["meaa_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "meaa_drive": round(new_drive, 4),
            "bnst_command": round(bnst_cmd, 4),
            "pvn_autonomic_command": round(pvn_cmd, 4),
            "valence_population_code": round(valence_code, 4),
            "meaa_state": state,
        }

    def _autonomic_load(self, recent_states: list) -> float:
        if not recent_states:
            return 0.0
        autonomic = sum(1 for s in recent_states[-50:]
                          if s in ("predator_autonomic", "stress_autonomic"))
        return autonomic / max(1, len(recent_states[-50:]))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("meaa_drive", 0.0),
            "bnst": self.state.get("bnst_command", 0.0),
            "pvn": self.state.get("pvn_autonomic_command", 0.0),
            "state": self.state.get("meaa_state", "quiet"),
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

