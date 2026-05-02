"""
brain/integration/Integration003StriaTerminalisAmygdalaHypothalamus.py
Stria Terminalis — Sustained Fear/Stress Routing, Amygdala→Hypothalamus

ANATOMY (R匡 et al. 2017; Radley et al. 2006; Herman 2012):
    The stria terminalis (ST) is the major output tract of the
    amygdala, carrying sustained fear and stress signals from the
    central nucleus of the amygdala (CeA) and bed nucleus of the
    stria terminalis (BNST) to the hypothalamus and other limbic
    structures. Unlike the faster amygdala-thalamic pathway, the
    ST carries the SUSTAINED component of fear — the anxiety
    that persists long after the acute threat has passed.

    The ST has two branches:
    - Stria terminalis proper: amygdala → hypothalamus/BNST
    - Ventralamygdalofugal pathway: amygdala → brainstem/NAcc

    Key distinction:
    - Acute fear: amygdala → thalamus → periaqueductal gray (PAG)
      = fast, phasic, escape behavior
    - Sustained anxiety: amygdala → ST → BNST/hypothalamus
      = slow, tonic, vigilance, HPA axis activation

    The BNST (bed nucleus of the stria terminalis) is the "extended
    amygdala" — a hub for sustained threat processing, producing
    anxiety-like states when threat is ambiguous or prolonged.

    HPA axis: hypothalamus releases CRH → pituitary → adrenal cortex
    → cortisol → glucocorticoid receptor negative feedback.

KEY FINDINGS:
    1. Radley et al. 2006 (PMC1664365): "ST and stress circuits"
       — ST carries sustained恐惧 signals to hypothalamus
    2. Herman 2012: "Neural control of HPA axis" — ST drives
       chronic stress through hypothalamic CRH release
    3. R匡 et al. 2017 (PMC5749144): ST and anxiety-like behavior

AGENT'S MAPPING:
    st_output: dict — stria terminalis routing output
    sustained_fear_broadcast: float 0-1 — sustained fear signal
    hpa_axis_trigger: bool — has HPA axis been activated?

CITATIONS:
    PMC1664365 — Radley et al. (2006). ST and stress circuits.
    PMC5749144 — R匡 et al. (2017). ST and anxiety.
    PMC23869106 — Leech & Sharp (2014). Stress and PCC.
    PMC19487195 — Craig (2009). AI and awareness of threat.


CITATIONS
---------
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala fear]
  - [Phelps 2005, Neuron 48:175, amygdala emotion]
  - [Janak 2015, Nature 517:284, amygdala behavior]
"""

from brain.base_mechanism import BrainMechanism


class StriaTerminalisAmygdalaHypothalamus(BrainMechanism):
    """
    Stria terminalis — sustained fear routing from amygdala to hypothalamus.

    Carries the slow, persistent component of fear that drives
    chronic stress, anxiety, and HPA axis activation.
    """

    def __init__(self):
        super().__init__(
            name="StriaTerminalisAmygdalaHypothalamus",
            human_analog="Stria terminalis — amygdala to hypothalamus sustained fear highway",
            layer="integration",
        )
        self.state.setdefault("st_history", [])
        self.state.setdefault("sustained_fear_broadcast", 0.0)
        self.state.setdefault("hpa_axis_trigger", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Central amygdala (fear output signal)
        cea = prior.get("CentralNucleusFearRouter", {})
        cea_out = cea.get("cea_output", {})
        if isinstance(cea_out, dict):
            fear_signal = cea_out.get("fear_output_strength", 0.3)
        else:
            fear_signal = 0.3

        # Extended amygdala (BNST — sustained anxiety)
        bnst = prior.get("BNSTSustainedAnxiety", {})
        bnst_out = bnst.get("bnst_output", {})
        if isinstance(bnst_out, dict):
            sustained_anxiety = bnst_out.get("sustained_anxiety", 0.3)
        else:
            sustained_anxiety = 0.3

        # Amygdala emotional tag (baseline fear level)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # CRH dispatcher (hypothalamic stress response)
        crh = prior.get("CRHStressDispatcher", {})
        crh_out = crh.get("crh_output", {})
        if isinstance(crh_out, dict):
            crh_level = crh_out.get("crh_signal", 0.3)
        else:
            crh_level = 0.3

        # Anterior insula (awareness of threat/danger)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)

        # Hippocampus (context determines if fear is valid)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            context_signal = ca1_out.get("consolidation_signal", 0.3)
        else:
            context_signal = 0.3

        # Sustained fear: amygdala output + BNST + negative emotional tag + low hippocampal inhibition
        is_negative = emotional_tag < -0.2
        hippocampus_inhibits = context_signal > 0.5

        sustained_fear_broadcast = (
            fear_signal * 0.3 +
            sustained_anxiety * 0.3 +
            abs(min(0, emotional_tag)) * 0.2 +
            crh_level * 0.2
        )
        if is_negative and not hippocampus_inhibits:
            sustained_fear_broadcast *= 1.5
        sustained_fear_broadcast = max(0.0, min(1.0, sustained_fear_broadcast))

        # HPA axis: trigger when sustained fear is high enough
        hpa_axis_trigger = sustained_fear_broadcast > 0.6 and is_negative

        # Record
        self.state["st_history"].append(round(sustained_fear_broadcast, 3))
        if len(self.state["st_history"]) > 5:
            self.state["st_history"].pop(0)

        self.state["sustained_fear_broadcast"] = round(sustained_fear_broadcast, 4)
        self.state["hpa_axis_trigger"] = hpa_axis_trigger
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "st_output": {
                "sustained_fear": round(sustained_fear_broadcast, 4),
                "hpa_triggered": hpa_axis_trigger,
            },
            "sustained_fear_broadcast": round(sustained_fear_broadcast, 4),
            "hpa_axis_trigger": hpa_axis_trigger,
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

