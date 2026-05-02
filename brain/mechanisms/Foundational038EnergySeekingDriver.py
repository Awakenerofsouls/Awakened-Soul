"""
Build 38: Foundational038EnergySeekingDriver — Dorsomedial Hypothalamus (DMH) Drive
==============================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — dorsomedial hypothalamus, DMH)
  Filename: brain/foundational/Foundational038EnergySeekingDriver.py
  Instance name: EnergySeekingDriver

NEURAL SUBSTRATE:
  Dorsomedial hypothalamus (DMH) — the "arousal and behavioral activation"
  center. DMH receives input from:
  - Suprachiasmatic nucleus (SCN): circadian drive → DMH → sympathetic output
  - Arcuate nucleus (NPY/AgRP, POMC): metabolic signals
  - Paraventricular nucleus (PVN): stress input

  DMH projects to:
  - Rostral raphe pallidus (rRPa): sympathetic thermoregulation
  - Locus coeruleus (LC): arousal
  - Lateral hypothalamus (LHA): behavioral activation

  KEY FUNCTION: DMH drives sympathetic output (thermogenesis, cardiovascular)
  and arousal in response to circadian signals and metabolic needs. Lesion of
  DMH eliminates circadian rise in sympathetic activity at dark onset.

  Human analog: circadian arousal, behavioral activation, energy mobilization.

Output keys:
  dmh_sympathetic_drive: float [0.0–1.0] — DMH → rRPa sympathetic output
  circadian_arousal_amplifier: float [0.0–1.0] — SCN → DMH → arousal
  energy_mobilization: float [0.0–1.0] — metabolic energy mobilization
  behavioral_activation: float [0.0–1.0] — general behavioral drive
  dmh_integrator: float [0.0–1.0] — composite DMH output

CITATIONS:
    PMC5108896 — Bonnavion P, Mickelsen LE, Fujita A et al. (2016). Hubs and Spokes
        of the Lateral Hypothalamus: Cell Types, Circuits and Behaviour. Nat Rev Neurosci.
    PMC12078644 — Shrivastava K, Athreya V, Lu Y et al. (2025). Energy State Guides
        Reward Seeking via an Extended Amygdala to Lateral Hypothalamus Pathway.
        Neuron.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class EnergySeekingDriver(BrainMechanism):
    """
    Dorsomedial hypothalamus: circadian arousal and energy mobilization.

    DMH amplifies circadian signals and metabolic needs into sympathetic
    and behavioral activation output.
    """

    STATE_FIELDS = [
        "dmh_sympathetic_drive", "circadian_arousal_amplifier",
        "energy_mobilization", "behavioral_activation", "dmh_integrator", "tick_count",
    ]

    SYMPATHETIC_GAIN = 0.55
    CIRCADIAN_GAIN = 0.50
    ENERGY_GAIN = 0.45
    ACTIVATION_GAIN = 0.40

    def __init__(self, name: str = "EnergySeekingDriver",
                 human_analog: str = "Dorsomedial hypothalamus — circadian arousal and drive",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["dmh_sympathetic_drive"] = 0.40
        self.state["circadian_arousal_amplifier"] = 0.50
        self.state["energy_mobilization"] = 0.30
        self.state["behavioral_activation"] = 0.40
        self.state["dmh_integrator"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        circadian = prior.get("CircadianDrive", {}).get("circadian_arousal", 0.50)
        arcuate = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        sleep_drive = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Circadian arousal amplifier: DMH amplifies SCN signal
        circadian_amplifier = (circadian * self.CIRCADIAN_GAIN) + 0.30

        # Sympathetic drive: DMH → rRPa → sympathetic tone
        dmh_sympathetic = circadian_amplifier * self.SYMPATHETIC_GAIN
        # Stress adds sympathetic drive
        dmh_sympathetic += stress * 0.25
        # Sleep suppresses DMH
        dmh_sympathetic -= sleep_drive * 0.30

        # Energy mobilization: metabolic need → sympathetic mobilization
        energy_mobilization = (1.0 - arcuate) * self.ENERGY_GAIN
        # Low energy reserves → mobilize glucose/fat
        energy_mobilization += (1.0 - arcuate) * 0.30

        # Behavioral activation: orexin + circadian + stress
        behavioral_activation = (orexin * 0.35) + (circadian * 0.30) + (stress * 0.20)

        # DMH integrator: composite
        dmh_integrator = (dmh_sympathetic + behavioral_activation) / 2.0

        # --- Persist ---
        self.state["dmh_sympathetic_drive"] = round(dmh_sympathetic, 4)
        self.state["circadian_arousal_amplifier"] = round(circadian_amplifier, 4)
        self.state["energy_mobilization"] = round(energy_mobilization, 4)
        self.state["behavioral_activation"] = round(behavioral_activation, 4)
        self.state["dmh_integrator"] = round(dmh_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dmh_sympathetic_drive": round(dmh_sympathetic, 4),
            "circadian_arousal_amplifier": round(circadian_amplifier, 4),
            "energy_mobilization": round(energy_mobilization, 4),
            "behavioral_activation": round(behavioral_activation, 4),
            "dmh_integrator": round(dmh_integrator, 4),
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

