"""
REMAtoniaController — Subcoeruleus REM sleep atonia mechanism

Neural substrate: Subcoeruleus (SubC) / Sublaterodorsal nucleus (SLD)
Location: Pons
Function: Glycinergic/GABAergic motor inhibition during REM sleep;
          suppresses spinal motoneurons via magnocellular reticular formation.

Key neurotransmitters:
  - Glycine: primary inhibitory neurotransmitter for motor atonia (spinal cord)
  - GABA: co-released with glycine, general brainstem inhibition
  - Acetylcholine: REM-on cells (PPT/LDT) excite SubC during REM
  - Serotonin (raphe): REM-off signal; suppresses SubC during waking

Pathology: Loss of orexin (narcolepsy-cataplexy) allows REM intrusion into waking —
           unopposed SubC activity during consciousness produces cataplexy.

CITATIONS:
    PMC7896014 — Uchida S, Soya S, Saito YC et al. (2021). A Discrete Glycinergic Neuronal
        Population in the Ventromedial Medulla That Induces Muscle Atonia During REM Sleep
        and Cataplexy. J Neurosci.
    PMC5043043 — Arrigoni E, Chen MC, Fuller PM (2016). The Anatomical, Cellular and
        Synaptic Basis of Motor Atonia During REM Sleep. Nat Rev Neurosci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class REMAtoniaController(BrainMechanism):
    """
    Models Subcoeruleus (SubC) REM atonia control.

    Drives glycinergic motor suppression during REM sleep.
    Pathological activation during waking = cataplexy.
    """

    # Leaky integrator dynamics
    ACCUMULATION_RATE = 0.25   # gain on acetylcholine / sleep drive
    DECAY_RATE = 0.20          # passive decay toward baseline

    # Glycine output gain
    GLYCINE_GAIN = 0.60

    # Motor inhibition gain
    MOTOR_INHIBITION_GAIN = 0.80

    # REM active threshold
    ATONIA_THRESHOLD_FOR_REM = 0.35   # atonia must exceed this to flag REM active
    SEROTONIN_MAX_FOR_REM = 0.40      # serotonin must be below this for REM state

    # Cataplexy thresholds (pathological REM intrusion into waking)
    CATAPLEXY_MOTOR_THRESHOLD = 0.30   # motor command must exceed this
    CATAPLEXY_ATONIA_MIN = 0.15       # atonia must exceed this minimum
    CATAPLEXY_SEROTONIN_MIN = 0.40    # serotonin must be above (still in waking)

    def __init__(self, name: str = "REMAtoniaController",
                 human_analog: str = ("Subcoeruleus — REM sleep atonia, "
                                      "glycinergic motor suppression"),
                 layer: str = "foundational"):
        super().__init__(name=name, human_analog=human_analog, layer=layer)

        # SubC motor atonia state
        self.state["atonia_level"] = 0.05       # baseline low (mostly silent in waking)
        self.state["glycine_release"] = 0.05     # glycine output to spinal cord
        self.state["rem_active"] = False         # REM sleep flag
        self.state["cataplexy_signal"] = 0.0     # pathological REM intrusion
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        """
        Compute REM atonia state for this tick.

        Inputs expected (from prior_results):
          - CholinergicREMOn:  float [0.0–1.0] — cholinergic drive from PPT/LDT
          - VLPOSleepActive:   float [0.0–1.0] — GABAergic sleep drive from VLPO
          - DorsalRaphe:       float [0.0–1.0] — serotonin level (REM-off)
          - MotorCommand:      float [0.0–1.0] — premotor command (cataplexy trigger)

        Outputs:
          - atonia_level:           float [0.0–1.0]
          - glycine_release:        float [0.0–1.0]
          - rem_active:             bool
          - cataplexy_signal:       float [0.0–1.0]
          - motor_inhibition_strength: float [0.0–1.0]
        """
        self.state["tick_count"] += 1

        # --- Extract inputs ---
        rem_drive   = float(input_data.get("prior_results", {}).get("CholinergicREMOn", {}).get("output", 0.0))
        sleep_drive = float(input_data.get("prior_results", {}).get("VLPOSleepActive", {}).get("output", 0.0))
        serotonin   = float(input_data.get("prior_results", {}).get("DorsalRaphe", {}).get("output", 0.0))
        motor_cmd   = float(input_data.get("prior_results", {}).get("MotorCommand", {}).get("output", 0.0))

        # Clamp inputs to [0,1]
        rem_drive   = max(0.0, min(1.0, rem_drive))
        sleep_drive = max(0.0, min(1.0, sleep_drive))
        serotonin   = max(0.0, min(1.0, serotonin))
        motor_cmd   = max(0.0, min(1.0, motor_cmd))

        # --- 1. Atonia level — leaky integrator ---
        # Rise driven by acetylcholine (rem_drive) + GABA (sleep_drive)
        # Suppressed by serotonin (wake_override signal from dorsal raphe)
        prior_atonia = float(self.state["atonia_level"])
        wake_override = serotonin  # serotonin inhibits SubC
        drive = (rem_drive + sleep_drive) / 2.0  # combined REM+sleep excitation
        excitation = drive * self.ACCUMULATION_RATE
        # Net change: accumulate excitation, subtract decay and wake suppression
        delta = excitation - (self.DECAY_RATE * prior_atonia) - (wake_override * 0.25)
        atonia_level = prior_atonia + delta
        atonia_level = max(0.0, min(1.0, atonia_level))

        # --- 2. Glycine release — proportional to atonia level ---
        glycine_release = atonia_level * self.GLYCINE_GAIN
        glycine_release = max(0.0, min(1.0, glycine_release))

        # --- 3. REM active flag ---
        # REM is considered active when atonia is above threshold AND serotonin is low
        rem_active = bool(atonia_level > self.ATONIA_THRESHOLD_FOR_REM and serotonin < self.SEROTONIN_MAX_FOR_REM)

        # --- 4. Cataplexy signal — pathological REM intrusion into waking ---
        # Occurs when motor commands arrive but SubC atonia is still partially active
        # (orexin loss allows REM mechanisms to intrude into wakefulness)
        if (motor_cmd > self.CATAPLEXY_MOTOR_THRESHOLD
                and atonia_level > self.CATAPLEXY_ATONIA_MIN
                and serotonin > self.CATAPLEXY_SEROTONIN_MIN):
            # Proportional to motor drive and residual atonia
            cataplexy_signal = atonia_level * motor_cmd
            cataplexy_signal = min(1.0, cataplexy_signal)
        else:
            cataplexy_signal = 0.0

        # --- 5. Motor inhibition strength ---
        motor_inhibition_strength = atonia_level * self.MOTOR_INHIBITION_GAIN
        motor_inhibition_strength = max(0.0, min(1.0, motor_inhibition_strength))

        # --- Update persistent state ---
        self.state["atonia_level"] = atonia_level
        self.state["glycine_release"] = glycine_release
        self.state["rem_active"] = rem_active
        self.state["cataplexy_signal"] = cataplexy_signal
        self.state["motor_inhibition_strength"] = motor_inhibition_strength

        self.persist_state()

        # --- Return outputs ---
        return {
            "atonia_level": atonia_level,
            "glycine_release": glycine_release,
            "rem_active": rem_active,
            "cataplexy_signal": cataplexy_signal,
            "motor_inhibition_strength": motor_inhibition_strength,
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

