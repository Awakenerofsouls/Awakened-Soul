"""
brain/neocortical/Neocortical046AssociativeCorticalLongRange.py
Associative Cortical Long-Range Connections — Cross-Region Binding

ANATOMY (Felleman & Van Essen 1991; Barone et al. 2000; Markov et al. 2013):
    Long-range association fibers connect distant cortical regions
    that are not directly adjacent. These are the "highways" of
    abstract thought — linking prefrontal cortex to posterior cortex,
    left hemisphere to right hemisphere, and integrating across
    functional networks.

    Key long-range connections:
    - Arcuate fasciculus: Broca ↔ Wernicke (language)
    - Corpus callosum: left ↔ right hemisphere
    - Extreme capsule: frontal ↔ temporal (semantic)
    - Uncinate fasciculus: PFC ↔ temporal pole (memory/emotion)
    - Fronto-occipital fasciculus: frontal ↔ occipital
    - Cingulum: cingulate ↔ frontal/parahippocampal

    These long-range connections are what makes cortex "integrative" —
    without them, each region would be a local processor. With them,
    the brain can bind distant information into coherent representations.

    Quantitative data (Markov et al. 2013): Only ~1% of cortical
    synapses are from long-range connections, but they are critical
    for higher-order functions.

KEY FINDINGS:
    1. Felleman & Van Essen 1991 (PMC2697346): "Distributed hierarchical
       processing" — long-range connection architecture
    2. Markov et al. 2013 (PMC3920108): "Cortical density vs distance"
       — long-range connections are rare but critical
    3. Barone et al. 2000: Long-range feedback connections in cortex

AGENT'S MAPPING:
    long_range_output: dict — long-range association output
    association_strength: float 0-1 — strength of cross-region binding
    binding_achieved: bool — have distant regions been bound?

CITATIONS:
    PMC2697346 — Felleman & Van Essen (1991). Hierarchical processing.
    PMC3920108 — Markov et al. (2013). Long-range cortical connectivity.
    PMC3000199 — Larsson (2010). Visual processing and long-range connections.


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Felleman 1991, Cereb Cortex 1:1, cortical hierarchy]
  - [Markram 2004, Nat Rev Neurosci 5:793, interneurons]
"""

from brain.base_mechanism import BrainMechanism


class AssociativeCorticalLongRange(BrainMechanism):
    """
    Long-range association — cross-region binding for abstract thought.

    Connects distant cortical regions to form unified, abstract
    representations across the whole brain.
    """

    def __init__(self):
        super().__init__(
            name="AssociativeCorticalLongRange",
            human_analog="Long-range association fibers — cross-region binding, abstract thought",
            layer="neocortical",
        )
        self.state.setdefault("association_paths", [])
        self.state.setdefault("association_strength", 0.0)
        self.state.setdefault("binding_achieved", False)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Layer II/III associator (upper layer association activity)
        layer23 = prior.get("LayerIIIIIAssociator", {})
        associator_out = layer23.get("layer_ii_iii_output", {})
        if isinstance(associator_out, dict):
            associator_sig = associator_out.get("association_strength", 0.5)
        else:
            associator_sig = 0.5

        # Layer I (cross-region integration)
        layer1 = prior.get("LayerIMolecularIntegrator", {})
        cross_region = layer1.get("cross_region_binding", 0.5)

        # DLPFC (cognitive control — when to bind distant regions)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Angular gyrus (semantic binding — connects language to meaning)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # Anterior insula (salience — when does binding need to happen?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # mPFC (self-narrative — binds across self-related content)
        mpfc = prior.get("MedialPrefrontalSelfReflection", {})
        mpfc_sig = mpfc.get("self_referential_signal", 0.5)

        # Association strength: when associator + cross-region + semantic are all active
        association_strength = (
            associator_sig * 0.25 +
            cross_region * 0.2 +
            sem_bind * 0.25 +
            cognitive_ctrl * 0.2 +
            mpfc_sig * 0.1
        )
        if salience > 0.6:
            association_strength *= (1.0 + (salience - 0.6) * 0.4)
        association_strength = max(0.0, min(1.0, association_strength))

        binding_achieved = association_strength > 0.55

        # Record association path
        if binding_achieved:
            self.state["association_paths"].append(round(association_strength, 3))
            if len(self.state["association_paths"]) > 5:
                self.state["association_paths"].pop(0)

        self.state["association_strength"] = round(association_strength, 4)
        self.state["binding_achieved"] = binding_achieved
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "long_range_output": {
                "association_strength": round(association_strength, 4),
                "binding_achieved": binding_achieved,
            },
            "association_strength": round(association_strength, 4),
            "binding_achieved": binding_achieved,
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
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

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

