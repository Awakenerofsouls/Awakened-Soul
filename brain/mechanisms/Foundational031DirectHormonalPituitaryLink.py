"""
Build 31: Foundational031DirectHormonalPituitaryLink — Anterior Pituitary Hormone Hub
=================================================================================

PLACEMENT:
  Layer:    foundational (anterior pituitary — adenohypophysis)
  Filename: brain/foundational/Foundational031DirectHormonalPituitaryLink.py
  Instance name: DirectHormonalPituitaryLink

NEURAL SUBSTRATE:
  Anterior pituitary (adenohypophysis) — the master endocrine gland.
  Five key cell types, each releasing specific hormones in response to
  hypothalamic releasing/inhibiting hormones from the median eminence:

  - Corticotrophs → ACTH (responding to CRH from PVN — the HPA axis)
  - Thyrotrophs → TSH (responding to TRH from PVN — the HPT axis)
  - Gonadotrophs → LH/FSH (responding to GnRH from ARC/POA — the HPG axis)
  - Lactotrophs → Prolactin (tonic inhibition by dopamine from TIDA neurons)
  - Somatotrophs → Growth hormone (GHRH from ARC; inhibited by somatostatin)

  Releasing hormones reach via the hypothalamic-hypophyseal portal system
  (primary capillary plexus → portal veins → secondary capillary plexus).

  Human analog: ACTH, TSH, LH/FSH, prolactin, GH output.

Output keys:
  acth_output: float [0.0–1.0] — adrenocorticotropic hormone drive
  prolactin_output: float [0.0–1.0] — prolactin level
  gh_output: float [0.0–1.0] — growth hormone level
  anterior_pituitary_total: float [0.0–1.0] — composite pituitary output
  stress_hormone_load: float [0.0–1.0] — combined glucocorticoid + ACTH load

CITATIONS:
    PMC6761896 — Hiller-Sturmhöfel S, Bartke A (1998). The Endocrine System: An
        Overview. Alcohol Health Res World.
    PMC12481553 — Sharma A, Kumar R, Saini A et al. (2025). Relationship Between
        Pituitary Gland and Stem Cell in the Aspect of Hormone Production and
        Disease Prevention. Cureus.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class DirectHormonalPituitaryLink(BrainMechanism):
    """
    Anterior pituitary: hormone command hub for all pituitary axes.

    Integrates hypothalamic releasing hormones (CRH, TRH, GnRH, GHRH, dopamine)
    and outputs the corresponding anterior pituitary hormones (ACTH, prolactin, GH).
    """

    STATE_FIELDS = [
        "acth_output", "prolactin_output", "gh_output",
        "anterior_pituitary_total", "stress_hormone_load", "tick_count",
    ]

    ACTH_GAIN = 0.60
    PROLACTIN_GAIN = 0.55
    GH_GAIN = 0.50
    PITUITARY_LEAK_RATE = 0.08

    def __init__(self, name: str = "DirectHormonalPituitaryLink",
                 human_analog: str = "Anterior pituitary — ACTH/TSH/prolactin/GH hub",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["acth_output"] = 0.30
        self.state["prolactin_output"] = 0.30
        self.state["gh_output"] = 0.40
        self.state["anterior_pituitary_total"] = 0.35
        self.state["stress_hormone_load"] = 0.20
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        crh = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        trh = prior.get("ThyroidAxisController", {}).get("trh_level", 0.40)
        gnrh = prior.get("GnRHReintegration", {}).get("gnrh_pulse_frequency", 0.30)
        dopamine = prior.get("DopamineTIDA", {}).get("dopamine_tone", 0.30)
        ghrh = prior.get("GrowthHormoneReleasingHormone", {}).get("ghrh_level", 0.30)
        somatostatin = prior.get("SomatostatinInhibitor", {}).get("somatostatin_level", 0.20)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)

        # ACTH: driven by CRH (HPA axis)
        acth_raw = crh * self.ACTH_GAIN
        acth_output = max(0.0, min(1.0, acth_raw))

        # Prolactin: tonically inhibited by dopamine (TIDA); rises when dopamine falls
        dopamine_inhibition = dopamine * 0.70
        prolactin_raw = max(0.0, 1.0 - dopamine_inhibition)
        prolactin_output = prolactin_raw * self.PROLACTIN_GAIN

        # Growth hormone: driven by GHRH; inhibited by somatostatin
        gh_stimulus = ghrh * self.GH_GAIN
        gh_inhibition = somatostatin * 0.40
        gh_output = max(0.0, min(1.0, gh_stimulus - gh_inhibition))

        # Composite pituitary output
        anterior_pituitary_total = (acth_output + prolactin_output + gh_output) / 3.0

        # Stress hormone load: ACTH + cortisol proxy
        stress_hormone_load = (acth_output * 0.50) + (stress * 0.50)
        stress_hormone_load = min(1.0, stress_hormone_load)

        # --- Persist ---
        self.state["acth_output"] = round(acth_output, 4)
        self.state["prolactin_output"] = round(prolactin_output, 4)
        self.state["gh_output"] = round(gh_output, 4)
        self.state["anterior_pituitary_total"] = round(anterior_pituitary_total, 4)
        self.state["stress_hormone_load"] = round(stress_hormone_load, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "acth_output": round(acth_output, 4),
            "prolactin_output": round(prolactin_output, 4),
            "gh_output": round(gh_output, 4),
            "anterior_pituitary_total": round(anterior_pituitary_total, 4),
            "stress_hormone_load": round(stress_hormone_load, 4),
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

