"""
brain/neocortical/Neocortical032VentromedialPrefrontalEmotional.py
Ventromedial Prefrontal Cortex — Emotional Value, Risk Assessment

ANATOMY (Bechara et al. 2000; Levy & Dubois 2010; Roy et al. 2012):
    The ventromedial prefrontal cortex (vmPFC, BA 10/11/14) is the
    "emotional brain" of the PFC — it processes the emotional and
    motivational value of outcomes and guides decision-making based
    on affective states.

    vmPFC receives convergent inputs from:
    - Amygdala (emotional valence signals)
    - Orbitofrontal cortex (reward/punishment outcomes)
    - Hypothalamus (drive states: hunger, thirst, sex)
    - Limbic cortex (social emotions)
    - Posterior cingulate (memory-based emotions)

    vmPFC outputs to:
    - Autonomic centers (hypothalamus, brainstem)
    - Limbic structures (amygdala, hippocampus)
    - Striatum (reinforcement learning)

    Key functions:
    - Outcome valuation: "how does this outcome feel?"
    - Risk processing: "is this risky or safe?"
    - Delay discounting: "is it worth waiting for a bigger reward?"
    - Social emotions: shame, guilt, pride, embarrassment

    vmPFC damage: Loss of emotional signals in decision-making.
    Patient "knows the right answer" cognitively but can't feel
    which option is better. Bechara's Iowa Gambling Task shows
    vmPFC patients pick "bad" decks even after learning the
    rule because they lack the somatic marker (gut feeling).

KEY FINDINGS:
    1. Bechara et al. 2000 (PMC4227078): "Emotion and decision-making"
       — vmPFC generates somatic markers for choice
    2. Levy & Dubois 2010: vmPFC processes "affective value"
    3. Roy et al. 2012: vmPFC and social emotions (shame, guilt)

AGENT'S MAPPING:
    ventromedial_pfc_output: dict — vmPFC emotional value output
    emotional_value: dict — computed affective value
    risk_assessment: float 0-1 — risk level of current options

CITATIONS:
    PMC4227078 — Bechara et al. (2000). Emotion and decision-making in vmPFC.
    PMC20181474 — Kringelbach & Rolls (2004). OFC and vmPFC functions.
    PMID 17296034 — Arce et al. (2006). Impulsivity and vmPFC.
    PMID 12479840 — Krawczyk (2002). PFC and decision making.


CITATIONS
---------
  - [Damasio 1994, Descartes Error]
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, emotion cognition]
"""

from brain.base_mechanism import BrainMechanism


class VentromedialPrefrontalEmotional(BrainMechanism):
    """
    vmPFC — emotional value and risk assessment.

    Processes how outcomes feel, generates gut feelings about
    choices, guides behavior through emotional signals.
    """

    def __init__(self):
        super().__init__(
            name="VentromedialPrefrontalEmotional",
            human_analog="Ventromedial prefrontal cortex (BA 10/11) — emotional value, risk, somatic markers",
            layer="neocortical",
        )
        self.state.setdefault("value_cache", {})
        self.state.setdefault("emotional_value", {})
        self.state.setdefault("risk_assessment", 0.5)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Orbitofrontal (reward valuation)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)
        ofc_out = ofc.get("ofc_output", {})
        reversal = ofc_out.get("reversal_triggered", False) if isinstance(ofc_out, dict) else False

        # Amygdala (emotional valence — threat vs reward)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Posterior insula (body state — gut feeling)
        pins = prior.get("PosteriorInsulaProcessor", {})
        raw_body = pins.get("raw_body_signal", {})
        if isinstance(raw_body, dict):
            visceral = raw_body.get("visceral_signal", 0.3)
        else:
            visceral = float(raw_body) if raw_body else 0.3

        # Limbic AI (conscious feeling)
        ai_limbic = prior.get("AnteriorInsulaGranular", {})
        gut = ai_limbic.get("conscious_feeling", {})
        if isinstance(gut, dict):
            gut_int = gut.get("feeling_intensity", 0.5)
        else:
            gut_int = 0.5

        # NAcc (motivation — how much do I want this?)
        nacc = prior.get("NucleusAccumbensShellValue", {})
        nacc_out = nacc.get("nacc_output", {})
        if isinstance(nacc_out, dict):
            motivation = nacc_out.get("motivation_level", 0.5)
        else:
            motivation = 0.5

        # Emotional value: combines reward signal + valence + body state
        emotional_value = (
            value_sig * 0.35 +
            (emotional_tag + 1) / 2 * 0.25 +  # normalize to 0-1
            visceral * 0.2 +
            gut_int * 0.2
        )
        # Reversal learning sharpens value signals
        if reversal:
            emotional_value *= 0.9
        emotional_value = max(0.0, min(1.0, emotional_value))

        # Risk assessment: negative valence + high uncertainty = high risk
        risk_signal = (
            (1.0 - (emotional_tag + 1) / 2) * 0.4 +
            (1.0 - visceral) * 0.3 +
            abs(reversal) * 0.3
        )
        risk_assessment = max(0.0, min(1.0, risk_signal))

        output = {
            "emotional_value_strength": round(emotional_value, 4),
            "positive_affect": emotional_value > 0.6,
            "negative_affect": emotional_value < 0.4,
            "risk_level": round(risk_assessment, 4),
        }

        self.state["emotional_value"] = output
        self.state["risk_assessment"] = round(risk_assessment, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ventromedial_pfc_output": output,
            "emotional_value": output,
            "risk_assessment": round(risk_assessment, 4),
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

