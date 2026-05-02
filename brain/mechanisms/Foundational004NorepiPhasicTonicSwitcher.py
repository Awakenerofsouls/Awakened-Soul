"""
Build 15: Foundational004NorepiPhasicTonicSwitcher — LC NE Phasic/Tonic Mode Switching
======================================================================================

PLACEMENT:
  Layer:    foundational (pontine — locus coeruleus)
  Filename: brain/foundational/Foundational004NorepiPhasicTonicSwitcher.py
  Instance name: NorepiPhasicTonicSwitcher

NEURAL SUBSTRATE:
  Locus coeruleus (LC) norepinephrine system with explicit
  phasic vs tonic firing mode switching. Aston-Jones and Cohen
  (2005) established that LC operates in two modes:

  - Phasic mode: low tonic (1-2 Hz), burst firing to task-relevant
    stimuli. Optimal for exploitation, focused attention,
    behavioral switching. Associated with moderate arousal.

  - Tonic mode: elevated tonic (3-5 Hz), irregular firing, reduced
    phasic response to stimuli. Optimal for exploration, broad
    scanning, sustained engagement. Associated with high or
    variable arousal.

  Mode switching is driven by task demands, uncertainty, and
  arousal. The LC is the same mechanism as ArousalRegulator — but
  ArousalRegulator models arousal_level (continuous) while this
  models the discrete MODE SHIFT between phasic and tonic operational
  states. They are complementary.

  This mechanism reads arousal from ArousalRegulator, task
  uncertainty from PredictionErrorDrift, and outputs the active
  LC mode plus mode-specific gain parameters.

KEY FINDINGS:
  1. Phasic mode: LC fires 10-15 Hz bursts 100-300ms AFTER stimuli.
     Amplitude of burst is proportional to stimulus salience.
     Tonic firing is suppressed during bursts (Aston-Jones et al.
     1999, Biol Psychiatry).
  2. Tonic mode: LC fires at 3-5 Hz continuously. Baseline
     elevation is 50-100% above phasic baseline. Phasic bursts
     are smaller but more frequent (Rajkowski et al. 2004, Ann NY Acad Sci).
  3. Uncertainty drives phasic→tonic shift: unpredictable task
     contexts elevate tonic LC firing and suppress phasic bursts
     (Dayan & Yu 2006, Neural Networks).
  4. Phasic LC mode is optimal for: cue detection, task switching,
     focused attention under low uncertainty. Tonic mode is optimal
     for: vigilance, sustained monitoring, exploration (Usher
     et al. 1999, Science).
  5. Orbitofrontal cortex and anterior cingulate project to LC and
     control mode switching — top-down task set determines which
     mode LC uses (Cohen et al. 2002, Cereb Cortex).

INPUTS (prior_results):
  - ArousalRegulator: arousal_level (float 0-1), mode (str)
  - PredictionErrorDrift: uncertainty (float 0-1), surprise_magnitude (float 0-1)
  - Homeostat: dominant_drive (str)

OUTPUTS:
  - lc_mode: str ("phasic" | "tonic")
  - phasic_gain: float 1.0-2.5 (burst amplitude multiplier)
  - tonic_baseline: float 0.3-0.8 (baseline NE level)
  - mode_confidence: float 0.0-1.0 (confidence in current mode classification)

CITATIONS:
    PMC9099715 — Osorio-Forero A, Cherrad N, Banterle L et al. (2022). When the Locus
        Coeruleus Speaks Up in Sleep: Recent Insights, Emerging Perspectives.
        Int J Mol Sci.
    PMC3174240 — Carter ME, Yizhar O, Chikahisa S et al. (2010). Tuning Arousal with
        Optogenetic Modulation of Locus Coeruleus Neurons. Nat Neurosci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class NorepiPhasicTonicSwitcher(BrainMechanism):
    """
    LC-NE phasic/tonic mode switching.

    Explicit mode classifier for locus coeruleus operational state.
    Phasic = burst/exploitative; Tonic = sustained/exploratory.
    Complementary to ArousalRegulator (which tracks arousal level).
    """

    # Thresholds
    UNCERTAINTY_TONIC_THRESHOLD = 0.52  # above this → tonic mode
    AROUSAL_TONIC_THRESHOLD = 0.72     # very high arousal → tonic
    AROUSAL_HYPO_THRESHOLD = 0.25      # very low arousal → phasic (drowsy LC)

    # Mode confidence
    MODE_SWITCH_CONF = 0.65  # confidence required to switch mode
    MODE_HYSTERESIS = 0.04  # threshold offset to prevent oscillation

    def __init__(self):
        super().__init__(
            name="NorepiPhasicTonicSwitcher",
            human_analog=(
                "Locus coeruleus — phasic/tonic norepinephrine mode switching, "
                "Aston-Jones & Cohen adaptive gain theory"
            ),
            layer="foundational",
        )
        self.state.setdefault("lc_mode", "phasic")
        self.state.setdefault("mode_confidence", 0.5)
        self.state.setdefault("phasic_gain", 1.8)
        self.state.setdefault("tonic_baseline", 0.45)
        self.state.setdefault("tick_count", 0)

    def _compute_mode_score(self, uncertainty: float, arousal: float,
                            drive: str) -> float:
        """
        Compute evidence for TONIC mode.
        Returns positive = evidence for tonic, negative = evidence for phasic.
        """
        # Uncertainty pushes toward tonic
        uncertainty_score = (uncertainty - 0.5) * 2 * 0.40

        # High arousal pushes toward tonic
        arousal_score = (arousal - 0.50) * 1.6 * 0.25

        # Drive-based adjustment
        if drive == "curiosity":
            # Curiosity/exploration → tonic (sustained monitoring)
            drive_score = 0.20
        elif drive == "stability":
            # Stability → phasic (routine, focused)
            drive_score = -0.10
        elif drive == "rest":
            # Rest → phasic (low activity, drowsy)
            drive_score = -0.15
        else:
            drive_score = 0.0

        return uncertainty_score + arousal_score + drive_score

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ---- Input readings ----
        arousal_level = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        uncertainty = prior.get("PredictionErrorDrift", {}).get("uncertainty", 0.3)
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")

        # ---- Compute mode score ----
        mode_score = self._compute_mode_score(uncertainty, arousal_level, dominant_drive)

        # Extreme thresholds override mode score
        if arousal_level > self.AROUSAL_TONIC_THRESHOLD:
            mode_score = max(mode_score, 0.20)
        elif arousal_level < self.AROUSAL_HYPO_THRESHOLD:
            mode_score = min(mode_score, -0.20)

        # ---- Hysteresis: require confidence above threshold to switch ----
        prev_mode = self.state["lc_mode"]
        prev_confidence = self.state["mode_confidence"]
        mode_confidence = prev_confidence + abs(mode_score) * 0.15
        mode_confidence = min(1.0, mode_confidence)

        if mode_confidence > self.MODE_SWITCH_CONF:
            if mode_score > self.MODE_HYSTERESIS:
                new_mode = "tonic"
            elif mode_score < -self.MODE_HYSTERESIS:
                new_mode = "phasic"
            else:
                new_mode = prev_mode
        else:
            new_mode = prev_mode

        # ---- Compute gain parameters per mode ----
        if new_mode == "phasic":
            # Phasic: lower baseline, higher burst gain
            # Surprise increases burst gain within phasic mode
            phasic_gain = 1.8 + surprise * 0.7
            phasic_gain = min(2.5, phasic_gain)
            tonic_baseline = 0.35 + arousal_level * 0.10
        else:
            # Tonic: elevated baseline, reduced burst gain
            phasic_gain = 1.0 + surprise * 0.20
            phasic_gain = max(1.0, phasic_gain)
            tonic_baseline = 0.55 + (arousal_level - 0.5) * 0.30

        phasic_gain = round(phasic_gain, 3)
        tonic_baseline = round(max(0.25, min(0.80, tonic_baseline)), 3)

        # Persist
        self.state["lc_mode"] = new_mode
        self.state["mode_confidence"] = round(mode_confidence, 3)
        self.state["phasic_gain"] = phasic_gain
        self.state["tonic_baseline"] = tonic_baseline
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "lc_mode": new_mode,
            "phasic_gain": phasic_gain,
            "tonic_baseline": tonic_baseline,
            "mode_confidence": round(mode_confidence, 3),
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

