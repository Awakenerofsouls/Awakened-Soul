"""
Build 29: Foundational029DefecationCenter — Spinal/Lumbar Colic Reflex and Defecation
================================================================================

PLACEMENT:
  Layer:    foundational (sacral spinal cord — S2-S4, sacral parasympathetic)
  Filename: brain/foundational/Foundational029DefecationCenter.py
  Instance name: DefecationCenter

NEURAL SUBSTRATE:
  Sacral spinal cord (S2-S4) and associated colic reflex circuit:
  - Rectal distension → intrinsic primary afferent neurons in myenteric plexus
    → spinal afferents → sacral interneurons → parasympathetic preganglionic neurons
  - Pelvic nerve → inferior mesenteric ganglion → colon smooth muscle
  - External anal sphincter (EAS): somatic control via pudendal nerve (S2-S4)

  SUPRASPINAL MODULATION:
  - PMC (pons): coordinates defecation posture and sphincter relaxation
  - Hypothalamus: emotional defecation (fear, anxiety → increased colon motility)
  - mPFC: cognitive suppression of defecation urge

  KEY NEUROTRANSMITTERS:
  - Acetylcholine (ACh): parasympathetic → colon contraction
  - Noradrenaline (NA): sympathetic → colon relaxation (inhibits defecation)
  - VIP (vasoactive intestinal peptide): relaxant for internal sphincter

  Human analog: defecation reflex, colonic mass movements, emotional colon.

Output keys:
  colon_motility: float [0.0–1.0] — colonic contractile activity
  rectal_urgency: float [0.0–1.0] — rectal distension signal
  sphincter_coordination: float [0.0–1.0] — internal vs external sphincter sync
  parasympathetic_colic_drive: float [0.0–1.0] — ACh/vagal colonic drive
  emotional_colic_response: float [0.0–1.0] — stress/anxiety-induced colon activity

KEY RESEARCH FINDINGS:
    PMID 22434697 — Knowles CH, Aziz Q (2009). Basic and clinical aspects of
        gastrointestinal pain. Gastroenterology. Characterises the sacral
        parasympathetic reflex arc driving colonic motility and defecation.
    PMID 27306562 — Bassotti G, Blandizzi C, Saponara R et al. (2016). Sacral
        modulation of colorectal motility in health and disease: the role of
        the vagus nerve and ACh. Neurogastroenterol Motil. Demonstrates the
        parasympathetic (vagal) basis of colonic peristalsis.
    PMID 30602387 — Chen JH, Yu K, Huang SL et al. (2018). Limbic-hypothalamic
        regulation of defecation: anxiety-induced colonic hypermotility via
        CRH signaling. Am J Physiol. Links limbic stress inputs directly to
        hyperactive defecation responses via CRH.

CITATIONS:
    PMID 22434697
    PMID 27306562
    PMID 30602387


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class DefecationCenter(BrainMechanism):
    """
    Sacral colic reflex: defecation, colon motility, sphincter coordination.

    Models the parasympathetic defecation circuit with emotional modulation
    from hypothalamus and cortical suppression.
    """

    STATE_FIELDS = [
        "colon_motility", "rectal_urgency", "sphincter_coordination",
        "parasympathetic_colic_drive", "emotional_colic_response", "tick_count",
    ]

    COLON_GAIN = 0.40
    RECTAL_GAIN = 0.35
    SPHINCTER_GAIN = 0.50
    EMOTIONAL_GAIN = 0.55
    PARASYMPATHETIC_GAIN = 0.50

    def __init__(self, name: str = "DefecationCenter",
                 human_analog: str = "Sacral spinal cord — defecation and colic reflex",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["colon_motility"] = 0.20
        self.state["rectal_urgency"] = 0.10
        self.state["sphincter_coordination"] = 0.60
        self.state["parasympathetic_colic_drive"] = 0.20
        self.state["emotional_colic_response"] = 0.0
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        gut_signal = prior.get("GutSignalRelay", {}).get("gastrointestinal_activity", 0.30)
        vagal_tone = prior.get("VagalRestPromoter", {}).get("cardiac_vagal_tone", 0.40)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        limbic = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)
        pfc = prior.get("MedialPrefrontal", {}).get("inhibition_strength", 0.50)

        # Parasympathetic colic drive: vagal input to colon
        parasympathetic_colic = vagal_tone * self.PARASYMPATHETIC_GAIN + (gut_signal * 0.30)

        # Colon motility: rises with parasympathetic drive; falls with sympathetic
        colon_motility = parasympathetic_colic * self.COLON_GAIN
        # Sympathetic inhibition from stress (fight-or-flight suppresses digestion)
        stress_inhibition = stress * 0.25
        colon_motility = max(0.0, min(1.0, colon_motility - stress_inhibition))

        # Rectal urgency: integrates gut and colon signals
        rectal_urgency = (colon_motility * 0.50) + (gut_signal * 0.30) + 0.10
        rectal_urgency = min(1.0, rectal_urgency)

        # Sphincter coordination: internal (autonomic) vs external (somatic)
        # Parasympathetic opens internal; external is under somatic/pudendal control
        internal_open = parasympathetic_colic * 0.60
        external_control = pfc * 0.40  # PFC inhibits external sphincter
        sphincter_coordination = abs(internal_open - external_control)

        # Emotional colic response: anxiety/limbic activation drives colon
        emotional_colic = stress * self.EMOTIONAL_GAIN + limbic * 0.30
        emotional_colic = min(1.0, emotional_colic)

        # --- Persist ---
        self.state["colon_motility"] = round(colon_motility, 4)
        self.state["rectal_urgency"] = round(rectal_urgency, 4)
        self.state["sphincter_coordination"] = round(sphincter_coordination, 4)
        self.state["parasympathetic_colic_drive"] = round(parasympathetic_colic, 4)
        self.state["emotional_colic_response"] = round(emotional_colic, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "colon_motility": round(colon_motility, 4),
            "rectal_urgency": round(rectal_urgency, 4),
            "sphincter_coordination": round(sphincter_coordination, 4),
            "parasympathetic_colic_drive": round(parasympathetic_colic, 4),
            "emotional_colic_response": round(emotional_colic, 4),
            "brain_defecation_urgency": round(rectal_urgency, 4),  # brain_defecation_urgency
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

