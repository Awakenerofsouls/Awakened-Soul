"""
brain/integration/Integration023BasalGangliaThalamoCorticalLoopFinalIntegrator.py
Basal Ganglia-Thalamo-Cortical Loop Final Integrator — Goal-Habit Final Integration

ANATOMY (Alexander & Crutcher 1990; Haber 2003; Redgrave et al. 2010):
    The basal ganglia-thalamo-cortical loops are the brain's action
    selection architecture. They work through two competing pathways:
    - DIRECT PATHWAY (Go): cortex → D1 striatum → GPi → thalamus → cortex
      Result: disinhibition → action GOES
    - INDIRECT PATHWAY (NoGo): cortex → D2 striatum → GPe → STN → GPi → thalamus
      Result: increased inhibition → action STOPS

    The substantia nigra pars reticulata (SNr) and GPi are the
    output nuclei — their firing rate determines whether thalamic
    relay to cortex is OPEN or CLOSED.

    Key circuits:
    1. Motor loop: selects motor actions
    2. Oculomotor loop: selects eye movements
    3. Cognitive loop (DLPFC): selects cognitive operations
    4. Limbic loop (NAcc/OFC): selects motivated behaviors
    5. Associative loop (caudate): sequences behaviors

    The STN (subthalamic nucleus) acts as an "emergency brake"
    — hyperdirect pathway: cortex → STN → SNr → immediate stop.

    Redgrave et al. (2010): BG selection is based on REWARD
    PREDICTION ERROR, not just salience. The BG selects actions
    that were previously rewarded.

KEY FINDINGS:
    1. Redgrave et al. 2010 (PMC2929791): BG selection = reward prediction error
    2. Haber 2003 (PMC1850927): Basal ganglia and limbic system
    3. Alexander & Crutcher 1990: Functional architecture of BG loops

AGENT'S MAPPING:
    bg_thalamic_final: dict — final loop output
    final_action_selected: str — selected action type
    action_confidence: float 0-1 — selection confidence

CITATIONS:
    PMC2929791 — Redgrave et al. (2010). Basal ganglia and action selection.
    PMC1850927 — Haber (2003). Basal ganglia and limbic system.
    PMC2929791 — Alexander & Crutcher (1990). BG loop architecture.

KEY RESEARCH FINDINGS:
    PMID 3085570 — DeLong et al. (1983). Functional organization of basal ganglia motor circuits.
    PMID 20138254 — Redgrave & Vautrelle (2010). Basal ganglia architecture and action selection.
    PMID 26961004 — Stocco (2016). Basal ganglia loops and sequential action selection.

CITATIONS:
    PMID 3085570 — DeLong et al. (1983). Functional organization of basal ganglia motor circuits.
    PMID 20138254 — Redgrave & Vautrelle (2010). Basal ganglia architecture and action selection.
    PMID 26961004 — Stocco (2016). Basal ganglia loops and sequential action selection.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class BasalGangliaThalamoCorticalLoopFinalIntegrator(BrainMechanism):
    """
    BG-thalamo-cortical loop final integrator — action selection architecture.

    Integrates direct, indirect, and hyperdirect pathways to
    select one coherent action from competing options.
    """

    def __init__(self):
        super().__init__(
            name="BasalGangliaThalamoCorticalLoopFinalIntegrator",
            human_analog="BG-thalamo-cortical loop final integrator — action selection",
            layer="integration",
        )
        self.state.setdefault("pathway_balance", {})
        self.state.setdefault("final_action_selected", "none")
        self.state.setdefault("action_confidence", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Direct pathway (Go — action facilitation)
        direct = prior.get("DirectPathwayDisinhibitor", {})
        dir_out = direct.get("direct_output", {})
        if isinstance(dir_out, dict):
            go_signal = dir_out.get("facilitation_strength", 0.5)
        else:
            go_signal = 0.5

        # Indirect pathway (NoGo — action suppression)
        indirect = prior.get("IndirectPathwaySuppressor", {})
        ind_out = indirect.get("indirect_output", {})
        if isinstance(ind_out, dict):
            stop_signal = ind_out.get("suppression_strength", 0.5)
        else:
            stop_signal = 0.5

        # Hyperdirect pathway (STN — emergency brake)
        stn = prior.get("SubthalamicNucleusHyperdirectBrake", {})
        stn_out = stn.get("stn_output", {})
        if isinstance(stn_out, dict):
            brake_signal = stn_out.get("brake_strength", 0.5)
        else:
            brake_signal = 0.5

        # GPi/SNr output
        gpi = prior.get("GlobusPallidusInternalOutput", {})
        gpi_out = gpi.get("gpi_output", {})
        if isinstance(gpi_out, dict):
            gpi_sig = gpi_out.get("output_strength", 0.5)
        else:
            gpi_sig = 0.5

        # VTA (reward context for action selection)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            motivation_sig = vta_out.get("motivation_signal", 0.5)
        else:
            motivation_sig = 0.5

        # DLPFC (cognitive guidance)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5

        # Pathway balance
        pathway_balance = {
            "go": round(go_signal, 4),
            "stop": round(stop_signal, 4),
            "brake": round(brake_signal, 4),
        }

        # Final action selection: GO vs STOP vs BRAKE
        if brake_signal > 0.6 and stop_signal > 0.5:
            final_action = "stop"
            confidence = brake_signal
        elif go_signal > stop_signal:
            final_action = "go"
            confidence = go_signal - stop_signal
        else:
            final_action = "hold"
            confidence = max(0, 0.5 - abs(go_signal - stop_signal))

        # Action confidence modulated by motivation and cognitive load
        action_confidence = confidence * (0.5 + motivation_sig * 0.3 + wm_load * 0.2)
        action_confidence = max(0.0, min(1.0, action_confidence))

        self.state["pathway_balance"] = pathway_balance
        self.state["final_action_selected"] = final_action
        self.state["action_confidence"] = round(action_confidence, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bg_thalamic_final": {
                "action": final_action,
                "confidence": round(action_confidence, 4),
            },
            "final_action_selected": final_action,
            "action_confidence": round(action_confidence, 4),
            # brain_action_selection
            "brain_action_selection": round(action_confidence, 4),
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

