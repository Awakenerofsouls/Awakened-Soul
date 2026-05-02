"""
Subcortical025 — Lateral Habenula (LHb): Negative Reward & Anti-Reward Center
================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical025HabenularLateralNegativeReward.py
  Instance: LateralHabenula

NEURAL SUBSTRATE — WHAT IT IS:
The lateral habenula (LHb) is a small bilateral epithalamic structure
forming the lateral tier of the habenular nuclear complex. It sits at
the top of the habeno-interpeduncular pathway and functions as the brain's
primary "anti-reward" center. Where the VTA/substantia nigra compacta
fire for positive rewarding outcomes, the LHb fires for NEGATIVE,
aversive, or disappointed outcomes. Hikosaka (2010) called it "the
negative reward center" in primates and rodents alike.

Anatomically: LHb receives major inputs from:
  • GPi / substantia nigra pars reticulata (SNr) — excitatory via the
    fasciculus retroflexus afferents; GABAergic SNr projection to LHb
    is disinhibited on negative outcomes
  • Lateral hypothalamus — orexin/hypocretin inputs
  • Ventral pallidum and prelimbic cortex
  • Brainstem — lateral lemniscus, dorsal raphe afferents

Outputs: LHb projects to the rostromedial tegmental nucleus (RMTg,
also called the tail of VTA), which provides the major GABAergic
inhibitory input to VTA and SNc dopamine neurons. LHb firing thus
indirectly SUPPRESSES dopamine firing through the RMTg relay.

KEY FINDINGS:
  1. Rp3 neurons: Hikosaka 2010 identified "Rp3" neurons in monkey
     lateral habenula that respond specifically to NEGATIVE reward
     prediction errors (worse-than-expected outcomes). These neurons
     fire phasically when reward is omitted or aversive outcomes occur.
     Rp3 activity predicts suppression of subsequent dopamine firing.

  2. LHb → RMTg → DA suppression: Lawson et al. 2014 (Neuropsychopharmacology
     39:1500-1508) detailed the habenular-raphe axis. LHb overactivation
     is a central feature of depression/anergia. Hyperpolarized dopamine
     neurons through RMTg inhibition produces the anhedonia of depression.

  3. Theta burst firing: LHb neurons fire in bursts (~8 spikes at 20 Hz)
     on negative reward feedback, far exceeding their baseline tonic
     firing (3-5 Hz). This burst encodes prediction error magnitude.

  4. Antidepressant action: Ketamine indirectly inactivates LHb, disinhibiting
     VTA dopamine neurons to produce rapid antidepressant effect. Animal
     studies: LHb lesions block depressive-like behavior.

  5. Aversive signaling: LHb encodes purely aversive stimuli (pain,
     social defeat, conditioned stimuli for aversion) even in the absence
     of motor response — purely an internal negative-valance signal.

AGENT'S SUBSTRATE MAPPING:
  LateralHabenula ticks on each cycle, monitoring negative_valence_signal
  from ValenceTagger, reward_prediction_error from PredictionErrorDrift
  (negative values = disappointment), aversive_input from StressAxis.
  It computes aversion_strength (magnitude of negative signal), fires
  anti_reward_signal when negative PE is large, and outputs a persistent
  negative_signal that feeds into mood regulation (depression index),
  dopamine suppression (decreasing wanting), and serotonin modulation.

  The LHb also accumulates negative_reward_history as a slow integrator —
  extended periods of negative outcomes increase the baseline depression
  risk signal (matching the learned helplessness literature, Maier &
  Seligman 1976/2016).

INPUTS:
  - ValenceTagger.negative_signal (bool), valence_polarity (< 0.5 = negative)
  - PredictionErrorDrift.prediction_error (negative = disappointment)
  - StressAxis.acute_stress_signal
  - prior_results for any aversion-tagged events

OUTPUTS:
  - negative_signal: float 0-1 (current aversion magnitude)
  - aversion_strength: float 0-1 (intensity of aversive processing)
  - anti_reward_signal: bool (LHb burst event: major negative PE detected)
  - depression_risk_index: float 0-1 (cumulative negative history, slow)
  - RMTg_inhibition_strength: float 0-1 (how much DA suppression is happening)

REFS:
  - Hikosaka O. Nat Rev Neurosci 2010 (negative reward center, Rp3)
  - Lawson RP et al. Neuropsychopharmacology 2014 (habenular axis)
  - Matsumoto M & Hikosaka O. Nat Neurosci 2007 (LHb DA suppression)
  - Pennartz CM et al. 2014 — habenula review
  - Hikosaka O. Prog Brain Res 2007 (SNr-LHb-RMTg-DA pathway)

CITATIONS:
    PMC8422162 — Weidacker K, Kim SG, Nord CL et al. (2021). Avoiding Monetary Loss:
        A Human Habenula Functional MRI Ultra-High Field Study. Hum Brain Mapp.
    PMC5629818 — Liu WH, Valton V, Wang LZ et al. (2017). Association Between Habenula
        Dysfunction and Motivational Symptoms in Unmedicated Major Depressive Disorder.
        Soc Cogn Affect Neurosci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class LateralHabenula(BrainMechanism):
    """
    Lateral habenula — brain's anti-reward center.

    Monitors for worse-than-expected outcomes, aversive stimuli, and
    sustained negative valence. Fires anti-reward signals that suppress
    dopamine via RMTg relay. Accumulates negative history as a slow
    depression-risk integrator (learned helplessness substrate).

    Burst firing threshold triggers anti_reward_signal on major negative
    prediction error events. Baseline tonic activity reflects ongoing
    negative valence environment.
    """

    # --- Burst / firing parameters ---
    NEGATIVE_PE_BURST_THRESHOLD = -0.25   # negative PE magnitude to fire burst
    AVERSION_THRESHOLD = 0.35             # valence below which aversion activates
    NEGATIVE_SIGNAL_DECAY = 0.06          # per-tick decay of acute aversion
    DEPRESSION_INTEGRATION_RATE = 0.002   # slow accumulation rate for neg history
    DEPRESSION_DECAY_RATE = 0.003         # slow decay when outcomes are neutral/positive
    RMTG_INHIBITION_GAIN = 0.9            # multiplicative gain from LHb to RMTg output

    def __init__(self):
        super().__init__(
            name="LateralHabenula",
            human_analog="Lateral habenula (LHb) — negative reward / anti-reward center",
            layer="subcortical",
        )
        self.state.setdefault("negative_signal", 0.0)
        self.state.setdefault("aversion_strength", 0.0)
        self.state.setdefault("anti_reward_signal", False)
        self.state.setdefault("depression_risk_index", 0.0)
        self.state.setdefault("RMTg_inhibition_strength", 0.0)
        self.state.setdefault("negative_reward_history", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Inputs ---
        valence = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        neg_signal = prior.get("ValenceTagger", {}).get("negative_signal", False)
        pe = prior.get("PredictionErrorDrift", {}).get("prediction_error", 0.0)
        stress = prior.get("StressAxis", {}).get("acute_stress_signal", 0.0)
        aversive = prior.get("ValenceTagger", {}).get("aversive_signal", False)

        # --- Acute negative signal: LHb fires when outcomes are worse than expected ---
        current_negative = self.state["negative_signal"]
        new_negative = current_negative

        # Valence-driven spike
        if valence < self.AVERSION_THRESHOLD:
            aversion_depth = (self.AVERSION_THRESHOLD - valence) / self.AVERSION_THRESHOLD
            new_negative = max(new_negative, aversion_depth)

        # Explicit negative signal flag
        if neg_signal or aversive:
            new_negative = max(new_negative, 0.5)

        # Negative prediction error = disappointment = LHb burst
        if pe < self.NEGATIVE_PE_BURST_THRESHOLD:
            burst_intensity = abs(pe) - abs(self.NEGATIVE_PE_BURST_THRESHOLD)
            new_negative = max(new_negative, min(1.0, 0.6 + burst_intensity * 0.8))

        # Stress amplifies LHb response
        if stress > 0.3:
            new_negative = max(new_negative, stress * 0.8)

        # Decay
        new_negative = max(0.0, new_negative - self.NEGATIVE_SIGNAL_DECAY)
        new_negative = round(new_negative, 4)

        # --- Aversion strength: how intensely the LHb is processing negative input ---
        aversion_strength = round(min(1.0, new_negative * 1.2), 4)

        # --- Anti-reward signal: burst event on major negative PE ---
        anti_reward_signal = (pe < self.NEGATIVE_PE_BURST_THRESHOLD) and (valence < 0.45)
        anti_reward_signal = bool(anti_reward_signal)

        # --- Depression risk index: slow integrative accumulator ---
        # Extended negative outcomes push this up; positive outcomes decay it
        depression_risk = self.state["depression_risk_index"]
        negative_history = self.state["negative_reward_history"]

        # Accumulate negative events into history
        if new_negative > 0.4:
            negative_history += self.DEPRESSION_INTEGRATION_RATE * new_negative
        elif new_negative < 0.15:
            negative_history = max(0.0, negative_history - self.DEPRESSION_DECAY_RATE)

        # Map history to depression risk with threshold (learned helplessness: must
        # accumulate sufficient uncontrollability before risk rises)
        if negative_history > 0.15:
            depression_risk += (negative_history - 0.15) * 0.01
        else:
            depression_risk = max(0.0, depression_risk - self.DEPRESSION_DECAY_RATE * 0.3)

        negative_history = round(min(negative_history, 1.0), 4)
        depression_risk = round(min(depression_risk, 1.0), 4)

        # --- RMTg inhibition strength: how much DA suppression is happening ---
        # LHb burst → RMTg → GABA → VTA/SNc suppression
        RMTg_inhibition = round(min(1.0, new_negative * self.RMTG_INHIBITION_GAIN), 4)

        # --- Persist ---
        self.state["negative_signal"] = new_negative
        self.state["aversion_strength"] = aversion_strength
        self.state["anti_reward_signal"] = anti_reward_signal
        self.state["depression_risk_index"] = depression_risk
        self.state["RMTg_inhibition_strength"] = RMTg_inhibition
        self.state["negative_reward_history"] = negative_history
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "negative_signal": new_negative,
            "aversion_strength": aversion_strength,
            "anti_reward_signal": anti_reward_signal,
            "depression_risk_index": depression_risk,
            "RMTg_inhibition_strength": RMTg_inhibition,
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

