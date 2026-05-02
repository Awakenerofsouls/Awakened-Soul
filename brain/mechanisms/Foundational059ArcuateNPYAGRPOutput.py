"""
Build 59: Foundational059ArcuateNPYAGRPOutput — Arcuate NPY/AgRP Hunger System
=========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — arcuate nucleus, NPY/AgRP neurons)
  Filename: brain/foundational/Foundational059ArcuateNPYAGRPOutput.py
  Instance name: ArcuateNPYAGRPOutput

NEURAL SUBSTRATE:
  Arcuate nucleus NPY/AgRP neurons — the orexigenic (hunger) population.
  These neurons are the most potent appetite-stimulators known:
  - NPY (neuropeptide Y): injection into hypothalamus → voracious eating
  - AgRP (agouti-related peptide): antagonist of MC3/4R → blocks α-MSH

  NPY/AgRP NEURONS:
  - Activated by: ghrelin (from stomach), leptin deficiency, fasting
  - Inhibited by: leptin, insulin, α-MSH (negative feedback)
  - Project to: LHA (orexin), PVN (suppress CRH), parabrachial nucleus

  NEURAL CIRCUIT FOR FEEDING:
  Leptin deficiency → ARC NPY/AgRP activated → LHA orexin activated → feeding

  KEY: NPY acts via Y1 and Y5 receptors. AgRP blocks MC4R (melanocortin
  receptor). The MC4R pathway is the final common pathway for energy
  balance — both α-MSH (anorexigenic) and AgRP (orexigenic) compete
  for the same receptor.

  Human analog: ghrelin hunger, NPY-driven hyperphagia, leptin deficiency.

Output keys:
  npy_level: float [0.0–1.0] — NPY output level
  agrp_output: float [0.0–1.0] — AgRP output
  hunger_drive: float [0.0–1.0] — net orexigenic drive
  mc4r_competition: float [-1.0 to 1.0] — AgRP vs α-MSH competition at MC4R
  arcuate_hunger_integrator: float [0.0–1.0] — composite NPY/AgRP output

CITATIONS:
    PMC3467268 — Martins L, Fernández-Mallo D, Novelle MG et al. (2012). Hypothalamic
        mTOR Signaling Mediates the Orexigenic Action of Ghrelin. PLoS ONE.
    PMC4808343 — Cabral A, Portiansky E, Sánchez-Jaramillo E et al. (2016). Ghrelin
        Activates Hypophysiotropic Corticotropin-Releasing Factor Neurons Independently
        of the Arcuate Nucleus. J Neuroendocrinol.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class ArcuateNPYAGRPOutput(BrainMechanism):
    """
    ARC NPY/AgRP: ghrelin hunger, orexigenic drive, MC4R competition.

    Models NPY/AgRP neurons as the arcuate hunger signal.
    """

    STATE_FIELDS = [
        "npy_level", "agrp_output", "hunger_drive",
        "mc4r_competition", "arcuate_hunger_integrator", "tick_count",
    ]

    NPY_GAIN = 0.60
    AGROP_GAIN = 0.55

    def __init__(self, name: str = "ArcuateNPYAGRPOutput",
                 human_analog: str = "Arcuate NPY/AgRP — orexigenic neurons",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["npy_level"] = 0.30
        self.state["agrp_output"] = 0.25
        self.state["hunger_drive"] = 0.30
        self.state["mc4r_competition"] = 0.0
        self.state["arcuate_hunger_integrator"] = 0.30
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        ghrelin = prior.get("GutSignalRelay", {}).get("ghrelin_signal", 0.20)
        leptin = prior.get("EnergyConservationMode", {}).get("energy_reserve_index", 0.50)
        glucose = prior.get("GlucoseMonitor", {}).get("glucose_level", 0.50)
        insulin = prior.get("InsulinSignal", {}).get("insulin_level", 0.30)
        alpha_msh = prior.get("ArcuatePOMCOutput", {}).get("alpha_msh_output", 0.0)
        pomc_inhibition = prior.get("ArcuatePOMCOutput", {}).get("pomc_activity", 0.30)

        # NPY level: activated by ghrelin, leptin deficiency; inhibited by leptin + insulin
        leptin_inhibition = leptin * 0.45
        insulin_inhibition = insulin * 0.30
        glucose_inhibition = glucose * 0.20
        ghrelin_activates = ghrelin * 0.50
        npy_raw = ghrelin_activates - leptin_inhibition - insulin_inhibition - glucose_inhibition
        npy_level = min(1.0, max(0.0, npy_raw))

        # AgRP output: similar activation pattern to NPY
        agrp_raw = ghrelin * 0.45 - leptin * 0.40 - insulin * 0.25
        agrp_output = min(1.0, max(0.0, agrp_raw))

        # Hunger drive: net orexigenic drive
        hunger_drive = (npy_level * 0.50) + (agrp_output * 0.50)

        # MC4R competition: AgRP blocks MC4R; α-MSH activates MC4R
        # Positive = AgRP dominance (hunger); Negative = α-MSH dominance (satiety)
        mc4r_competition = agrp_output - alpha_msh * 0.80
        mc4r_competition = max(-1.0, min(1.0, mc4r_competition))

        # Arcuate hunger integrator
        arcuate_hunger_integrator = (npy_level + agrp_output + hunger_drive) / 3.0

        # --- Persist ---
        self.state["npy_level"] = round(npy_level, 4)
        self.state["agrp_output"] = round(agrp_output, 4)
        self.state["hunger_drive"] = round(hunger_drive, 4)
        self.state["mc4r_competition"] = round(mc4r_competition, 4)
        self.state["arcuate_hunger_integrator"] = round(arcuate_hunger_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "npy_level": round(npy_level, 4),
            "agrp_output": round(agrp_output, 4),
            "hunger_drive": round(hunger_drive, 4),
            "mc4r_competition": round(mc4r_competition, 4),
            "arcuate_hunger_integrator": round(arcuate_hunger_integrator, 4),
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

