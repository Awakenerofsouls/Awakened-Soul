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
