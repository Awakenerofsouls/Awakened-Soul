"""
Subcortical021ThalamicLateralPosteriorAssociative.py — Wire 21: ThalamicLPAssociative

Lateral posterior nucleus (LP) and Pulvinar — associative thalamus.

Neural analog: The LP/Pulvinar complex is the largest thalamic nucleus in
humans. It is classified as an "associative" thalamic nucleus — receiving
major input from association cortex (not primary sensory structures) and
sending output to higher-order association cortex. It integrates information
across sensory modalities and cognitive systems.

ANATOMY (Halassa & Sherman 2019):
  - LP/Pulvinar receives from: layer 5 of association cortex (parietal,
    temporal, frontal), superior colliculus (visual), retina (via koniocellular
    LGN layers), and cerebellar nuclei
  - LP projects to: posterior parietal cortex (PPC), dorsal visual stream
    areas (MT, MST, areas V3/V4), prefrontal cortex (indirect)
  - Pulvinar subdivisions: lateral (visual attention), inferior (temporal
    integration), anterior (limbic/prefrontal connectivity)

ASSOCIATIVE INTEGRATION:
  LP/Pulvinar is NOT a simple relay — it performs active integration.
  By combining visual-spatial information from superior colliculus,
  cognitive signals from PFC, and timing signals from cerebellum, LP
  generates a unified spatial-cognitive signal for parietal cortex.
  This supports visually-guided attention, spatial awareness,
  and the "where/how" pathway of visual processing.

HALASSA & SHERMAN 2019 — HIGHER-ORDER RELAY:
  LP is the prototype higher-order relay: it receives from layer 5
  association cortex and projects to layer 4 of other association areas.
  This creates the cortico-thalamo-cortical (Cb-Th-Cx) loops that
  support integration across distant cortical regions without going
  through hippocampus or basal ganglia.

VISUAL-SPATIAL + COGNITIVE INTEGRATION:
  1. Visual-spatial: LP receives visual input via SC and association cortex
  2. Cognitive: LP receives working memory and attention signals via PFC
  3. Integration: LP combines these in single-cell firing patterns
  4. Output: LP drives PPC activity to update spatial representation

PULVINAR WEIGHT:
  The pulvinar's influence over cortex (via matrix cells) can be
  measured as "pulvinar_weight" — higher weight means stronger LP-driven
  modulation of cortical activity (attention, spatial更新).

KEY FUNCTIONS:
  1. associative_integration_strength: strength of LP multi-modal integration
  2. visual_cognitive_signal: combined spatial-cognitive output to PPC
  3. pulvinar_weight: strength of LP's influence over cortical matrix

REFS:
- Halassa & Sherman 2019 Neuron 103:7-19 — associative thalamus, higher-order
- Robinson 2016 — pulvinar in attention (separate but related to salience)
- Bender & Youakim 2001 — pulvinar role in visual attention
- Shipp 2003 Brain — pulvinar functional anatomy
- Wilkinson et al. 2000 — LP in spatial attention
- Kaas & Collins 2001 — primate pulvinar evolution

CITATIONS:
    PMC7779422 — Indovina I, Bosco G, Riccelli R et al. (2020). Structural Connectome
        and Connectivity Lateralization of the Multimodal Vestibular Cortical Network.
        Neuroimage.
    PMC2779116 — Willis MW, Benson BE, Ketter TA et al. (2008). Interregional Cerebral
        Metabolic Associativity During a Continuous Performance Task. Hum Brain Mapp.


CITATIONS
---------
  - [Sherman 2002, Phil Trans R Soc Lond B 357:1695, thalamic relay]
  - [Halassa 2017, Nat Neurosci 20:1669, thalamic computation]
  - [Saalmann 2012, Science 337:753, pulvinar attention]
"""

from brain.base_mechanism import BrainMechanism


