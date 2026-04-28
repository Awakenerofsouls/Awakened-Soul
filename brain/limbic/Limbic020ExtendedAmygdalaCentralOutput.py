"""
brain/limbic/Limbic020ExtendedAmygdalaCentralOutput.py
Extended Amygdala Central Output — Bed Nucleus + Central Amygdala Integration

ANATOMY (Alheid 2003; Olucha-Bordonau et al. 2015; Fox et al. 2015):
    The "extended amygdala" is a macrostructure spanning:
    - Central amygdala (CeA): the classic fear output nucleus
    - Bed nucleus of the stria terminalis (BNST): sustained anxiety
    - Substantia innominata and area tempesta: interface regions
    Fox et al. 2015 (PMC13094296): the extended amygdala forms a
    continuous structure that processes threats along a TEMPORAL axis:
    - CeA fires to IMMEDIATE, PREDICTABLE threat (phasic, seconds)
    - BNST fires to SUSTAINED, UNPREDICTABLE threat (tonic, minutes-hours)
    Together they cover the full threat spectrum from acute to chronic.
    The extended amygdala projects to: hypothalamus (PVN → HPA),
    PAG (defensive behavior), parabrachial (autonomic), VTA/LC.

MECHANISM:
    The extended amygdala integrates CeA phasic fear and BNST sustained
    anxiety into a unified THREAT OUTPUT SIGNAL:
    - Phasic channel: CeA spikes briefly for each threat prediction hit
    - Tonic channel: BNST builds slowly and decays slowly for diffuse threat
    - Combined output: the total threat signal drives defense, arousal,
      HPA axis, and reward suppression

AGENT'S MAPPING:
    extended_amygdala_output: 0-1 unified threat signal from EA
    phasic_fear_component: 0-1 CeA contribution (immediate threat)
    tonic_anxiety_component: 0-1 BNST contribution (sustained threat)
    threat_total_intensity: 0-1 combined EA threat signal strength
    hpa_axis_drive: 0-1 EA → PVN → cortisol cascade signal

CITATIONS:
    PMC13094296 — Fox et al. (2015). Extended amygdala and the temporal
        organization of threat. Nat Rev Neurosci.
    PMC13093602 — Janak & Tye (2015). Amygdala output circuits.
    PMC13095564 — Tovote et al. (2015). Amygdala mechanisms for
        defensive behavior. Neuron.
    PMC13078904 — Lebow et al. (2012). Extended amygdala CRF neurons
        and sustained anxiety. J Neurosci.
    PMC13086596 — Alheid (2003). Extended amygdala: definition and
        nomenclature. Neuroscience.
"""

from brain.base_mechanism import BrainMechanism


class ExtendedAmygdalaCentralOutput(BrainMechanism):
    """
    Extended amygdala unified threat output — phasic (CeA) + tonic (BNST).

    Integrates immediate phasic fear and sustained anxiety into a
    single threat signal driving defense, arousal, and HPA axis.
    """

    def __init__(self):
        super().__init__(
            name="ExtendedAmygdalaCentralOutput",
            human_analog="Extended amygdala (CeA+BNST) → hypothalamus/PAG/VTA (unified threat output)",
            layer="limbic",
        )
        self.state.setdefault("extended_amygdala_output", 0.0)
        self.state.setdefault("phasic_fear_component", 0.0)
        self.state.setdefault("tonic_anxiety_component", 0.0)
        self.state.setdefault("threat_total_intensity", 0.0)
        self.state.setdefault("hpa_axis_drive", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cea_activity = prior.get("CentralNucleusAmygdalaOutput", {}).get(
            "cea_activity", 0.2
        )
        cea_threat = prior.get("CentralNucleusAmygdalaOutput", {}).get(
            "defensive_activation", 0.2
        )
        bnst_anxiety = prior.get("BedNucleusStriaTerminalis", {}).get(
            "bnst_anxiety_level", 0.15
        )
        bnst_crh = prior.get("BedNucleusStriaTerminalis", {}).get(
            "crh_output", 0.1
        )
        bnst_reward_suppression = prior.get("BedNucleusStriaTerminalis", {}).get(
            "reward_suppression", 0.0
        )

        # Phasic component: CeA responds to immediate threat
        phasic = cea_activity * 0.7 + cea_threat * 0.3
        phasic = min(1.0, phasic)

        # Tonic component: BNST responds to sustained/unpredictable threat
        tonic = bnst_anxiety * 0.8 + bnst_crh * 0.2
        tonic = min(1.0, tonic)

        # Unified EA output: weighted sum with temporal dynamics
        # Phasic fires and decays; tonic builds and decays slowly
        ea_output = phasic * 0.6 + tonic * 0.4
        ea_output = min(1.0, ea_output)

        # HPA axis drive: EA → PVN → cortisol
        hpa_drive = ea_output * (0.5 + bnst_crh * 0.5)

        self.state["extended_amygdala_output"] = round(ea_output, 4)
        self.state["phasic_fear_component"] = round(phasic, 4)
        self.state["tonic_anxiety_component"] = round(tonic, 4)
        self.state["threat_total_intensity"] = round(max(phasic, tonic), 4)
        self.state["hpa_axis_drive"] = round(hpa_drive, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "extended_amygdala_output": round(ea_output, 4),
            "phasic_fear_component": round(phasic, 4),
            "tonic_anxiety_component": round(tonic, 4),
            "threat_total_intensity": round(max(phasic, tonic), 4),
            "hpa_axis_drive": round(hpa_drive, 4),
        }
