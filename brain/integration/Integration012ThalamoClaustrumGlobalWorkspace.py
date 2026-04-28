"""
brain/integration/Integration012ThalamoClaustrumGlobalWorkspace.py
Thalamus-Claustrum Global Workspace — Conscious Broadcasting

ANATOMY (Dehaene & Changeux 2011; Baars 1997; Sergent & Naccache 2012):
    The global workspace theory proposes that consciousness arises
    when information is broadcast from a "workspace" to all cortical
    regions simultaneously. The thalamus and claustrum are key
    components of this workspace:

    Thalamus: the "relay" — intralaminar nuclei (centromedian, parafascicular)
    project broadly to cortex, providing a "thalamic relay" for global
    broadcast. The intralaminar nuclei fire during salience and
    arousal, driving global cortical activation.

    Claustrum: the "gateway" — gates which signals enter the global
    workspace. Only signals that pass through the claustrum's
    synchronized burst get broadcast globally.

    Global workspace dynamics:
    - Non-conscious: processing is local (specific cortical regions)
    - Conscious access: information reaches workspace → global broadcast
    - Workspace neurons: distributed across prefrontal, parietal, temporal
    - Competition: only one coherent content wins the workspace at a time

    Key evidence: Dehaene's experiments show that masked (unconscious)
    stimuli do not activate prefrontal cortex; unmasked (conscious)
    stimuli do. The prefrontal cortex is the "workspace hub."

KEY FINDINGS:
    1. Dehaene & Changeux 2011 (PMC3972740): "Global workspace theory
       and conscious access"
    2. Baars 1997: "Global workspace theory of consciousness"
    3. Sergent & Naccache 2012 (PMC4326522): GM workspace and consciousness

AGENT'S MAPPING:
    global_workspace: dict — workspace state
    workspace_broadcast: float 0-1 — strength of broadcast
    all_regions_fired: list — regions that received the broadcast

CITATIONS:
    PMID 32135090 — Mashour et al. (2020). Conscious Processing and the GNW Hypothesis. Neuron.
    PMID 40307561 — Cogitate Consortium (2025). Adversarial testing of GNW and IIT. Nature.
    PMID 16257162 — Crick & Koch (2005). What is the claustrum? Nat Neurosci.
    PMC2697346 — Dehaene et al. (2011). Towards a cognitive neuroscience of global workspace.
"""

from brain.base_mechanism import BrainMechanism


class ThalamoClaustrumGlobalWorkspace(BrainMechanism):
    """
    Thalamus-claustrum global workspace — conscious broadcasting.

    Broadcasts salient information to all cortical regions
    simultaneously, creating conscious awareness.
    """

    def __init__(self):
        super().__init__(
            name="ThalamoClaustrumGlobalWorkspace",
            human_analog="Thalamus-claustrum global workspace — conscious broadcasting",
            layer="integration",
        )
        self.state.setdefault("workspace_content", {})
        self.state.setdefault("workspace_broadcast", 0.0)
        self.state.setdefault("all_regions_fired", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Claustrum gate
        claustrum = prior.get("ClaustrumGlobalConsciousness", {})
        claustrum_out = claustrum.get("claustral_output", {})
        if isinstance(claustrum_out, dict):
            claustrum_act = claustrum_out.get("claustrum_activation", 0.5)
            global_broadcast = claustrum_out.get("global_broadcast", False)
        else:
            claustrum_act = 0.5
            global_broadcast = False

        # Thalamic intralaminar nuclei (centromedian — salience broadcast)
        thal_cm = prior.get("ThalamicCentromedianIntralaminar", {})
        cm_out = thal_cm.get("cm_output", {})
        if isinstance(cm_out, dict):
            cm_signal = cm_out.get("intralaminar_strength", 0.5)
        else:
            cm_signal = 0.5

        # Salience network (what gets broadcast)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)

        # ACC (cognitive salience)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
        else:
            error_sig = 0.3

        # Theta-gamma binding (what to broadcast — the content)
        tg = prior.get("ThetaGammaCrossFrequencyBinding", {})
        bound_exp = tg.get("bound_experience", 0.5)

        # Prefrontal cortex hub (workspace hub for conscious content)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5

        # OFC (value — what's worth broadcasting?)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # Workspace readiness
        workspace_readiness = (
            claustrum_act * 0.3 +
            cm_signal * 0.2 +
            bound_exp * 0.2 +
            salience * 0.2 +
            value_sig * 0.1
        )

        # Workspace broadcast
        workspace_broadcast = workspace_readiness * (1.5 if global_broadcast else 1.0)
        workspace_broadcast = max(0.0, min(1.0, workspace_broadcast))

        # Regions that fired: depends on broadcast strength
        regions_fired = []
        if workspace_broadcast > 0.3:
            regions_fired.extend(["pfc", "parietal"])
        if workspace_broadcast > 0.5:
            regions_fired.extend(["temporal", "cingulate"])
        if workspace_broadcast > 0.7:
            regions_fired.extend(["motor", "occipital", "limbic"])

        self.state["workspace_content"] = {"broadcast_strength": round(workspace_broadcast, 4)}
        self.state["workspace_broadcast"] = round(workspace_broadcast, 4)
        self.state["all_regions_fired"] = regions_fired
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "global_workspace": {
                "broadcast_strength": round(workspace_broadcast, 4),
                "regions_fired": regions_fired,
            },
            "workspace_broadcast": round(workspace_broadcast, 4),
            "all_regions_fired": regions_fired,
        }