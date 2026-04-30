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
  - [Boutilier 2001, J Exp Biol 204:3171]
  - [Sokoloff 1996, Brain Energy Metabolism]
  - [Sterling 2012, Physiol Behav 106:5, doi:10.1016/j.physbeh.2011.06.004]
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
            name="EnergyConservationMode_EnergyConservationMode",
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

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out

    # ---------- enrichment helpers (phase-2 expansion) ----------
    def attribute_signature(self) -> tuple:
        out = []
        for attr_name in sorted(dir(self)):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            out.append((attr_name, type(v).__name__))
        return tuple(out)

    def numeric_attribute_values(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[attr_name] = float(v)
        return out

    def list_attribute_lengths(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, list):
                out[attr_name] = len(v)
        return out

    def boolean_attributes(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, bool):
                out[attr_name] = v
        return out

    def callable_method_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                out.append(attr_name)
        return out

    def has_attribute(self, name: str) -> bool:
        return hasattr(self, name) and not name.startswith("_")

    def safe_get(self, name: str, default=None):
        try:
            v = getattr(self, name, default)
            return v
        except Exception:
            return default

    def history_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                out.append(attr_name)
        return out

    def total_history_length(self) -> int:
        total = 0
        for attr_name in self.history_attribute_names():
            v = getattr(self, attr_name, None)
            if isinstance(v, list):
                total += len(v)
        return total

    def is_initialized(self) -> bool:
        return getattr(self, "tick_count", 0) >= 0

    def class_metadata(self) -> dict:
        return {
            "name": self.__class__.__name__,
            "module": self.__class__.__module__,
            "n_attrs": self.attribute_count() if hasattr(self, "attribute_count") else 0,
            "n_history": len(self.history_attribute_names()),
        }

    def state_size(self) -> int:
        try:
            return len(self.export_state())
        except Exception:
            return 0


