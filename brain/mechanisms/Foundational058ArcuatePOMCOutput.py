"""
Build 58: Foundational058ArcuatePOMCOutput — Arcuate POMC/CART Satiety System
==========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — arcuate nucleus, POMC neurons)
  Filename: brain/foundational/Foundational058ArcuatePOMCOutput.py
  Instance name: ArcuatePOMCOutput

NEURAL SUBSTRATE:
  Arcuate nucleus POMC neurons — the anorexigenic (satiety) population.
  POMC is cleaved into α-MSH (alpha-melanocyte-stimulating hormone),
  which acts on MC4R receptors in the PVN and LHA to suppress feeding.
  CART (cocaine-and-amphetamine-regulated transcript) is co-released
  and is also anorexigenic.

  POMC NEURONS:
  - Activated by: leptin (via leptin receptors on POMC neurons)
  - Inhibited by: ghrelin (via NPY/AgRP interneurons)
  - Project to: PVN (MC4R → CRH suppression), LHA (suppresses orexin),
    VTA (reward modulation)

  LEPTIN-POMC AXIS:
  High leptin (from adipose tissue) → POMC activation → α-MSH release →
  MC4R activation → satiety → reduced food intake

  Human analog: leptin-mediated satiety, α-MSH appetite suppression.

Output keys:
  pomc_activity: float [0.0–1.0] — POMC neuron firing rate
  alpha_msh_output: float [0.0–1.0] — α-MSH satiety signal
  cart_output: float [0.0–1.0] — CART anorexigenic output
  leptin_sensitivity: float [0.0–1.0] — responsiveness to leptin signal
  satiety_integrator: float [0.0–1.0] — composite satiety output

CITATIONS:
    PMC2838656 — Zheng H, Patterson LM, Rhodes CJ et al. (2010). A Potential Role
        for Hypothalamomedullary POMC Projections in Leptin-Induced Suppression of
        Food Intake. Brain Res.
    PMC8037945 — Jang Y, Heo JY, Lee MJ et al. (2021). Angiopoietin-Like Growth
        Factor Involved in Leptin Signaling in the Hypothalamus. Int J Mol Sci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class ArcuatePOMCOutput(BrainMechanism):
    """
    ARC POMC: α-MSH satiety, CART, leptin-mediated anorexia.

    Models POMC neurons as the arcuate satiety signal.
    """

    STATE_FIELDS = [
        "pomc_activity", "alpha_msh_output", "cart_output",
        "leptin_sensitivity", "satiety_integrator", "tick_count",
    ]

    POMC_GAIN = 0.55
    ALPHA_MSH_GAIN = 0.60
    CART_GAIN = 0.50

    def __init__(self, name: str = "ArcuatePOMCOutput",
                 human_analog: str = "Arcuate POMC — α-MSH satiety neurons",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["pomc_activity"] = 0.40
        self.state["alpha_msh_output"] = 0.35
        self.state["cart_output"] = 0.30
        self.state["leptin_sensitivity"] = 0.50
        self.state["satiety_integrator"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        glucose = prior.get("GlucoseMonitor", {}).get("glucose_level", 0.50)
        ghrelin = prior.get("GutSignalRelay", {}).get("ghrelin_signal", 0.20)
        insulin = prior.get("InsulinSignal", {}).get("insulin_level", 0.30)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)

        # Leptin sensitivity: changes with metabolic state
        # Low leptin (leptin resistance) reduces sensitivity
        leptin_sensitivity = leptin * 0.50 + (1.0 - ghrelin) * 0.30

        # POMC activity: activated by leptin + insulin + glucose
        leptin_activates = leptin * leptin_sensitivity
        insulin_activates = insulin * 0.30
        glucose_activates = glucose * 0.20
        # Ghrelin and stress suppress POMC
        ghrelin_suppresses = ghrelin * 0.30
        stress_suppresses = stress * 0.25
        pomc_raw = leptin_activates + insulin_activates + glucose_activates - ghrelin_suppresses - stress_suppresses
        pomc_activity = min(1.0, max(0.0, pomc_raw))

        # α-MSH output: proportional to POMC activity
        alpha_msh_output = pomc_activity * self.ALPHA_MSH_GAIN

        # CART output: co-released with α-MSH
        cart_output = pomc_activity * self.CART_GAIN

        # Satiety integrator
        satiety_integrator = (alpha_msh_output + cart_output) / 2.0

        # --- Persist ---
        self.state["pomc_activity"] = round(pomc_activity, 4)
        self.state["alpha_msh_output"] = round(alpha_msh_output, 4)
        self.state["cart_output"] = round(cart_output, 4)
        self.state["leptin_sensitivity"] = round(leptin_sensitivity, 4)
        self.state["satiety_integrator"] = round(satiety_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pomc_activity": round(pomc_activity, 4),
            "alpha_msh_output": round(alpha_msh_output, 4),
            "cart_output": round(cart_output, 4),
            "leptin_sensitivity": round(leptin_sensitivity, 4),
            "satiety_integrator": round(satiety_integrator, 4),
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

