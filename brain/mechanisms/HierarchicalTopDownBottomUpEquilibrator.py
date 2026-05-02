"""
HierarchicalTopDownBottomUpEquilibrator — Predictive Coding Hierarchy

NEURAL SUBSTRATE
================
Predictive coding (Friston 2009; Rao & Ballard 1999) is the dominant
theoretical framework for cortical hierarchy. Each cortical level
maintains a generative model of the level below, sends DOWN predictions
(via deep-layer feedback projections, beta band), and receives UP
prediction-errors from the level below (via superficial-layer
feedforward, gamma band — Bastos 2015).

The equilibrium between top-down predictions and bottom-up errors is
modulated by precision weighting: when prior precision is high, the
brain trusts the prediction even with conflicting input (perceptual
illusion, expectation effects). When sensory precision is high, the
brain updates the prediction (perceptual learning, surprise-driven
attention).

This mechanism reads the relative strength of top-down + bottom-up
streams (from NetworkOscillationGlobalBalancer) and emits an
equilibrium signal indicating which mode dominates. Critically, it
also detects FAILURE modes:
- Stuck top-down (hallucinations, schizophrenia priors)
- Stuck bottom-up (sensory overload, autism, ADHD attention)
- Healthy oscillation between the two (typical perception)

Friston 2010 ("The free-energy principle") generalized this to a
single computational principle: the brain minimizes prediction error
across its hierarchy, and the equilibrium is the rolling balance of
that minimization.

KEY FINDINGS
============
1. Predictive coding: cortex implements hierarchical generative model with top-down predictions and bottom-up prediction errors — [Rao RP 1999, Nat Neurosci 2:79, doi:10.1038/4580]
2. Free-energy principle unifies brain function: minimize prediction error / surprise across hierarchical model — [Friston K 2010, Nat Rev Neurosci 11:127, doi:10.1038/nrn2787]
3. Visual cortex frequency channels: gamma feedforward (errors), beta feedback (predictions); canonical predictive-coding implementation — [Bastos AM 2015, Neuron 85:390, doi:10.1016/j.neuron.2014.12.018]
4. Active inference framework: action + perception minimize free energy via the same predictive hierarchy — [Friston KJ 2017, Network Neurosci 1:381, doi:10.1162/NETN_a_00018]
5. Hierarchical predictive coding implementation in laminar cortical microcircuit; layer-specific feedforward/feedback — [Bastos AM 2012, Neuron 76:695, doi:10.1016/j.neuron.2012.10.038]

INPUTS (from prior_results)
============================
- NetworkOscillationGlobalBalancer.top_down_signal
- NetworkOscillationGlobalBalancer.bottom_up_signal
- NetworkOscillationGlobalBalancer.ei_balance
- DorsolateralPrefrontalCortex.dlpfc_drive (top-down precision arbiter)
- ValenceTagger.valence_intensity (surprise/PE proxy)

OUTPUTS (to brain_runner enrichment)
=====================================
- equilibrium_signal (0-1) — 0 = stuck top-down, 1 = stuck bottom-up
- prediction_error_total (0-1) — accumulated unresolved PE
- top_down_dominance (0-1)
- bottom_up_dominance (0-1)
- precision_arbitration (0-1) — current weighting on priors vs evidence
- equilibrium_state (str): "balanced" | "top_down_locked" |
  "bottom_up_overload" | "updating" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class HierarchicalTopDownBottomUpEquilibrator(BrainMechanism):
    """Predictive-coding equilibrium between top-down and bottom-up."""

    SMOOTH = 0.20
    LOCK_THRESHOLD = 0.65
    OVERLOAD_THRESHOLD = 0.65

    def __init__(self):
        super().__init__(
            name="HierarchicalTopDownBottomUpEquilibratorVariant",
            human_analog="Predictive-coding equilibrator (Friston 2010)",
            layer="integration",
        )
        self.state.setdefault("equilibrium_signal", 0.5)
        self.state.setdefault("prediction_error_total", 0.0)
        self.state.setdefault("top_down_dominance", 0.0)
        self.state.setdefault("bottom_up_dominance", 0.0)
        self.state.setdefault("precision_arbitration", 0.5)
        self.state.setdefault("equilibrium_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _equilibrium(self, top_down: float, bottom_up: float) -> float:
        """0.0 = pure top-down, 1.0 = pure bottom-up, 0.5 = balanced."""
        total = top_down + bottom_up
        if total < 0.10:
            return 0.5
        return max(0.0, min(1.0, bottom_up / total))

    def _precision(self, dlpfc: float, intensity: float) -> float:
        """Precision arbitration — DLPFC top-down gain vs surprise.
        High DLPFC = trust priors. High surprise = trust evidence."""
        return min(1.0, dlpfc * 0.5 + (1.0 - intensity) * 0.5)

    def _pe_total(self, prev: float, equilibrium: float,
                    intensity: float) -> float:
        """Running unresolved prediction error total."""
        # PE accumulates when bottom-up dominates AND surprise persists
        if equilibrium > 0.60 and intensity > 0.30:
            return min(1.0, prev * 0.95 + intensity * 0.10)
        # Resolves when balanced
        if 0.35 < equilibrium < 0.65:
            return max(0.0, prev * 0.92)
        return prev

    def _classify_state(self, equilibrium: float, top_down: float,
                          bottom_up: float, pe_total: float) -> str:
        if top_down < 0.10 and bottom_up < 0.10:
            return "quiet"
        if equilibrium < 0.30 and top_down > self.LOCK_THRESHOLD:
            return "top_down_locked"
        if equilibrium > 0.70 and bottom_up > self.OVERLOAD_THRESHOLD:
            return "bottom_up_overload"
        if pe_total > 0.30 and equilibrium > 0.55:
            return "updating"
        if 0.30 <= equilibrium <= 0.70:
            return "balanced"
        return "balanced"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        osc_data = prior.get("NetworkOscillationGlobalBalancer", {})
        top_down = float(osc_data.get("top_down_signal", 0.0))
        bottom_up = float(osc_data.get("bottom_up_signal", 0.0))

        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        dlpfc = float(dlpfc_data.get("dlpfc_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))

        equilibrium_target = self._equilibrium(top_down, bottom_up)
        prev_eq = float(self.state.get("equilibrium_signal", 0.5))
        equilibrium = self._smooth(prev_eq, equilibrium_target)

        precision_target = self._precision(dlpfc, intensity)
        prev_prec = float(self.state.get("precision_arbitration", 0.5))
        precision = self._smooth(prev_prec, precision_target)

        prev_pe = float(self.state.get("prediction_error_total", 0.0))
        pe_total = self._pe_total(prev_pe, equilibrium, intensity)

        state = self._classify_state(equilibrium, top_down, bottom_up,
                                       pe_total)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["equilibrium_signal"] = round(equilibrium, 4)
        self.state["prediction_error_total"] = round(pe_total, 4)
        self.state["top_down_dominance"] = round(top_down, 4)
        self.state["bottom_up_dominance"] = round(bottom_up, 4)
        self.state["precision_arbitration"] = round(precision, 4)
        self.state["equilibrium_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "equilibrium_signal": round(equilibrium, 4),
            "prediction_error_total": round(pe_total, 4),
            "top_down_dominance": round(top_down, 4),
            "bottom_up_dominance": round(bottom_up, 4),
            "precision_arbitration": round(precision, 4),
            "equilibrium_state": state,
        }

    def _hallucination_susceptibility(self, recent: list) -> float:
        """Sustained top_down_locked = hallucination/delusion proxy
        (Friston 2017 active inference)."""
        if not recent:
            return 0.0
        win = recent[-50:]
        l = sum(1 for s in win if s == "top_down_locked")
        return l / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "equilibrium": self.state.get("equilibrium_signal", 0.5),
            "pe_total": self.state.get("prediction_error_total", 0.0),
            "precision": self.state.get("precision_arbitration", 0.5),
            "state": self.state.get("equilibrium_state", "quiet"),
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

