"""
brain/integration/Integration004ClaustrumGlobalConsciousness.py
Claustrum — Global Ignition, Attention Binding, Consciousness Switch

ANATOMY (Crick & Koch 2005; Mathuru 2012; Reardon 2020):
    The claustrum is a thin, sheet-like bilateral structure deep
    within each hemisphere, between the putamen and the insular
    cortex. It has been called "the most connected structure
    in the brain" — every cortical area sends projections to
    the claustrum, and the claustrum projects back to every
    cortical area.

    Crick & Koch (2005, PMID 16257162) proposed that the claustrum
    is the "seat of consciousness" — a global synchronization
    hub that binds all cortical signals into a unified conscious
    experience. When a salient event occurs, the claustrum fires
    a burst that synchronizes all relevant cortical regions,
    creating momentary conscious awareness.

    The claustrum works via:
    - GABAergic interneurons (inhibitory broadcast)
    - Very fast electrical coupling (gap junctions)
    - Large receptive fields spanning entire cortex

    In 2020, researchers discovered that claustrum stimulation
    (in a human patient) caused immediate loss of consciousness —
    stimulating the claustrum "turned off" consciousness
    instantly; stopping stimulation "turned it back on" (Reardon 2020).

KEY FINDINGS:
    1. Crick & Koch 2005 (PMID 16257162): "What is the claustrum?"
       — proposed as the seat of consciousness
    2. Mathuru 2012 (PMC22749889): "Claustrum and attention" —
       claustrum gates cortical inputs
    3. Reardon 2020 (PMID 32084324): Human claustrum stimulation
       causes loss of consciousness

AGENT'S MAPPING:
    claustral_output: dict — claustrum global output
    global_broadcast: bool — has global broadcast occurred?
    consciousness_signal: float 0-1 — level of conscious awareness

CITATIONS:
    PMID 15643691 — Edelstein et al. (2004). The claustrum: a historical review. Cell Mol Biol.
    PMID 16257162 — Crick & Koch (2005). What is the claustrum? Nat Neurosci.
    PMID 32084324 — Reardon (2020). Scientists Probed the Seat of Consciousness. Nature.
    PMC2697346 — Felleman & Van Essen (1991). Cortical connectivity. Cereb Cortex.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class ClaustrumGlobalConsciousness(BrainMechanism):
    """
    Claustrum — global consciousness switch and attention binding.

    Acts as the brain's "ignition" — when salient, fires a
    coordinated burst that synchronizes all cortical regions
    into momentary conscious awareness.
    """

    def __init__(self):
        super().__init__(
            name="ClaustrumGlobalConsciousness",
            human_analog="Claustrum — global ignition, attention binding, consciousness switch",
            layer="integration",
        )
        self.state.setdefault("broadcast_history", [])
        self.state.setdefault("global_broadcast", False)
        self.state.setdefault("consciousness_signal", 0.5)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Salience network (AI + ACC — what matters right now)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)
        net_switch = ai.get("network_switch_trigger", "default")
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        error_sig = acc_out.get("error_signal", 0.3) if isinstance(acc_out, dict) else 0.3

        # Thalamus (intracortical relay — input to claustrum)
        thal_md = prior.get("ThalamicMediodorsalExecutive", {})
        thal_out = thal_md.get("thal_output", {})
        if isinstance(thal_out, dict):
            exec_signal = thal_out.get("executive_signal", 0.5)
        else:
            exec_signal = 0.5

        # Anterior cingulate (conflict detection for conscious access)
        acc_limbic = prior.get("AnteriorCingulateEmotion", {})
        acc_emo = acc_limbic.get("acc_output", {})
        if isinstance(acc_emo, dict):
            conflict = acc_emo.get("conflict_level", 0.3)
        else:
            conflict = 0.3

        # Orbitofrontal (value — does this deserve conscious attention?)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # Global workspace (conscious content integration)
        gw = prior.get("GlobalWorkspaceIntegrator", {})
        gw_out = gw.get("global_workspace_content", {})
        if isinstance(gw_out, dict):
            conscious_content = gw_out.get("conscious_content", "unknown")
        else:
            conscious_content = "unknown"

        # Claustrum activation: strong salience + executive signal + conflict/value
        claustrum_signal = (
            salience * 0.25 +
            exec_signal * 0.25 +
            error_sig * 0.2 +
            conflict * 0.15 +
            value_sig * 0.15
        )
        claustrum_signal = max(0.0, min(1.0, claustrum_signal))

        # Global broadcast: claustrum fires when signal exceeds ignition threshold
        ignition_threshold = 0.65
        global_broadcast = claustrum_signal > ignition_threshold

        # Consciousness signal: elevated during global broadcast
        if global_broadcast:
            consciousness_signal = claustrum_signal * 1.2
        else:
            consciousness_signal = max(0.5, claustrum_signal * 0.8)
        consciousness_signal = max(0.0, min(1.0, consciousness_signal))

        # Record
        self.state["broadcast_history"].append(round(claustrum_signal, 3))
        if len(self.state["broadcast_history"]) > 5:
            self.state["broadcast_history"].pop(0)

        self.state["global_broadcast"] = global_broadcast
        self.state["consciousness_signal"] = round(consciousness_signal, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "claustral_output": {
                "claustrum_activation": round(claustrum_signal, 4),
                "global_broadcast": global_broadcast,
                "consciousness_level": round(consciousness_signal, 4),
            },
            "global_broadcast": global_broadcast,
            "consciousness_signal": round(consciousness_signal, 4),
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

