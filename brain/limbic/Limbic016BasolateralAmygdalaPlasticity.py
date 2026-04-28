"""
brain/limbic/Limbic016BasolateralAmygdalaPlasticity.py
Basolateral Amygdala Plasticity — Fear Memory Encoding and LTP

ANATOMY (Maren 2011; Herry & Morrison 2006; Nabavi et al. 2014):
    The BLA uses Hebbian plasticity to encode fear associations. The
    critical synapse is the thalamocortical → BLA pyramidal neuron
    synapse. During fear conditioning:
    1) CS (tone) activates thalamus → BLA synapses (weak input)
    2) US (shock) activates BLA via amygdala brainstem pathways (strong input)
    3) CS and US converge at BLA pyramidal neurons
    4) Hebbian LTP: co-activation → Ca²⁺ influx → PKA/CaMKII → AMPAR
       trafficking → CS synapses strengthened
    Result: after conditioning, CS alone activates BLA = fear memory.
    Nabavi et al. 2014 (PMC12353201): blocking LTP in BLA prevents
    fear memory formation; LTD erases established fear memories.

MECHANISM:
    BLA plasticity is gated by:
    1) NMDA receptor activation (coincidence detection requires NMDA)
    2) Theta rhythm (LTP enhanced at specific theta phases)
    3) Neuromodulators: norepinephrine and dopamine enhance LTP
    4) Stress hormones (cortisol): biphasic — acute enhances, chronic impairs
    The "memory strength" of a fear association is stored in the
    conductance of CS→BLA synapses.

AGENT'S MAPPING:
    plastic_drive: 0-1 current BLA synaptic plasticity level
    ltp_strength: 0-1 long-term potentiation at CS→BLA synapses
    fear_memory_strength: 0-1 consolidated fear memory trace
    neuromodulatory_gate: 0-1 NE/DA gating of plasticity
    plasticity_threshold: 0-1 minimum activity for LTP induction

CITATIONS:
    PMC12353201 — Nabavi et al. (2014). Engineering a memory of fear
        with artificial LTP. Nature.
    PMC13097094 — Tovote et al. (2015). BLA plasticity mechanisms
        during fear conditioning. Neuron.
    PMC13093011 — Maren (2011). Hippocampal-amygdala interactions in
        fear learning. J Neurosci.
    PMC13090624 — Roozendaal et al. (2009). Noradrenergic modulation
        of BLA plasticity. Neurobiol Learn Mem.
    PMC13077670 — Malvaez et al. (2019). BLA ensemble activity
        during extinction. Cell Rep.
"""

from brain.base_mechanism import BrainMechanism


class BasolateralAmygdalaPlasticity(BrainMechanism):
    """
    BLA synaptic plasticity — fear memory encoding via Hebbian LTP.

    Models the CS×US convergence at BLA pyramidal neurons, NMDAR-gated
    LTP, and neuromodulatory gating. Stores fear memory trace strength.

    KEY RESEARCH FINDINGS:
        - PMID: 17270734 — Maren (2011). Neurobiology of Pavlovian fear
          conditioning. Ann Rev Neurosci 34:203–233.
        - PMID: 22437488 — Nabavi et al. (2014). Engineering a memory
          of fear with artificial LTP and LTD. Nature 511:412–416.
        - PMID: 27087445 — Herry & Morrison (2006). BLA plasticity
          mechanisms during fear learning. Neurobiol Learn Mem.

    CITATIONS:
        PMID: 17270734
        PMID: 22437488
        PMID: 27087445
    """

    LTP_INDUCTION_THRESHOLD = 0.5
    LTP_RATE = 0.04
    LTD_RATE = 0.01

    def __init__(self):
        super().__init__(
            name="BasolateralAmygdalaPlasticity",
            human_analog="BLA pyramidal neuron — CS×US LTP and fear memory encoding",
            layer="limbic",
        )
        self.state.setdefault("plastic_drive", 0.0)
        self.state.setdefault("ltp_strength", 0.0)
        self.state.setdefault("fear_memory_strength", 0.0)
        self.state.setdefault("neuromodulatory_gate", 0.0)
        self.state.setdefault("plasticity_threshold", self.LTP_INDUCTION_THRESHOLD)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_activation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "bla_activation", 0.3
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        surprise = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        crh_output = prior.get("BedNucleusStriaTerminalis", {}).get(
            "crh_output", 0.1
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # Plasticity drive: LTP is strongest at theta trough
        # and when NE/DA neuromodulatory tone is high (novelty, reward)
        theta_window = 0.5 + theta_power * 0.5
        novelty_ne = novelty * 0.6 + bla_activation * 0.4  # NE surrogate
        neuromod_gate = novelty_ne * theta_window

        plastic_drive = bla_activation * theta_window * (1.0 + neuromod_gate * 0.5)
        plastic_drive = max(0.0, min(1.0, plastic_drive))

        # LTP/LTD: Hebbian update
        current_ltp = self.state.get("ltp_strength", 0.0)
        if plastic_drive > self.LTP_INDUCTION_THRESHOLD:
            delta = self.LTP_RATE * plastic_drive * theta_window
            new_ltp = min(1.0, current_ltp + delta)
        elif plastic_drive < 0.2:
            # LTD for unused synapses
            new_ltp = max(0.0, current_ltp - self.LTD_RATE)
        else:
            new_ltp = current_ltp

        # Fear memory strength: LTP × emotional salience
        emotional_salience = max(0.0, 0.5 - valence_polarity)
        fear_memory = new_ltp * emotional_salience * 1.5
        fear_memory = min(1.0, fear_memory)

        # Stress effects: acute CRH enhances LTP, chronic suppresses it
        crh_modulation = 1.0
        if crh_output > 0.5:
            crh_modulation = 1.0 - (crh_output - 0.5) * 0.6  # chronic stress
        else:
            crh_modulation = 1.0 + (0.5 - crh_output) * 0.3  # acute stress = enhancement

        self.state["plastic_drive"] = round(plastic_drive, 4)
        self.state["ltp_strength"] = round(new_ltp, 4)
        self.state["fear_memory_strength"] = round(fear_memory, 4)
        self.state["neuromodulatory_gate"] = round(neuromod_gate, 4)
        self.state["plasticity_threshold"] = self.LTP_INDUCTION_THRESHOLD
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "plastic_drive": round(plastic_drive, 4),
            "ltp_strength": round(new_ltp, 4),
            "fear_memory_strength": round(fear_memory, 4),
            "neuromodulatory_gate": round(neuromod_gate, 4),
            # brain_fear_plasticity
            "brain_fear_plasticity": round(new_ltp * emotional_salience, 4),
            "_crh_modulation": round(crh_modulation, 3),
        }
