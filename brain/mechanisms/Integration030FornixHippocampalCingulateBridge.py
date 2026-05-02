"""
brain/integration/Integration019FornixHippocampalCingulateBridge.py
Fornix — Hippocampal-Cingulate Memory Bridge

ANATOMY (Tsibulski & Amaram 2011; Gloor 1997; O'Leary 2017):
    The fornix is the major output tract of the hippocampus,
    carrying memory signals to the mammillary bodies and
    septal region, and indirectly to the cingulate cortex.
    Its connections form a critical bridge for memory consolidation:

    Fornix connections:
    - Pre-commissural fornix: hippocampus → septal nuclei → cortex
    - Post-commissural fornix: hippocampus → mammillary bodies
    - Crus of fornix: hippocampus → temporal lobe
    - Body:汇聚 from both crura

    The fornix carries theta rhythm from the hippocampus, which
    serves as a timing signal for memory encoding. The septal
    nuclei (fornix target) project cholinergic fibers back to
    the hippocampus, modulating theta generation.

    Damage to the fornix (as in the famous case of patient H.M.)
    produces severe anterograde amnesia — the hippocampus can no
    longer communicate with the rest of the brain to consolidate
    long-term memories.

    The fornix also carries value signals from the septal nuclei
    to the hippocampus, marking which memories are important.

KEY FINDINGS:
    1. Tsibulski & Amaram 2011: "Fornix and memory consolidation"
    2. Gloor 1997: "The fornix in temporal lobe epilepsy"
    3. O'Leary 2017: Fornix development and memory function

AGENT'S MAPPING:
    fornix_output: dict — fornix bridging output
    memory_consolidation_strength: float 0-1 — memory consolidation signal

CITATIONS:
    PMC2830733 — Vann et al. (2009). RSC and episodic memory.
    PMC1852382 — Cavanna & Trimble (2006). PCC and memory.
    PMC23869106 — Leech & Sharp (2014). Memory circuits.

KEY RESEARCH FINDINGS:
    PMID 19641600 — Vann & Albasser (2009). Hippocampal fornix and memory guidance.
    PMID 22365813 — Agster et al. (2012). Fornix and anterior thalamic mammillary circuit.
    PMID 28902393 — Cona et al. (2016). Fornix role in memory consolidation and hippocampal-cingulate communication.

CITATIONS:
    PMID 19641600 — Vann & Albasser (2009). Hippocampal fornix and memory guidance.
    PMID 22365813 — Agster et al. (2012). Fornix and anterior thalamic mammillary circuit.
    PMID 28902393 — Cona et al. (2016). Fornix role in memory consolidation and hippocampal-cingulate communication.


CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus]
"""

from brain.base_mechanism import BrainMechanism


class FornixHippocampalCingulateBridge(BrainMechanism):
    """
    Fornix — hippocampal-cingulate memory bridge.

    Carries memory consolidation signals from hippocampus
    to mammillary bodies, septal nuclei, and cingulate cortex.
    """

    def __init__(self):
        super().__init__(
            name="FornixHippocampalCingulateBridge",
            human_analog="Fornix — hippocampal-cingulate memory bridge",
            layer="integration",
        )
        self.state.setdefault("fornix_activity", 0.0)
        self.state.setdefault("memory_consolidation_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Hippocampal theta (memory encoding rhythm)
        theta_gen = prior.get("HippocampalThetaGenerator", {})
        theta_out = theta_gen.get("theta_output", {})
        if isinstance(theta_out, dict):
            theta_power = theta_out.get("theta_power", 0.5)
        else:
            theta_power = 0.5

        # Hippocampal CA3 (pattern separation/storage)
        ca3 = prior.get("HippocampalCA3Recurrent", {})
        ca3_out = ca3.get("ca3_output", {})
        if isinstance(ca3_out, dict):
            pattern_sig = ca3_out.get("pattern_completion", 0.5)
        else:
            pattern_sig = 0.5

        # Septal nuclei (cholinergic theta modulation)
        septal = prior.get("SeptalLateralReward", {})
        septal_out = septal.get("septal_output", {})
        if isinstance(septal_out, dict):
            septal_sig = septal_out.get("reward_signal", 0.3)
        else:
            septal_sig = 0.3

        # Amygdala (emotional tagging → important memories)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Mammillary bodies (hypothalamic relay)
        mb = prior.get("MammillaryBodiesRelay", {})
        mb_out = mb.get("mammillary_output", {})
        if isinstance(mb_out, dict):
            mb_sig = mb_out.get("autonomic_strength", 0.5)
        else:
            mb_sig = 0.5

        # PCC (memory retrieval monitoring)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            retrieval_mon = pcc_out.get("retrieval_monitoring", 0.5)
        else:
            retrieval_mon = 0.5

        # Fornix signal: theta × pattern activity × emotional tag
        fornix_activity = theta_power * 0.3 + pattern_sig * 0.3 + abs(emotional_tag) * 0.2 + septal_sig * 0.2
        fornix_activity = max(0.0, min(1.0, fornix_activity))

        # Memory consolidation: fornix signal × retrieval monitoring
        memory_consolidation_strength = fornix_activity * (0.5 + retrieval_mon * 0.5)
        memory_consolidation_strength = max(0.0, min(1.0, memory_consolidation_strength))

        self.state["fornix_activity"] = round(fornix_activity, 4)
        self.state["memory_consolidation_strength"] = round(memory_consolidation_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "fornix_output": {
                "fornix_signal": round(fornix_activity, 4),
                "theta_modulated": theta_power,
            },
            "memory_consolidation_strength": round(memory_consolidation_strength, 4),
            # brain_fornix_relay
            "brain_fornix_relay": round(fornix_activity, 4),
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

