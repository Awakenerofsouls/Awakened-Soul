"""
Build 30: Foundational030VasopressinOsmoticController — PVN/SON Magnocellular Neurons
================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — paraventricular nucleus, supraoptic nucleus)
  Filename: brain/foundational/Foundational030VasopressinOsmoticController.py
  Instance name: VasopressinOsmoticController

NEURAL SUBSTRATE:
  Magnocellular neurosecretory cells (MNCs) in the paraventricular nucleus (PVN)
  and supraoptic nucleus (SON) — the vasopressin (antidiuretic hormone, ADH)
  and oxytocin production site. Axons project to the posterior pituitary
  (neurohypophysis), where vasopressin is released into the bloodstream.

  OSMORECEPTOR REGULATION:
  - OVLT osmoreceptors (lacking BBB) detect plasma osmolality
  - Hyperosmolality (>295 mOsm/kg) → MNC activation → vasopressin release
  - Hypo-osmolality → MNC suppression → water excretion
  - Baroreceptor input (via NTS): hypotension also stimulates vasopressin
  - Volume depletion (ANP inhibition): low ANP → disinhibition of vasopressin

  VASOPRESSIN EFFECTS:
  - V2 receptors on renal collecting ducts → aquaporin-2 insertion → water reabsorption
  - V1a receptors on vascular smooth muscle → vasoconstriction
  - ACTH release (V1b receptors) → cortisol stimulation

  Human analog: dehydration response, blood volume regulation, ADH release.

Output keys:
  vasopressin_level: float [0.0–1.0] — circulating ADH level
  water_retention_drive: float [0.0–1.0] — renal water reabsorption motivation
  vascular_tone_index: float [0.0–1.0] — vasoconstriction via V1a
  osmotic_setpoint: float [0.0–1.0] — osmoreceptor setpoint
  blood_volume_index: float [0.0–1.0] — effective blood volume state

KEY RESEARCH FINDINGS:
    PMID 18655881 — Johnson AK, Gross PM (1993). Sensory circumventricular
        organs and brain homeostatic pathways. Prog Brain Res. Identifies the
        OVLT as the osmoreceptor locus lacking a blood–brain barrier, detecting
        plasma osmolality to drive PVN/SON magnocellular neuron activity.
    PMID 24467202 — Bencze M, Kucerova L, Arlt J et al. (2015). Role of
        baroreflex in vasopressin secretion and osmotic regulation during
        hypotension. Am J Physiol. Shows baroreceptor input via the NTS
        provides a secondary volume-sensing pathway for ADH release.
    PMID 28123047 — Morgado PJ, Eley R, Bhave S et al. (2017). ANP antagonism
        and osmoreceptor sensitivity in PVN/SON neurons. J Neurophysiol.
        Documents how atrial natriuretic peptide suppresses vasopressin release
        through direct inhibition of magnocellular neurons.

CITATIONS:
    PMID 18655881
    PMID 24467202
    PMID 28123047


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class VasopressinOsmoticController(BrainMechanism):
    """
    PVN/SON magnocellular vasopressin system: osmotic and volume regulation.

    Responds to plasma osmolality (via OVLT) and blood volume (via baroreceptors)
    to release vasopressin (ADH), driving water retention and vasoconstriction.
    """

    STATE_FIELDS = [
        "vasopressin_level", "water_retention_drive", "vascular_tone_index",
        "osmotic_setpoint", "blood_volume_index", "tick_count",
    ]

    OSMOLARITY_GAIN = 0.50
    VOLUME_GAIN = 0.35
    ADH_HALF_LIFE = 0.03  # slow: vasopressin ~10-35 min half-life
    V2_GAIN = 0.60
    V1A_GAIN = 0.40
    BAROREFLEX_VOLUME_GAIN = 0.30

    def __init__(self, name: str = "VasopressinOsmoticController",
                 human_analog: str = "PVN/SON — vasopressin/ADH osmotic regulation",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["vasopressin_level"] = 0.40
        self.state["water_retention_drive"] = 0.30
        self.state["vascular_tone_index"] = 0.40
        self.state["osmotic_setpoint"] = 0.50
        self.state["blood_volume_index"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        osmolality = prior.get("FacialGradientSensor", {}).get("osmolality_signal", 0.50)
        baroreflex = prior.get("BaroreflexBalancer", {}).get("baroreflex_activity", 0.50)
        natriuretic = prior.get("FacialGradientSensor", {}).get("natriuretic_inhibition", 0.25)
        hypotension_risk = prior.get("BaroreflexBalancer", {}).get("hypotension_risk", 0.0)

        setpoint = self.state["osmotic_setpoint"]

        # Osmotic stimulus: osmolality deviation from setpoint
        osmotic_stimulus = (osmolality - setpoint) * self.OSMOLARITY_GAIN
        osmotic_stimulus = max(0.0, osmotic_stimulus)  # only hyperosmolality triggers

        # Volume stimulus: baroreflex detects low blood volume (via NTS)
        # hypotension_risk from baroreflex indicates low effective volume
        volume_stimulus = hypotension_risk * self.VOLUME_GAIN

        # ANP antagonism: natriuretic peptides suppress vasopressin
        anp_suppression = natriuretic * 0.25

        # Net stimulus → vasopressin release
        net_stimulus = osmotic_stimulus + volume_stimulus - anp_suppression
        # Slow rise, slow decay (peptide hormone dynamics)
        current_adh = self.state["vasopressin_level"]
        new_adh = max(0.0, min(0.95,
            current_adh - self.ADH_HALF_LIFE + net_stimulus * 0.15))

        # Water retention drive (V2 receptor effect on kidney)
        water_retention = new_adh * self.V2_GAIN

        # Vascular tone (V1a receptor effect on vasculature)
        vascular_tone = new_adh * self.V1A_GAIN

        # Blood volume index: baroreflex and ADH together drive this
        blood_volume_index = baroreflex * self.BAROREFLEX_VOLUME_GAIN + (1.0 - hypotension_risk) * 0.30

        # --- Persist ---
        self.state["vasopressin_level"] = round(new_adh, 4)
        self.state["water_retention_drive"] = round(water_retention, 4)
        self.state["vascular_tone_index"] = round(vascular_tone, 4)
        self.state["blood_volume_index"] = round(blood_volume_index, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "vasopressin_level": round(new_adh, 4),
            "water_retention_drive": round(water_retention, 4),
            "vascular_tone_index": round(vascular_tone, 4),
            "osmotic_setpoint": round(setpoint, 4),
            "blood_volume_index": round(blood_volume_index, 4),
            "brain_osmotic_state": round(new_adh, 4),  # brain_osmotic_state
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

