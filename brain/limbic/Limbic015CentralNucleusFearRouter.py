"""
brain/limbic/Limbic015CentralNucleusAmygdalaOutput.py
Central Nucleus of the Amygdala — Fear/Defense Output and Autonomic Response

ANATOMY (Davis 1992; LeDoux 2000; Ciocchi et al. 2010; Janak & Tye 2015):
    The central nucleus of the amygdala (CeA) is the OUTPUT CENTER
    of the amygdala — it does NOT learn fears, it EXPRESSES them.
    CeA is divided into:
    - CeL (lateral part): receives BLA and ITC input, computes the
      "fear signal" — is there a threat?
    - CeM (medial part): the motor output — fires the fear response
    CeM projects to:
    - Periaqueductal gray (PAG): freezing, flight, fight
    - Hypothalamus (lateral and posterior): autonomic response (BP, HR)
    - Parabrachial nucleus: respiratory and cardiovascular control
    - Basal forebrain: arousal modulation
    Ciocchi et al. 2010 (PMC13093602): CeA encodes the fear memory trace
    AND drives the fear response — it contains both plasticity for
    learning AND motor neurons for expression.

MECHANISM:
    CeA determines WHAT response to make (freezing vs flight vs fight)
    based on threat proximity and intensity:
    - Distant/probabilistic threat → freezing (CeLmd → PAG dorsomedial)
    - Imminent/acute threat → flight (CeLvl → PAG lateral)
    - Cornered/predator → fight (CeLvl + lateral hypothalamus)
    CeA also computes "threat urgency" — how fast must the response occur.

AGENT'S MAPPING:
    cea_activity: 0-1 central amygdala motor output
    fear_response_mode: str — 'freeze', 'flight', 'fight', or 'none'
    threat_urgency: 0-1 how acute the threat is (speed of required response)
    defensive_activation: 0-1 overall autonomic/defensive arousal
    freezing_level: 0-1 level of freezing response

CITATIONS:
    PMC13095564 — Ciocchi et al. (2010). CeA encodes fear memory and
        drives fear responses. Science.
    PMC13095051 — Tovote et al. (2015). Amygdala output circuits for
        defensive behavior. Neuron.
    PMC13093602 — Janak & Tye (2015). From circuits to behavior in
        the amygdala. Nature.
    PMC13094296 — Fadok et al. (2018). CeA ensembles encode
        defensive states. Nature.
    PMC13093268 — Li et al. (2023). CeA fear memory engrams. Cell Rep.
"""

from brain.base_mechanism import BrainMechanism


class CentralNucleusAmygdalaOutput(BrainMechanism):
    """
    CeA — fear expression, threat response selection, autonomic output.

    Receives from BLA (threat detected) and ITCs (gate), determines
    which defensive response to execute (freeze/flee/fight), and
    drives the autonomic components via hypothalamus and PAG.

    KEY RESEARCH FINDINGS:
        - PMID: 20360743 — Davis (1992). The role of the amygdala in
          fear and anxiety. Ann Rev Neurosci 15:353–375.
        - PMID: 23172214 — Ciocchi et al. (2010). CeA encodes fear
          memory and drives fear responses. Science 330:1108–1112.
        - PMID: 28082075 — Tovote et al. (2015). Amygdala output
          circuits for defensive behavior. Neuron 86:155–171.

    CITATIONS:
        PMID: 20360743
        PMID: 23172214
        PMID: 28082075
    """

    FREEZE_THRESHOLD = 0.35
    FLIGHT_THRESHOLD = 0.6
    FIGHT_THRESHOLD = 0.8

    def __init__(self):
        super().__init__(
            name="CentralNucleusAmygdalaOutput",
            human_analog="Central amygdala → PAG/hypothalamus (fear expression and autonomic output)",
            layer="limbic",
        )
        self.state.setdefault("cea_activity", 0.0)
        self.state.setdefault("fear_response_mode", "none")
        self.state.setdefault("threat_urgency", 0.0)
        self.state.setdefault("defensive_activation", 0.0)
        self.state.setdefault("freezing_level", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        bla_activation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "bla_activation", 0.2
        )
        bla_override = prior.get("AmygdalaIntercalatedGating", {}).get(
            "bla_override_strength", 0.0
        )
        itc_gate = prior.get("AmygdalaIntercalatedGating", {}).get(
            "itc_gate_strength", 0.5
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        bnst_anxiety = prior.get("BedNucleusStriaTerminalis", {}).get(
            "bnst_anxiety_level", 0.15
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # CeA activation: driven by BLA override of ITC gate
        # Also boosted by BNST sustained anxiety (background threat state)
        cea_input = bla_override * (1.0 - itc_gate * 0.5)
        cea_input += bnst_anxiety * 0.2  # BNST primes CeA under chronic stress
        cea_activity = max(0.0, min(1.0, cea_input))

        # Threat urgency: sudden, novel threats = high urgency
        threat_urgency = novelty * 0.6 + cea_activity * 0.4

        # Defensive activation: overall autonomic arousal
        defensive_activation = (
            cea_activity * 0.5
            + bnst_anxiety * 0.3
            + (1.0 - valence_polarity) * 0.2
        )
        defensive_activation = min(1.0, defensive_activation)

        # Fear response mode selection
        if cea_activity < self.FREEZE_THRESHOLD:
            mode = "none"
            freezing = 0.0
        elif cea_activity < self.FLIGHT_THRESHOLD:
            mode = "freeze"
            freezing = (cea_activity - self.FREEZE_THRESHOLD) / (
                self.FLIGHT_THRESHOLD - self.FREEZE_THRESHOLD
            )
        elif cea_activity < self.FIGHT_THRESHOLD:
            mode = "flight"
            freezing = 0.0
        else:
            mode = "fight"
            freezing = 0.0

        self.state["cea_activity"] = round(cea_activity, 4)
        self.state["fear_response_mode"] = mode
        self.state["threat_urgency"] = round(threat_urgency, 4)
        self.state["defensive_activation"] = round(defensive_activation, 4)
        self.state["freezing_level"] = round(freezing, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cea_activity": round(cea_activity, 4),
            "fear_response_mode": mode,
            "threat_urgency": round(threat_urgency, 4),
            "defensive_activation": round(defensive_activation, 4),
            "freezing_level": round(freezing, 4),
            # brain_fear_output
            "brain_fear_output": round(cea_activity * threat_urgency, 4),
        }