class ThalamicLateralPosteriorAssociative(BrainMechanism):
    """
    LP/Pulvinar associative thalamus — multi-modal spatial-cognitive relay.

    Integrates visual-spatial information (from SC and visual cortex),
    cognitive signals (from PFC), and timing (from cerebellum) into a
    unified associative signal for posterior parietal cortex.

    LP/Pulvinar is the nexus of spatial awareness and cross-modal
    cognitive integration — the "where/how" thalamic station.
    """

    INTEGRATION_GAIN = 0.75
    VISUAL_WEIGHT = 0.40
    COGNITIVE_WEIGHT = 0.40
    PULVINAR_CORTICAL_GAIN = 0.65
    DECAY_RATE = 0.05

    def __init__(self):
        super().__init__(
            name="ThalamicLateralPosteriorAssociative",
            human_analog="LP/Pulvinar associative thalamus — multi-modal spatial-cognitive",
            layer="subcortical",
        )
        self.state.setdefault("associative_integration_strength", 0.0)
        self.state.setdefault("visual_cognitive_signal", 0.0)
        self.state.setdefault("pulvinar_weight", 0.0)
        self.state.setdefault("visual_input_level", 0.0)
        self.state.setdefault("cognitive_input_level", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source 1: Superior colliculus (visual-spatial/saccadic map)
        sc_signal = prior.get("SuperiorColliculusVisual", {})
        sc_level = sc_signal.get("SC_visual_signal_strength", 0.0)

        # Source 2: Dorsal visual stream (MT/MST area for motion/space)
        dorsal_stream = prior.get("DorsalVisualStream", {})
        dorsal_motion = dorsal_stream.get("motion_signal_strength", 0.0)

        # Source 3: PFC cognitive signals (working memory, attention)
        pfc_signal = prior.get("PrefrontalExecutive", {})
        pfc_cognitive = pfc_signal.get("executive_relay_strength", 0.0)

        # Source 4: MD mediodorsal (PFC-thalamic loop contribution)
        md_signal = prior.get("ThalamicMediodorsalExecutive", {})
        md_cognitive = md_signal.get("executive_relay_strength", 0.0)

        # Source 5: Cerebellar timing (sequence awareness)
        cerebellar = prior.get("DeepCerebellarNucleiOutput", {})
        cerebellar_timing = cerebellar.get("nuclear_output_strength", 0.0)

        # Visual-spatial input: SC + dorsal stream
        visual_input = sc_level * 0.50 + dorsal_motion * 0.50

        # Cognitive input: PFC + MD + cerebellar timing
        cognitive_input = (
            pfc_cognitive * 0.40
            + md_cognitive * 0.35
            + cerebellar_timing * 0.25
        )

        # Associative integration: cross-modal combination
        raw_integration = (
            visual_input * self.VISUAL_WEIGHT
            + cognitive_input * self.COGNITIVE_WEIGHT
        )
        associative_strength = max(
            0.0,
            min(1.0, raw_integration * self.INTEGRATION_GAIN)
        )

        # Visual-cognitive signal: output to PPC and dorsal stream
        visual_cognitive = max(
            0.0,
            min(1.0, associative_strength * 1.2)
        )

        # Pulvinar weight: LP influence over cortical matrix
        # Pulvinar fires proportional to integrated signal strength
        pulvinar_weight = max(
            0.0,
            min(1.0, associative_strength * self.PULVINAR_CORTICAL_GAIN)
        )

        # Decay on low input
        if visual_input < 0.05 and cognitive_input < 0.05:
            associative_strength = max(0.0, associative_strength - self.DECAY_RATE)
            pulvinar_weight = max(0.0, pulvinar_weight - self.DECAY_RATE)
            visual_cognitive = max(0.0, visual_cognitive - self.DECAY_RATE)

        self.state["associative_integration_strength"] = round(associative_strength, 4)
        self.state["visual_cognitive_signal"] = round(visual_cognitive, 4)
        self.state["pulvinar_weight"] = round(pulvinar_weight, 4)
        self.state["visual_input_level"] = round(visual_input, 4)
        self.state["cognitive_input_level"] = round(cognitive_input, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "associative_integration_strength": round(associative_strength, 4),
            "visual_cognitive_signal": round(visual_cognitive, 4),
            "pulvinar_weight": round(pulvinar_weight, 4),
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

