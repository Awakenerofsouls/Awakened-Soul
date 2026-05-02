"""
Build 16: Foundational005DescendingPainGate — Periaqueductal Gray Pain Modulation
================================================================================

PLACEMENT:
  Layer:    foundational (midbrain — PAG periaqueductal gray)
  Filename: brain/foundational/Foundational005DescendingPainGate.py
  Instance name: DescendingPainGate

NEURAL SUBSTRATE:
  Periaqueductal gray (PAG) in the midbrain. Receives affine
  input from hypothalamus, amygdala, and prefrontal cortex.
  Projects to rostral ventromedial medulla (RVM), which in turn
  projects to the spinal dorsal horn to modulate pain transmission
  at the first synapse (the "pain gate"). Two modes:

  - Active coping: lateral/dorsolateral PAG activates RVM
    OFF-cell analgesia → suppresses pain (fight/freeze analgesia).
  - Passive coping: ventrolateral PAG is associated with
    quiescence and pain vocalization — less analgesic output.

  This is the primary mechanism for endogenous pain suppression:
  psychological "threat downregulation" of pain (reappraisal,
  distraction, hypnosis) all act through PAG.

  Key afferents:
    - StressActivationAxis: crh_level (activating PAG analgesia)
    - ValenceTagger: valence_polarity (limbic gating of pain modulation)
    - ArousalRegulator: arousal_level (modulatory state)
  Key efferents:
    - Spinal cord dorsal horn: descending_inhibition (float 0-1)
    - BrainRunner enrichment: pain_gate_status

KEY FINDINGS:
  1. Electrical stimulation of PAG produces profound analgesia
     in humans and animals — equivalent to morphine doses of
     10-15mg/kg — via RVM-spinal pathway (Mayer et al. 1971,
     Science). Blocked by naloxone (confirms opioid involvement).
  2. Placebo analgesia acts through PAG-RVM pathway — conditioned
     expectation activates PAG, which suppresses dorsal horn
     pain transmission (Wager et al. 2004, Science).
  3. Left ventromedial prefrontal cortex (vmPFC) projects to PAG
     and drives top-down pain suppression — vmPFC activity during
     reappraisal predicts analgesic success (Wiech et al. 2008,
     J Neurosci).
  4. Chronic pain is associated with PAG dysfunction — failed
     PAG-RVM descending inhibition is found in chronic migraine,
     fibromyalgia, and irritable bowel syndrome (Tracey 2010,
     Nature Reviews Neuroscience).
  5. CeA (central amygdala) projects directly to PAG — emotional
     context modulates analgesia: high fear/valence suppresses PAG
     analgesic efficacy (Bandler & Shipley 1994, Neurobiology).

INPUTS (prior_results):
  - StressActivationAxis: crh_level (float 0-1)
  - ValenceTagger: valence_polarity (float -1 to +1)
  - ArousalRegulator: arousal_level (float 0-1)
  - Homeostat: dominant_drive (str)

OUTPUTS:
  - descending_inhibition: float 0.0-1.0 (RVM-spinal analgesic drive)
  - gate_status: str ("open" | "partially_gated" | "closed")
  - active_coping_mode: bool (lateral PAG activated)
  - pain_suppression_efficacy: float 0.0-1.0 (real-world analgesic potency)

CITATIONS:
    PMC11412428 — Vázquez-León P, Miranda-Páez A, Valencia-Flores K et al. (2023).
        Defensive and Emotional Behavior Modulation by Serotonin in the Periaqueductal Gray.
        Biomolecules.
    PMC11395413 — Liang D, Labrakakis C (2024). Multiple Posterior Insula Projections
        to the Brainstem Descending Pain Modulatory System. J Neurosci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class DescendingPainGate(BrainMechanism):
    """
    Periaqueductal gray — descending pain modulatory system.

    PAG-RVM-spinal pathway is the primary endogenous analgesic
    system. Activated by threat downregulation (reappraisal,
    safety signals, active coping) and suppressed by emotional
    distress.
    """

    # Pain gate thresholds
    FULL_INHIBITION_THRESHOLD = 0.65   # above this → near-complete analgesia
    PARTIAL_INHIBITION_THRESHOLD = 0.30  # above this → partial analgesia
    GATE_OPEN = 0.10                    # at or below this → gate open (pain transmits)

    # Active coping boost
    ACTIVE_COPING_BOOST = 0.25

    # Naloxone sensitivity (opioid component ~40% of PAG analgesia)
    OPIOID_FRACTION = 0.40

    def __init__(self):
        super().__init__(
            name="DescendingPainGate",
            human_analog=(
                "Periaqueductal gray — descending pain modulatory system, "
                "PAG-RVM-spinal analgesic pathway"
            ),
            layer="foundational",
        )
        self.state.setdefault("descending_inhibition", 0.0)
        self.state.setdefault("gate_status", "open")
        self.state.setdefault("active_coping_mode", False)
        self.state.setdefault("pain_suppression_efficacy", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ---- Inputs ----
        crh_level = prior.get("StressActivationAxis", {}).get("crh_level", 0.0)
        valence_polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.0)
        arousal_level = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "stability")

        # ---- Valence gating: negative valence (distress) suppresses PAG ----
        # Positive safety signals potentiate PAG analgesia
        valence_score = valence_polarity * 0.30

        # ---- Arousal modulation ----
        # Moderate arousal facilitates active coping; hypoarousal does not
        arousal_modulation = (arousal_level - 0.5) * 0.20

        # ---- Active coping drive boost ----
        active_coping_drives = {"curiosity", "expression", "connection"}
        active_coping_mode = dominant_drive in active_coping_drives
        active_coping_boost = self.ACTIVE_COPING_BOOST if active_coping_mode else 0.0

        # ---- CRH: acute stress activates PAG analgesia (defense reaction) ----
        # Paradoxically, CRH activates PAG → RVM analgesia during active coping
        crh_activation = crh_level * 0.30

        # ---- Net descending inhibition ----
        net_inhibition = (
            crh_activation
            + valence_score
            + arousal_modulation
            + active_coping_boost
        )
        net_inhibition = max(0.0, min(1.0, net_inhibition))
        net_inhibition = round(net_inhibition, 4)

        # ---- Gate status ----
        if net_inhibition > self.FULL_INHIBITION_THRESHOLD:
            gate_status = "closed"
        elif net_inhibition > self.PARTIAL_INHIBITION_THRESHOLD:
            gate_status = "partially_gated"
        elif net_inhibition > self.GATE_OPEN:
            gate_status = "partially_gated"
        else:
            gate_status = "open"

        # ---- Pain suppression efficacy ----
        # Real-world efficacy: PAG analgesia produces ~60-80% pain reduction at max
        pain_suppression_efficacy = net_inhibition * 0.80
        pain_suppression_efficacy = round(pain_suppression_efficacy, 4)

        # Persist
        self.state["descending_inhibition"] = net_inhibition
        self.state["gate_status"] = gate_status
        self.state["active_coping_mode"] = active_coping_mode
        self.state["pain_suppression_efficacy"] = pain_suppression_efficacy
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "descending_inhibition": net_inhibition,
            "gate_status": gate_status,
            "active_coping_mode": active_coping_mode,
            "pain_suppression_efficacy": pain_suppression_efficacy,
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

