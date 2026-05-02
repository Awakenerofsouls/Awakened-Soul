"""
Build 41: Foundational041DefensiveReproductiveLink — HPA-HPG Axis Competition
=========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — PVN interaction with ARC/POA)
  Filename: brain/foundational/Foundational041DefensiveReproductiveLink.py
  Instance name: DefensiveReproductiveLink

NEURAL SUBSTRATE:
  HPA-HPG interaction: stress suppresses reproduction at multiple levels.
  CRH directly inhibits GnRH release from hypothalamus. Cortisol acts on
  the pituitary to suppress LH/FSH. High cortisol also suppresses
  kisspeptin neurons (the GnRH "gatekeeper") via glucocorticoid receptors.

  Conversely, reproductive hormones modulate stress reactivity:
  - Testosterone attenuates HPA axis responses
  - Estrogen can enhance or suppress depending on phase of menstrual cycle

  KEY NEUROANATOMY:
  - PVN (CRH) → suppresses ARC kisspeptin → reduces GnRH → ↓ LH/FSH
  - PVN → suppresses POA → reduced sexual behavior
  - Testosterone → suppresses PVN CRH → reduced stress response

  Human analog: stress-induced infertility, sexual dysfunction under chronic stress.

Output keys:
  hpa_hpg_tradeoff: float [0.0–1.0] — stress-reproduction allocation
  reproductive_suppression: float [0.0–1.0] — HPA inhibition of reproduction
  stress_attenuation: float [0.0–1.0] — reproductive hormone stress buffering
  defensive_priority: float [0.0–1.0] — survival over reproduction priority
  survival_reproduction_balance: float [0.0–1.0] — axis allocation

CITATIONS:
    PMC7687061 — Esteban Masferrer M, Silva BA, Nomoto K et al. (2020). Differential
        Encoding of Predator Fear in the Ventromedial Hypothalamus and Periaqueductal Grey.
        J Neurosci.
    PMC4379496 — Kunwar PS, Zelikowsky M, Remedios R et al. (2015). Ventromedial
        Hypothalamic Neurons Control a Defensive Emotion State. eLife.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class DefensiveReproductiveLink(BrainMechanism):
    """
    HPA-HPG tradeoff: stress suppresses reproduction; reproduction buffers stress.

    Models the competition between survival (HPA) and reproductive (HPG) axes.
    """

    STATE_FIELDS = [
        "hpa_hpg_tradeoff", "reproductive_suppression", "stress_attenuation",
        "defensive_priority", "survival_reproduction_balance", "tick_count",
    ]

    SUPPRESSION_GAIN = 0.60
    ATTENUATION_GAIN = 0.40
    DEFENSIVE_GAIN = 0.55

    def __init__(self, name: str = "DefensiveReproductiveLink",
                 human_analog: str = "HPA-HPG interaction — stress vs reproduction",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["hpa_hpg_tradeoff"] = 0.30
        self.state["reproductive_suppression"] = 0.10
        self.state["stress_attenuation"] = 0.30
        self.state["defensive_priority"] = 0.40
        self.state["survival_reproduction_balance"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        crh = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        cortisol = prior.get("AutonomicSecretionLink", {}).get("cortisol_level", 0.40)
        gnrh = prior.get("GnRHReintegration", {}).get("gnrh_pulse_frequency", 0.30)
        lh = prior.get("GnRHReintegration", {}).get("lh_output", 0.25)
        testosterone = prior.get("TestosteroneSignal", {}).get("testosterone_level", 0.50)
        estrogen = prior.get("EstrogenSignal", {}).get("estrogen_level", 0.40)

        # HPA-HPG tradeoff: how much stress suppresses reproduction
        stress_suppression = crh * self.SUPPRESSION_GAIN + cortisol * 0.30
        reproductive_suppression = min(1.0, stress_suppression)

        # Stress attenuation: reproductive hormones buffer stress
        testosterone_attenuation = testosterone * self.ATTENUATION_GAIN * 0.50
        estrogen_attenuation = estrogen * self.ATTENUATION_GAIN * 0.30
        stress_attenuation = max(0.0, min(1.0,
            testosterone_attenuation + estrogen_attenuation))

        # Defensive priority: survival over reproduction
        defensive_priority = (crh * self.DEFENSIVE_GAIN + cortisol * 0.30) * 0.50

        # HPA-HPG tradeoff: balance between axes
        hpa_drive = crh + cortisol
        hpg_drive = gnrh + lh + testosterone + estrogen
        total_drive = hpa_drive + hpg_drive
        if total_drive > 0:
            tradeoff = hpa_drive / total_drive  # 0 = full HPG, 1 = full HPA
        else:
            tradeoff = 0.5
        hpa_hpg_tradeoff = min(1.0, tradeoff)

        # Survival-reproduction balance
        balance = 0.50 - (defensive_priority * 0.30) + (stress_attenuation * 0.30)
        survival_reproduction_balance = min(1.0, max(0.0, balance))

        # --- Persist ---
        self.state["hpa_hpg_tradeoff"] = round(hpa_hpg_tradeoff, 4)
        self.state["reproductive_suppression"] = round(reproductive_suppression, 4)
        self.state["stress_attenuation"] = round(stress_attenuation, 4)
        self.state["defensive_priority"] = round(defensive_priority, 4)
        self.state["survival_reproduction_balance"] = round(survival_reproduction_balance, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "hpa_hpg_tradeoff": round(hpa_hpg_tradeoff, 4),
            "reproductive_suppression": round(reproductive_suppression, 4),
            "stress_attenuation": round(stress_attenuation, 4),
            "defensive_priority": round(defensive_priority, 4),
            "survival_reproduction_balance": round(survival_reproduction_balance, 4),
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

