"""
Foundational020EnergyConservationMode.py
Arcuate Nucleus (ARC) — Metabolic Energy Homeostasis

Neural substrate: Arcuate nucleus of the hypothalamus.
  - NPY/AgRP neurons: orexigenic (appetite-stimulating), activated by leptin deficiency
  - POMC/CART neurons: anorexigenic (satiety), activated by leptin (satiety signal)
  - Projects to LHA (orexin/hypocretin), PVN (CRH/stress axis), VMH

Key neuropeptides:
  - NPY: most potent orexigenic peptide
  - AgRP: orexigenic, blocks MC4R
  - POMC → α-MSH: satiety signal
  - CART: satiety

Inputs: GlucoseMonitor, LeptinSignal, GhrelinSignal, OrexinLevel, ThyroidAxis
Outputs: energy_reserve_index, orexigenic_drive, anorexigenic_drive,
         energy_expenditure_rate, metabolic_autonomic_index

CITATIONS:
    PMC3111271 — Gao S, Zhu G, Gao X et al. (2011). Important Roles of Brain-Specific
        Carnitine Palmitoyltransferase and Ceramide Metabolism in Leptin Hypothalamic
        Control of Feeding. PLoS ONE.
    PMC3467268 — Martins L, Fernández-Mallo D, Novelle MG et al. (2012). Hypothalamic
        mTOR Signaling Mediates the Orexigenic Action of Ghrelin. PLoS ONE.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class EnergyConservationMode(BrainMechanism):
    """
    Arcuate nucleus (ARC) — primary metabolic sensing and energy homeostasis center.

    Integrates circulating signals: leptin (adipokine from fat), insulin, ghrelin
    (stomach-derived hunger signal), glucose. Controls feeding behavior, energy
    expenditure, and body weight via projections to PVN, LHA, and VMH.
    """

    def __init__(self):
        super().__init__(
            name="EnergyConservationMode",
            human_analog="Arcuate nucleus — metabolic energy homeostasis",
            layer="foundational",
        )
        # Metabolic state variables
        self.state["energy_reserve_index"] = 0.50
        self.state["orexigenic_drive"] = 0.30
        self.state["anorexigenic_drive"] = 0.40
        self.state["energy_expenditure_rate"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        """
        Process metabolic signals and compute homeostatic energy outputs.

        Parameters
        ----------
        input_data : dict
            prior_results from upstream mechanisms:
                - GlucoseMonitor : float [0.0–1.0], default 0.50
                - LeptinSignal   : float [0.0–1.0], default 0.50
                - GhrelinSignal  : float [0.0–1.0], default 0.20
                - OrexinLevel    : float [0.0–1.0], default 0.30
                - ThyroidAxis    : float [0.0–1.0], default 0.50

        Returns
        -------
        dict
            energy_reserve_index      : float [0.0–1.0]
            orexigenic_drive          : float [0.0–1.0]
            anorexigenic_drive        : float [0.0–1.0]
            energy_expenditure_rate   : float [0.0–1.0]
            metabolic_autonomic_index : float [0.0–1.0]
        """
        self.state["tick_count"] += 1

        # ── Parse input signals ────────────────────────────────────────────────
        glucose = float(input_data.get("GlucoseMonitor", {}).get("glucose_level", 0.50))
        leptin  = float(input_data.get("LeptinSignal",   {}).get("leptin_level",  0.50))
        ghrelin = float(input_data.get("GhrelinSignal",  {}).get("ghrelin_level", 0.20))
        orexin  = float(input_data.get("OrexinLevel",    {}).get("orexin_level", 0.30))
        thyroid = float(input_data.get("ThyroidAxis",   {}).get("thyroid_level", 0.50))

        # ── 1. Energy Reserve Index ─────────────────────────────────────────────
        # Composite energy store level. High leptin (adequate fat) and high glucose
        # indicate plentiful reserves; high ghrelin indicates depletion (inverse).
        energy_reserve_index = (
            leptin        * 0.35
            + glucose     * 0.30
            + (1 - ghrelin) * 0.35
        )

        # ── 2. Orexigenic Drive (NPY / AgRP activation) ────────────────────────
        # Driven by leptin deficiency, ghrelin elevation, and low glucose.
        # NPY is the most potent natural orexigenic peptide.
        orexigenic_drive = (
            (1 - leptin)  * 0.40
            + ghrelin     * 0.40
            + (1 - glucose) * 0.20
        )

        # ── 3. Anorexigenic Drive (POMC / CART activation) ─────────────────────
        # Driven by leptin sufficiency, adequate glucose, and low ghrelin.
        # POMC cleaved to α-MSH; CART is an independent satiety peptide.
        anorexigenic_drive = (
            leptin         * 0.50
            + glucose      * 0.30
            + (1 - ghrelin) * 0.20
        )

        # ── 4. Energy Expenditure Rate ─────────────────────────────────────────
        # High orexin (LHA) and thyroid hormone drive expenditure;
        # leptin suppresses it (energy-conserving mode when reserves are low).
        energy_expenditure_rate = (
            orexin         * 0.40
            + thyroid      * 0.30
            + (1 - leptin) * 0.30
        )

        # ── 5. Metabolic Autonomic Index ───────────────────────────────────────
        # Alias of energy_reserve_index; represents the net autonomic metabolic state.
        metabolic_autonomic_index = energy_reserve_index

        # ── State persistence ───────────────────────────────────────────────────
        self.state["energy_reserve_index"]    = energy_reserve_index
        self.state["orexigenic_drive"]         = orexigenic_drive
        self.state["anorexigenic_drive"]       = anorexigenic_drive
        self.state["energy_expenditure_rate"]  = energy_expenditure_rate
        self.persist_state()

        # ── Build output dict ───────────────────────────────────────────────────
        return {
            "energy_reserve_index":    energy_reserve_index,
            "orexigenic_drive":         orexigenic_drive,
            "anorexigenic_drive":       anorexigenic_drive,
            "energy_expenditure_rate":  energy_expenditure_rate,
            "metabolic_autonomic_index": metabolic_autonomic_index,
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

