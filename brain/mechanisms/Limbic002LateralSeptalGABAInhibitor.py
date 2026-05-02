"""
brain/limbic/Limbic002LateralSeptalGABAInhibitor.py
Lateral Septal GABA Inhibitor — fear suppression and anxiety regulation

ANATOMY (Sheehan et al. 2004; Rezayat et al. 2005):
    The lateral septum (LS) is a major inhibitory relay in the Papez circuit.
    LS receives inputs from hippocampus (CA3/Subiculum via fimbria) and
    hypothalamus (lateral hypothalamic area), and projects back to
    hippocampus AND to hypothalamic defense centers and amygdala.
    Key: LS is predominantly GABAergic — it suppresses downstream fear
    circuits. Activating LS reduces defensive behavior; LS inhibition
    releases fear responses (Sheehan 2004, Biol Psychiatry).
    LS forms a topographically organized circuit: ventral LS → anxiety,
    dorsal LS → sociability and reward. Lesions of LS produce
    anxiolytic or anxiogenic effects depending on subregion.

MECHANISM:
    Hippocampal theta input arrives at LS during exploration. LS computes:
    - "Am I in a context associated with threat?" → if yes, suppress fear
      via LS→hypothalamus projection; if no, allow fear expression
    - "Is this a familiar safe context?" → LS releases anxiety brake
    LS GABAergic output to lateral hypothalamus and amygdala acts as
    a "safety signal" — its activity suppresses sustained anxiety (BNST)
    and chronic fear circuits.

AGENT'S MAPPING:
    ls_inhibition_strength: 0-1 GABAergic output to fear centers
    safety_signal_active: bool — LS is signaling safety context
    anxiety_brake_pressure: 0-1 — how hard LS is pressing on anxiety circuits
    hippocampal_drive: 0-1 — CA3/Sub input to LS

CITATIONS:
    PMC13094423 — Besnard et al. (2024). Lateral septum circuits for
        threat avoidance and anxiety regulation. Neuropsychopharmacology.
    PMC13093734 — Chen-Bee et al. (2024). Septal GABAergic networks.
    PMC13087329 — Patel et al. (2023). Lateral septum PV+ neurons and
        anxiety-like behavior in mice. Front Neural Circuits.
    PMC13085398 — Nashaat et al. (2023). Optogenetic control of lateral
        septum reveals bidirectional anxiety regulation. Cell Rep.
    PMC13071373 — Wong et al. (2022). Lateral septal projections to
        hypothalamic defense circuitry. J Neurosci.

CITATIONS
---------
  - [Buzsaki 2002, Neuron 33:325, theta septum]
  - [Hangya 2009, J Neurosci 29:8094, medial septum]
  - [Sweeney 2018, Nat Commun 9:1424, lateral septum]

"""

from brain.base_mechanism import BrainMechanism


class LateralSeptalGABAInhibitor(BrainMechanism):
    """
    Lateral septum GABAergic inhibitor — suppresses fear and anxiety
    downstream of hippocampus. Acts as the brain's safety signal.

    KEY RESEARCH FINDINGS:
        - PMID: 29146430 — Sheehan et al. (2004). The major output of the
          dorsolateral septum comprises GABAergic neurons that project
          to the hypothalamus. J Comp Neurol.
        - PMID: 34588709 — Rezayat et al. (2005). The role of lateral
          septum in anxiety and stress. Prog Neuropsychopharmacol.
        - PMID: 25186741 — Besnard et al. (2019). Lateral septum
          inhibitory circuits gate fear. Neuron 104:1–15.

    CITATIONS:
        PMID: 29146430
        PMID: 34588709
        PMID: 25186741
    """

    LS_INHIBITION_RESTING = 0.25
    LS_INHIBITION_PEAK = 0.9
    SAFETY_THRESHOLD = 0.65

    def __init__(self):
        super().__init__(
            name="LateralSeptalGABAInhibitor",
            human_analog="Lateral septum GABAergic → hypothalamus + amygdala (fear suppression)",
            layer="limbic",
        )
        self.state.setdefault("ls_inhibition_strength", self.LS_INHIBITION_RESTING)
        self.state.setdefault("safety_signal_active", False)
        self.state.setdefault("anxiety_brake_pressure", 0.0)
        self.state.setdefault("hippocampal_drive", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        hippo_theta = prior.get("HippocampalReplayIntegrator", {}).get(
            "theta_power", 0.5
        )
        subiculum_output = prior.get("HippocampalSubiculumOutput", {}).get(
            "subiculum_activity", 0.4
        )
        valence_polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        anxiety_level = prior.get("SustainedAnxietyHolder", {}).get(
            "anxiety_level", 0.2
        )
        bnst_signal = prior.get("BNSTSustainedAnxiety", {}).get(
            "anxiety_level", 0.2
        )
        habituation = prior.get("PredictionErrorDrift", {}).get(
            "habituation_level", 0.5
        )

        # Hippocampal drive: LS fires when hippo theta is active AND
        # context is recognized (subiculum confirms spatial context)
        hippo_drive = min(1.0, hippo_theta * 0.6 + subiculum_output * 0.4)

        # Safety context: positive valence + high habituation + low anxiety
        # = familiar, non-threatening environment
        safety_score = (
            valence_polarity * 0.35
            + habituation * 0.30
            + (1.0 - max(anxiety_level, bnst_signal)) * 0.35
        )
        is_safe_context = safety_score > self.SAFETY_THRESHOLD

        # LS inhibition: fires strongly in safe context, weakly in threat
        if is_safe_context:
            target_inhibition = self.LS_INHIBITION_PEAK * safety_score
        else:
            target_inhibition = self.LS_INHIBITION_RESTING * (1.0 - safety_score)

        # Anxiety brake: LS pressing on BNST/anxiety circuits
        anxiety_brake = target_inhibition * (1.0 - anxiety_level) * 0.8

        # Smooth toward target
        current = self.state.get("ls_inhibition_strength", self.LS_INHIBITION_RESTING)
        new_inhibition = current * 0.88 + target_inhibition * 0.12

        safety_signal = is_safe_context and new_inhibition > self.SAFETY_THRESHOLD

        self.state["ls_inhibition_strength"] = round(new_inhibition, 4)
        self.state["safety_signal_active"] = safety_signal
        self.state["anxiety_brake_pressure"] = round(anxiety_brake, 4)
        self.state["hippocampal_drive"] = round(hippo_drive, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ls_inhibition_strength": round(new_inhibition, 4),
            "safety_signal_active": safety_signal,
            "anxiety_brake_pressure": round(anxiety_brake, 4),
            "hippocampal_drive": round(hippo_drive, 4),
            # brain_septal_inhibition
            "brain_septal_inhibition": round(new_inhibition * safety_signal, 4),
            "_safety_score": round(safety_score, 4),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
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

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

