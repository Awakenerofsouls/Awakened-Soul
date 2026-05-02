"""
Build 40: Foundational040PortalInterfaceHub — Hypothalamic-Hypophyseal Portal System
===============================================================================

PLACEMENT:
  Layer:    foundational (median eminence — hypothalamic-pituitary portal interface)
  Filename: brain/foundational/Foundational040PortalInterfaceHub.py
  Instance name: PortalInterfaceHub

NEURAL SUBSTRATE:
  Hypothalamic-hypophyseal portal system — the vascular link between
  hypothalamus and anterior pituitary:
  1. Primary capillary plexus (median eminence) — receives releasing hormones
  2. Portal veins — carry blood directly to secondary capillary plexus
  3. Secondary capillary plexus (anterior pituitary) — hormone release

  This portal system is a "short-loop" vascular connection that ensures
  high local concentrations of hypothalamic hormones at the pituitary,
  with minimal systemic spillover.

  KEY FEATURES:
  - Blood flow is primarily downward (hypothalamus → pituitary)
  - Some retrograde flow allows pituitary feedback to hypothalamus
  - Portal vessels have fenestrated endothelium (no BBB here)

  Human analog: portal circulation, endocrine signal transmission.

Output keys:
  portal_flow_strength: float [0.0–1.0] — portal blood flow rate
  rh_transmission_fidelity: float [0.0–1.0] — RH signal transmission quality
  anterior_pituitary_activation: float [0.0–1.0] — pituitary stimulation level
  portal_leakage: float [0.0–1.0] — systemic spillover of RH signals
  endocrine_permissiveness: float [0.0–1.0] — portal gate openness

CITATIONS:
    PMC8332811 — Kelly WM, Kucharczyk W, Kucharczyk J et al. (1988). Posterior
        Pituitary Ectopia: An MR Feature of Pituitary Dwarfism. Am J Neuroradiol.
    PMC4251598 — Sarkar DK, Frautschy SA, Mitsugi N (1992). Pituitary Portal Plasma
        Levels of Oxytocin During the Estrous Cycle, Lactation, and Hyperprolactinemia.
        Endocrinology.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class PortalInterfaceHub(BrainMechanism):
    """
    Hypothalamic-hypophyseal portal system interface.

    Models the portal vascular connection, transmission fidelity,
    and feedback dynamics between hypothalamus and pituitary.
    """

    STATE_FIELDS = [
        "portal_flow_strength", "rh_transmission_fidelity",
        "anterior_pituitary_activation", "portal_leakage",
        "endocrine_permissiveness", "tick_count",
    ]

    FLOW_GAIN = 0.55
    FIDELITY_GAIN = 0.60
    ACTIVATION_GAIN = 0.50

    def __init__(self, name: str = "PortalInterfaceHub",
                 human_analog: str = "Hypothalamic-hypophyseal portal system",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["portal_flow_strength"] = 0.50
        self.state["rh_transmission_fidelity"] = 0.60
        self.state["anterior_pituitary_activation"] = 0.40
        self.state["portal_leakage"] = 0.05
        self.state["endocrine_permissiveness"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        releasing = prior.get("ReleasingHormoneHub", {}).get(
            "releasing_hormone_composite", 0.40
        )
        crh = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        trh = prior.get("ThyroidAxisController", {}).get("trh_level", 0.40)
        gnrh = prior.get("GnRHReintegration", {}).get("gnrh_pulse_frequency", 0.30)
        acth = prior.get("DirectHormonalPituitaryLink", {}).get("acth_output", 0.30)
        cortisol = prior.get("AutonomicSecretionLink", {}).get("cortisol_level", 0.40)
        sleep_signal = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Portal flow: driven by hypothalamic activity; suppressed during sleep
        base_flow = releasing * self.FLOW_GAIN
        sleep_suppression = sleep_signal * 0.50
        portal_flow = max(0.0, min(1.0, base_flow - sleep_suppression))

        # RH transmission fidelity: high during active releasing, low during sleep
        rh_fidelity = (releasing * 0.50) + 0.30

        # Anterior pituitary activation: sum of all pituitary axes
        pituitary_input = (crh * 0.30) + (trh * 0.25) + (gnrh * 0.25) + (acth * 0.20)
        anterior_activation = pituitary_input * self.ACTIVATION_GAIN

        # Portal leakage: when portal pressure is high, some RH escapes to systemic
        portal_leakage = releasing * 0.10 + cortisol * 0.05

        # Endocrine permissiveness: cortisol feedback reduces portal gate openness
        cortisol_inhibition = cortisol * 0.30
        permissiveness = max(0.0, min(1.0, 0.70 - cortisol_inhibition))

        # --- Persist ---
        self.state["portal_flow_strength"] = round(portal_flow, 4)
        self.state["rh_transmission_fidelity"] = round(rh_fidelity, 4)
        self.state["anterior_pituitary_activation"] = round(anterior_activation, 4)
        self.state["portal_leakage"] = round(portal_leakage, 4)
        self.state["endocrine_permissiveness"] = round(permissiveness, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "portal_flow_strength": round(portal_flow, 4),
            "rh_transmission_fidelity": round(rh_fidelity, 4),
            "anterior_pituitary_activation": round(anterior_activation, 4),
            "portal_leakage": round(portal_leakage, 4),
            "endocrine_permissiveness": round(permissiveness, 4),
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

