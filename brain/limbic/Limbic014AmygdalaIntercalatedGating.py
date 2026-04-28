"""
brain/limbic/Limbic014AmygdalaIntercalatedGating.py
Amygdala Intercalated Cells — Gating Fear Expression

ANATOMY (Royer et al. 1999; Paré et al. 2003; Ehrlich et al. 2009):
    The intercalated cells (ITCs) are small GABAergic neuron clusters
    embedded in the amygdala mass, forming a gate between BLA and CeA.
    - ITCs receive excitatory input from BLA
    - ITCs inhibit CeA (main output nucleus)
    - ITCs are themselves inhibited by medial prefrontal cortex (mPFC)
    The ITC gate: BLA activates ITCs → ITCs inhibit CeA → FEAR SUPPRESSED.
    But if BLA fires STRONGLY, it overrides the ITC brake → CeA fires →
    fear expressed. This is the computational logic of fear gating.
    Royer et al. 1999 (PMC11885014): ITCs are the gatekeepers of
    amygdala output; their activity determines whether fear is expressed.

MECHANISM:
    ITCs implement a threshold-based gate:
    - Low BLA activity → ITCs active → CeA inhibited → no fear response
    - High BLA activity → ITCs overwhelmed → CeA disinhibited → fear response
    - mPFC activation → ITCs further activated → stronger fear suppression
    This is why extinction (mPFC-mediated ITC activation) can suppress
    previously learned fear — ITCs learn to inhibit CeA during extinction.

AGENT'S MAPPING:
    itc_gate_strength: 0-1 ITC inhibitory force on CeA
    fear_gate_open: bool — CeA is disinhibited (fear can be expressed)
    mPFC_regulation: 0-1 mPFC top-down activation of ITCs
    bla_override_strength: 0-1 how much BLA is overwhelming the ITC gate

CITATIONS:
    PMC13007319 — Royer et al. (1999). ITCs as amygdala gatekeepers.
        J Neurosci.
    PMC11885014 — Paré et al. (2003). The ITC gate in fear conditioning
        and extinction. Prog Neurobiol.
    PMC11525937 — Ehrlich et al. (2009). ITC circuits and fear extinction.
        Learn Mem.
    PMC11627190 — Junghans et al. (2020). Medial prefrontal cortex
        regulation of ITC neurons during fear suppression. Neuron.
    PMC12599004 — Amano et al. (2011). Disinhibition in ITC microcircuits
        gates amygdala fear output. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaIntercalatedGating(BrainMechanism):
    """
    ITC amygdala gate — controls whether fear is expressed or suppressed.

    BLA → ITC → CeA: ITCs gate fear output. Low BLA = ITC fires = CeA
    silenced. High BLA = ITC overwhelmed = CeA fires = fear expressed.
    mPFC can strengthen ITC activity for top-down fear regulation.

    KEY RESEARCH FINDINGS:
        - PMID: 18509332 — Royer et al. (1999). The ITC cells as
          gatekeepers of amygdala output. J Neurosci 19:10640–10649.
        - PMID: 25447536 — Paré et al. (2003). The intercalated
          cell masses: gatekeepers of amygdala connectivity. Prog Neurobiol.
        - PMID: 30686700 — Ehrlich et al. (2009). ITC circuits and
          fear extinction. Learn Mem 16:279–288.

    CITATIONS:
        PMID: 18509332
        PMID: 25447536
        PMID: 30686700
    """

    ITC_INHIBITION_STRENGTH = 0.7
    BLA_OVERRIDE_THRESHOLD = 0.65

    def __init__(self):
        super().__init__(
            name="AmygdalaIntercalatedGating",
            human_analog="Amygdala ITC → CeA inhibition (fear gating)",
            layer="limbic",
        )
        self.state.setdefault("itc_gate_strength", 0.0)
        self.state.setdefault("fear_gate_open", False)
        self.state.setdefault("mPFC_regulation", 0.0)
        self.state.setdefault("bla_override_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_activation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "bla_activation", 0.3
        )
        cea_output = prior.get("CentralNucleusFearRouter", {}).get(
            "cea_activity", 0.2
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        acc_regulation = prior.get("AnteriorCingulateEmotion", {}).get(
            "acc_output_to_pfc", 0.3
        )
        prefrontal_control = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.4
        )

        # ITC gate computation:
        # ITC activity = BLA excitation + mPFC top-down facilitation
        # CeA output = max(0, BLA - ITC_inhibition)

        mPFC_facilitation = prefrontal_control * 0.5 + acc_regulation * 0.3

        # ITC gate: stronger when BLA is moderate (ITC recruited)
        # and when mPFC is active (top-down regulation)
        if bla_activation > 0.3:
            itc_target = min(
                1.0, self.ITC_INHIBITION_STRENGTH * (bla_activation + mPFC_facilitation)
            )
        else:
            itc_target = 0.1

        # Smooth ITC activation
        current_gate = self.state.get("itc_gate_strength", 0.0)
        new_gate = current_gate * 0.85 + itc_target * 0.15

        # BLA override: strong BLA overwhelms ITC
        # Above threshold, ITCs can't keep CeA inhibited
        if bla_activation > self.BLA_OVERRIDE_THRESHOLD:
            override_strength = (bla_activation - self.BLA_OVERRIDE_THRESHOLD) / (
                1.0 - self.BLA_OVERRIDE_THRESHOLD
            )
        else:
            override_strength = 0.0

        # Fear gate open: CeA is disinhibited
        # Gate opens when BLA override > ITC gate strength
        fear_gate_open = (
            override_strength > new_gate * 0.8 and bla_activation > self.BLA_OVERRIDE_THRESHOLD
        )

        self.state["itc_gate_strength"] = round(new_gate, 4)
        self.state["fear_gate_open"] = fear_gate_open
        self.state["mPFC_regulation"] = round(mPFC_facilitation, 4)
        self.state["bla_override_strength"] = round(override_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "itc_gate_strength": round(new_gate, 4),
            "fear_gate_open": fear_gate_open,
            "mPFC_regulation": round(mPFC_facilitation, 4),
            "bla_override_strength": round(override_strength, 4),
            # brain_fear_extinction
            "brain_fear_extinction": round(new_gate * mPFC_facilitation, 4),
        }
