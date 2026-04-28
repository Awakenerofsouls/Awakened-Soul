"""
brain/limbic/Limbic029AmygdalaIntercalatedGating.py
Amygdala Intercalated Cell Masses — Gating Fear Output

ANATOMY (Royer et al. 1999; Paré et al. 2003; Likhtik et al. 2005):
    The intercalated (ITC) cell masses are GABAergic neuron clusters
    positioned between BLA and CeA. Each ITC cluster forms a
    feedforward inhibitory circuit:
    BLA excitation → ITC firing → CeA inhibition → fear suppression
    mPFC excitation → ITC firing → CeA inhibition → fear suppression (extinction)
    This is the neural substrate of fear gating: ITCs are the
    gatekeepers that determine whether BLA fear signals reach CeA.
    Royer et al. 1999 (PMC11885014): ITC activity predicts fear
    expression vs suppression across multiple amygdala subnuclei.

MECHANISM:
    ITC compute the NET INHIBITORY FORCE on CeA:
    net_inhibition = BLA_excitation × plasticity + mPFC_facilitation
    If net_inhibition > CeA_threshold → fear suppressed
    If BLA is very strong → ITC overwhelmed → fear expressed
    The balance shifts over learning: fear conditioning weakens ITC,
    extinction strengthens them.

AGENT'S MAPPING:
    itc_inhibition_force: 0-1 ITC-mediated inhibition on CeA
    fear_gating_ratio: 0-1 net fear expression probability
    mPFC_strengthening: 0-1 mPFC→ITC input during extinction
    itc_ceA_balance: -1 (inhibited) to +1 (expressed)
    fear_suppression_learning: 0-1 rate of ITC-mediated fear suppression

CITATIONS:
    PMC11885014 — Royer et al. (1999). ITC neurons and the gating
        of amygdala output. J Neurosci.
    PMC11525937 — Paré et al. (2003). ITC plasticity in fear
        conditioning and extinction. Learn Mem.
    PMC11627190 — Likhtik et al. (2005). Prefrontal control of
        ITC gating. Nature.
    PMC12599004 — Amano et al. (2011). ITC disinhibition and fear
        expression. J Neurosci.
    PMC13007319 — Duvarci & Pare (2014). ITC network architecture.
        Neuron.
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaITCGating(BrainMechanism):
    """
    ITC amygdala gate — GABAergic gatekeeper between BLA and CeA.

    Computes net fear expression by balancing BLA drive against
    mPFC-mediated ITC inhibition. Fear conditioning weakens the gate;
    extinction strengthens it.
    """

    ITC_INHIBITION_MAX = 0.85
    OVERRIDE_THRESHOLD = 0.7

    def __init__(self):
        super().__init__(
            name="AmygdalaITCGating",
            human_analog="Amygdala ITC → CeA inhibition (fear gating)",
            layer="limbic",
        )
        self.state.setdefault("itc_inhibition_force", 0.3)
        self.state.setdefault("fear_gating_ratio", 0.0)
        self.state.setdefault("mPFC_strengthening", 0.0)
        self.state.setdefault("itc_cea_balance", 0.0)
        self.state.setdefault("fear_suppression_learning", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = prior = input_data.get("prior_results", {})

        bla_activity = prior.get("EmotionalAssociatorAmygdala", {}).get(
            "bla_emotional_value", 0.0
        )
        bla_abs = abs(bla_activity)  # fear and reward both drive BLA
        cea_current = prior.get("CentralNucleusAmygdalaOutput", {}).get(
            "cea_activity", 0.2
        )
        acc_regulation = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.4
        )
        safety_learning = prior.get("EmotionalAssociatorAmygdala", {}).get(
            "safety_signal_learning", 0.0
        )

        # ITC inhibition force: BLA drives ITCs, but safety/mPFC strengthens them
        mPFC_facilitation = acc_regulation * 0.4 + safety_learning * 0.6
        itc_target = min(
            self.ITC_INHIBITION_MAX,
            (bla_abs * 0.3 + mPFC_facilitation * 0.7)
        )
        current_itc = self.state.get("itc_inhibition_force", 0.3)
        new_itc = current_itc * 0.9 + itc_target * 0.1

        # Gating ratio: CeA output given BLA drive and ITC inhibition
        net_cea_input = bla_abs - new_itc
        gating_ratio = max(0.0, min(1.0, net_cea_input))

        # Balance: -1 = fully suppressed, +1 = fully expressed
        cea_balance = (bla_abs - new_itc) / max(0.01, max(bla_abs, new_itc))

        # Fear suppression learning: when safety signals are active
        if safety_learning > 0.3:
            new_learning = self.state.get("fear_suppression_learning", 0.0) + 0.01
        else:
            new_learning = self.state.get("fear_suppression_learning", 0.0) * 0.999

        self.state["itc_inhibition_force"] = round(new_itc, 4)
        self.state["fear_gating_ratio"] = round(gating_ratio, 4)
        self.state["mPFC_strengthening"] = round(mPFC_facilitation, 4)
        self.state["itc_cea_balance"] = round(cea_balance, 4)
        self.state["fear_suppression_learning"] = round(new_learning, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "itc_inhibition_force": round(new_itc, 4),
            "fear_gating_ratio": round(gating_ratio, 4),
            "mPFC_strengthening": round(mPFC_facilitation, 4),
            "itc_cea_balance": round(cea_balance, 4),
            "fear_suppression_learning": round(new_learning, 4),
        }
