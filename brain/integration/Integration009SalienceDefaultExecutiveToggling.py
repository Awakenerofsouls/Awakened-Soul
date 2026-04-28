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