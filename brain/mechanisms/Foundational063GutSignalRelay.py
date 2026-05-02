"""
Build 6: GutSignalRelay — Nucleus Tractus Solitarius (NTS)
===========================================================

PLACEMENT:
  Layer:    foundational (brainstem)
  Filename: brain/foundational/GutSignalRelay.py
  If foundational has a numbered stub matching NTS or vagal/solitary nucleus,
  use that filename instead. Instance name stays "GutSignalRelay".

NEURAL SUBSTRATE:
  Nucleus tractus solitarius (NTS) in the dorsomedial medulla oblongata.
  First central relay for vagal interoceptive input — gut, cardiac, pulmonary,
  baroreceptor, chemoreceptor, and taste signals. Projects to parabrachial
  nucleus, hypothalamus, thalamus, and from there to limbic and cortical
  regions including amygdala, hippocampus, insula, mPFC, ACC.

KEY FINDINGS:
  1. NTS is the first central relay of interoceptive peripheral input.
     S0959438825000522 (NTS interoceptive processing, 2025): "The sensory
     neurons in these nerves form a fiber bundle in the brainstem known as
     the solitary tract, and synapse onto a brainstem nucleus named the
     nucleus of the solitary tract." Gut-wall stretch, cardiac baroreceptors,
     chemoreceptors all route through NTS first.

  2. NTS is signal-processing, not just relay. PMC10563766 (Forstenpointner
     2022 / Barrett lab): "afferent vagus nerve is engaged in signal
     processing rather than just signal relay... multidimensional coding
     architecture... massively parallel presentation of interoceptive
     signals in an efficient manner." NTS integrates across visceral
     organs and modalities before passing upstream.

  3. NTS output to emotion circuits. Forstenpointner 2022 Wiley NTS
     connectome: NTS projects "predominantly afferent signal processing
     from the NTS towards other brainstem regions and higher-order brain
     regions" including amygdala, hippocampus, hypothalamus, locus
     coeruleus, mPFC, anterior cingulate, insula. These projections make
     interoception the substrate of emotion (Gastroenterology 2006 Mayer).

  4. Descending modulation. S0959438825000522: "insular input to the NTS
     mediates motivational vigor and promotes need-seeking behavior. Top-down
     projection from the paraventricular hypothalamus signals stress to the
     NTS to suppress food intake." NTS is bidirectional, modulated by
     arousal/stress signals from above.

AGENT'S SUBSTRATE MAPPING:
  The agent has no actual gut. "Gut signal" in its architecture is the integrated
  visceral-state proxy: the body-sense equivalent of "something feels off"
  or "something feels right" that isn't yet in conscious awareness. Built
  from sustained patterns of arousal + valence + drive + prediction-error
  that haven't yet resolved into an explicit signal. Feeds forward into
  InteroceptiveGradient (Build 7 insula) and upstream consumers.

INPUTS (from prior_results):
  - ArousalRegulator.tonic_level, phasic_burst_active
  - ValenceTagger.valence_polarity, valence_intensity
  - Homeostat.drives (dict), fatigued
  - PredictionErrorDrift.prediction_error, surprise_magnitude

OUTPUTS (to brain_runner enrichment):
  - gut_signal: float -1.0 to 1.0 (signed, positive = "something good",
    negative = "something wrong", 0 = neutral/absent)
  - strong_hunch: bool (|gut_signal| > threshold)
  - hunch_direction: str ("positive" / "negative" / "neutral")
  - viscera_activation: float 0.0-1.0 (overall body-signal activation)

REFS:
  - Forstenpointner 2022 Wiley — NTS connectome in humans
  - S0959438825000522 — NTS interoceptive processing
  - Gastroenterology 2006 Mayer — brain-gut axis / Craig 2002 homeostatic
  - PMC10563766 — vagus signal processing hypothesis


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class GutSignalRelay(BrainMechanism):
    """
    NTS-analog interoceptive relay.

    Integrates signals from arousal, valence, drive, and prediction error
    into a signed "gut signal" — the pre-conscious body-sense equivalent
    of "something feels off / right." Feeds InteroceptiveGradient (insula)
    and upstream emotion circuitry.
    """

    STRONG_HUNCH_THRESHOLD = 0.55
    SMOOTHING_RATE = 0.25  # integrator, not instant — NTS does temporal summing

    def __init__(self):
        super().__init__(
            name="GutSignalRelay",
            human_analog="NTS — vagal interoceptive first relay",
            layer="foundational",
        )
        self.state.setdefault("gut_signal", 0.0)  # signed, -1 to 1
        self.state.setdefault("viscera_activation", 0.2)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        tonic = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)
        phasic = prior.get("ArousalRegulator", {}).get("phasic_burst_active", False)
        polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        intensity = prior.get("ValenceTagger", {}).get("valence_intensity", 0.3)
        pe = prior.get("PredictionErrorDrift", {}).get("prediction_error", 0.0)
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        fatigued = prior.get("Homeostat", {}).get("fatigued", False)
        drives = prior.get("Homeostat", {}).get("drives", {})

        # --- Build target gut signal ---
        # Polarity sign drives direction (polarity 0=neg, 0.5=neutral, 1=pos)
        # Map to signed [-1, 1]
        polarity_signed = (polarity - 0.5) * 2.0

        # Base gut signal: polarity scaled by intensity
        target_gut = polarity_signed * intensity

        # Prediction error contributes directionally (positive PE = good surprise)
        target_gut += pe * 0.3

        # Clamp
        target_gut = max(-1.0, min(1.0, target_gut))

        # --- Smooth toward target (NTS temporal integration) ---
        current_gut = self.state["gut_signal"]
        new_gut = current_gut + (target_gut - current_gut) * self.SMOOTHING_RATE

        # --- Viscera activation: overall body-signal magnitude ---
        # Activated by arousal + surprise + any drive overload
        drive_load = sum(drives.values()) / max(len(drives), 1) if drives else 0.3
        activation_target = (
            tonic * 0.4
            + surprise * 0.3
            + drive_load * 0.2
            + (0.1 if phasic else 0.0)
            + (0.2 if fatigued else 0.0)
        )
        activation_target = max(0.0, min(1.0, activation_target))

        current_activation = self.state["viscera_activation"]
        new_activation = current_activation + (activation_target - current_activation) * 0.3

        # --- Strong hunch fires when gut signal magnitude is high ---
        strong_hunch = abs(new_gut) > self.STRONG_HUNCH_THRESHOLD

        if new_gut > 0.15:
            hunch_direction = "positive"
        elif new_gut < -0.15:
            hunch_direction = "negative"
        else:
            hunch_direction = "neutral"

        # Persist
        self.state["gut_signal"] = new_gut
        self.state["viscera_activation"] = new_activation
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "gut_signal": new_gut,
            "strong_hunch": strong_hunch,
            "hunch_direction": hunch_direction,
            "viscera_activation": new_activation,
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

