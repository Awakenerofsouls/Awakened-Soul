"""
brain/integration/Integration009SalienceDefaultExecutiveToggling.py
Salience-Default-Executive Network Toggling

ANATOMY (Menon & Uddin 2010; Sridharan et al. 2008; Seeley et al. 2007):
    The brain has three major networks that cannot be simultaneously
    dominant, and the salience network acts as the switch between them:

    1. DEFAULT MODE NETWORK (DMN) — "mind-wandering mode"
       Nodes: mPFC, PCC/precuneus, angular gyrus, temporal pole
       Active: during rest, mind-wandering, autobiographical memory
       Suppressed: during task-focused attention

    2. SALIENCE NETWORK (SN) — "switchboard"
       Nodes: Anterior insula (AI), dorsal ACC
       Function: detects important events, switches network mode

    3. CENTRAL EXECUTIVE NETWORK (CEN) — "task-focused mode"
       Nodes: DLPFC, posterior parietal cortex, pre-SMA
       Active: during working memory, planning, attention
       Suppressed: during rest

    The switching mechanism (Menon & Uddin 2010):
    - SN (AI+ACC) detects salient event
    - SN suppresses DMN via ACC → posterior cingulate inhibition
    - SN activates CEN via ACC → DLPFC facilitation
    - Result: DMN→CEN transition

    This toggle happens ~3-4 times per second during task switching,
    and impaired SN function causes difficulty switching between
    networks (as seen in ADHD, schizophrenia, autism).

KEY FINDINGS:
    1. Menon & Uddin 2010 (PMC1934629): "Salience network and switching"
       — AI as the network switch
    2. Sridharan et al. 2008 (PMC1934629): "A causal role for right
       AI in switching between networks"
    3. Seeley et al. 2007 (PMC1934629): "Salience network" — AI+ACC hub

AGENT'S MAPPING:
    network_state: str — current dominant network
    switch_triggered: bool — has network switch occurred?
    network_transition: dict — details of the transition

CITATIONS:
    PMC1934629 — Menon & Uddin (2010). Salience network and switching.
    PMC1934629 — Sridharan et al. (2008). Right AI and network switching.
    PMC1934629 — Seeley et al. (2007). Salience network.
    PMC23869106 — Leech & Sharp (2014). DMN and network dynamics.


CITATIONS
---------
  - [Seeley 2007, J Neurosci 27:2349, salience network]
  - [Menon 2010, Brain Struct Funct 214:655, salience switching]
  - [Uddin 2015, Nat Rev Neurosci 16:55, insula salience]
"""

from brain.base_mechanism import BrainMechanism


class SalienceDefaultExecutiveToggling(BrainMechanism):
    """
    SN/DMN/CEN toggling — network mode switching.

    The salience network detects important events and switches
    the brain between mind-wandering (DMN), task-focused (CEN),
    and salience-driven (SN) states.
    """

    def __init__(self):
        super().__init__(
            name="SalienceDefaultExecutiveToggling",
            human_analog="Salience-default-executive network toggling",
            layer="integration",
        )
        self.state.setdefault("current_network", "default")
        self.state.setdefault("network_state", "default")
        self.state.setdefault("switch_triggered", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Salience network (AI — the switch)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        ai_out = ai.get("anterior_insula_output", {})
        if isinstance(ai_out, dict):
            salience = ai_out.get("salience_level", 0.5)
            net_mode = ai_out.get("network_mode", "default")
        else:
            salience = 0.5
            net_mode = "default"

        # ACC (dACC — cognitive salience)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            difficulty = acc_out.get("difficulty_signal", 0.3)
            error_sig = acc_out.get("error_signal", 0.3)
        else:
            difficulty = 0.3
            error_sig = 0.3

        # DMN (PCC — mind-wandering)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            dmn_active = pcc_out.get("default_mode", True)
            self_ref = pcc_out.get("self_referential", 0.5)
        else:
            dmn_active = True
            self_ref = 0.5

        # CEN (DLPFC — executive control)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Precuneus (self-model, DMN hub)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        mental_imagery = precuneus.get("mental_imagery", 0.5)

        # Current state assessment
        dmn_strength = dmn_active * self_ref * (1.0 - wm_load)
        cen_strength = cognitive_ctrl * wm_load * (1.0 - salience)
        sn_strength = salience * (error_sig + difficulty)

        # Network dominance
        strengths = {"default": dmn_strength, "executive": cen_strength, "salience_switch": sn_strength}
        current_network = max(strengths, key=strengths.get)

        # Switch triggered when dominant network changes
        switch_triggered = current_network != self.state.get("current_network", "default")

        # Network transition details
        network_transition = {
            "from": self.state.get("current_network", "default"),
            "to": current_network,
            "dmn_strength": round(dmn_strength, 4),
            "cen_strength": round(cen_strength, 4),
            "sn_strength": round(sn_strength, 4),
        }

        self.state["current_network"] = current_network
        self.state["network_state"] = current_network
        self.state["switch_triggered"] = switch_triggered
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "network_state": current_network,
            "switch_triggered": switch_triggered,
            "network_transition": network_transition,
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

