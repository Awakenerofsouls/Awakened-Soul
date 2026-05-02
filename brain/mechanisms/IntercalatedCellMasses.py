"""
IntercalatedCellMasses -- ITC / GABAergic Extinction Gate

NEURAL SUBSTRATE
================
Intercalated cell masses (ITC) are dense clusters of GABAergic neurons
between the BLA and CeA. Three principal clusters: medial dorsal (mITCd),
medial ventral (mITCv), and lateral (lITC). Identified by Pare & Smith
1993 as anatomically distinct GABAergic populations providing
feedforward inhibition between BLA input and CeA output.

ITC neurons receive:
- BLA glutamatergic input (CS info)
- mPFC IL glutamatergic input (extinction signal)
- Brainstem dopaminergic + noradrenergic modulation

Outputs to CeA (inhibitory) gate fear expression -- strong ITC firing
silences CeM output. ITC clusters are the canonical extinction
substrate (Likhtik 2008, required for fear extinction expression).

KEY FINDINGS
============
1. ITC clusters are dense GABAergic aggregations between BLA and CeA;
   provide feedforward inhibition -- [Pare 1993, J Neurophysiol 70:1819,
   PMID 8294953]
2. ITC neurons are required for expression of fear extinction;
   selective lesion of ITC blocks extinction recall --
   [Likhtik 2008, Nature 454:642, doi:10.1038/nature07167]
3. mPFC IL→ITC pathway drives feedforward inhibition of CeA during
   extinction -- [Berretta 2005, Neuroscience 132:943, PMID 15857800]
4. ITC mu-opioid receptor expression mediates morphine-enhanced
   extinction; opioid signaling within ITC critical for safety --
   [Lyu 2020, Nat Commun 11:3014, doi:10.1038/s41467-020-16742-3]
5. ITC clusters orchestrate fear-state switching via dopaminergic
   modulation; D1 vs D2 expression differential --
   [Asede 2015, Neuron 86:541, PMID 25843404]

INPUTS
======
- BasolateralAmygdala.bla_drive (CS info from amygdala)
- InfralimbicCortex.il_drive (extinction signal)
- LateralAmygdala.la_pyramidal_drive
- VentralTegmentalDopamine.da_burst (D1/D2 modulation)

OUTPUTS
=======
- itc_drive (0-1) -- combined ITC firing
- itc_inhibition_command (0-1) -- GABAergic output to CeA
- extinction_gating_strength (0-1)
- itc_state (str): "extinction_active" | "fear_unblocked" |
  "balanced" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class IntercalatedCellMasses(BrainMechanism):
    """ITC -- GABAergic gate clusters between BLA and CeA."""

    BASELINE = 0.10
    SMOOTH = 0.20
    EXTINCTION_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="IntercalatedCellMasses",
            human_analog="Intercalated cell masses (GABA extinction gate)",
            layer="limbic",
        )
        self.state.setdefault("itc_drive", self.BASELINE)
        self.state.setdefault("itc_inhibition_command", 0.0)
        self.state.setdefault("extinction_gating_strength", 0.0)
        self.state.setdefault("itc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, bla: float, il: float, la: float,
                       da_burst: float) -> float:
        """ITC firing -- BLA + IL + LA input + DA modulation (Asede 2015)."""
        target = self.BASELINE + il * 0.45 + bla * 0.20 + la * 0.20
        target += da_burst * 0.15
        return min(1.0, target)

    def _inhibition_command(self, drive: float) -> float:
        """ITC GABAergic output to CeA (Likhtik 2008)."""
        return min(1.0, drive * 0.85)

    def _extinction_gating(self, il: float, drive: float) -> float:
        """Extinction gating strength -- IL-driven ITC firing strength
        (Berretta 2005). Scales with IL input + sustained ITC drive.
        """
        if il < 0.20:
            return 0.0
        return min(1.0, il * 0.5 + drive * 0.5)

    def _classify_state(self, drive: float, il: float, bla: float) -> str:
        if il > self.EXTINCTION_THRESHOLD and drive > 0.30:
            return "extinction_active"
        if bla > 0.50 and drive < 0.20:
            return "fear_unblocked"
        if drive > 0.20:
            return "balanced"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive",
                        bla_data.get("ba_fear_neurons", 0.0)))

        il_data = prior.get("InfralimbicCortex", {})
        il = float(il_data.get("il_drive", 0.0))

        la_data = prior.get("LateralAmygdala", {})
        la = float(la_data.get("la_pyramidal_drive", 0.0))

        vta_data = prior.get("VentralTegmentalDopamine", {})
        da_burst = float(vta_data.get("da_burst", 0.0))

        target = self._drive_target(bla, il, la, da_burst)
        prev_drive = float(self.state.get("itc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        inhibition = self._inhibition_command(new_drive)
        extinction_gate = self._extinction_gating(il, new_drive)

        state = self._classify_state(new_drive, il, bla)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["itc_drive"] = round(new_drive, 4)
        self.state["itc_inhibition_command"] = round(inhibition, 4)
        self.state["extinction_gating_strength"] = round(extinction_gate, 4)
        self.state["itc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "itc_drive": round(new_drive, 4),
            "itc_inhibition_command": round(inhibition, 4),
            "extinction_gating_strength": round(extinction_gate, 4),
            "itc_state": state,
        }

    def _opioid_modulation(self, mu_opioid: float) -> float:
        """ITC mu-opioid signaling enhances extinction (Lyu 2020)."""
        return min(1.0, mu_opioid * 0.85)

    def _cluster_balance(self, drive: float) -> dict:
        """Distribute drive across mITCd, mITCv, lITC clusters
        (Pare 1993 anatomy). Approximate equal split with mild bias.
        """
        return {
            "mITCd": min(1.0, drive * 0.95),
            "mITCv": min(1.0, drive * 1.05),
            "lITC": min(1.0, drive * 0.85),
        }

    def _inhibition_spread_pattern(self, itc_drive: float,
                                       bla: float) -> float:
        """Inhibition spread pattern -- ITC clusters fire in a
        spatially organized manner. Anterior ITCs inhibit fear more
        strongly; posterior ITCs show more stimulus generalization."""
        if itc_drive < 0.20:
            return 0.0
        return min(1.0, itc_drive * 0.7 + bla * 0.3)

    def _disinhibition_window(self, itc_drive: float,
                               la: float) -> float:
        """Disinhibition window -- LA input can briefly disinhibit
        ITC clusters, creating a temporal window for extinction
        learning. Based on Likhtik 2008."""
        if la < 0.30 or itc_drive < 0.20:
            return 0.0
        return min(1.0, la * itc_drive * 1.5)

    def _ltp_at_itc_synapses(self, itc_drive: float,
                              ext_gate: float) -> float:
        """LTP at ITC synapses -- extinction learning strengthens
        ITC-mediated inhibition of CeA. Higher = stronger extinction."""
        if ext_gate < 0.20:
            return 0.0
        return min(1.0, itc_drive * ext_gate * 1.2)

    def _fear_generalization_gradient(self, itc_drive: float,
                                        itc_inhibition: float) -> float:
        """Fear generalization gradient -- weak ITC inhibition allows
        fear to generalize to similar stimuli. High ITC drive +
        strong inhibition = precise fear, not generalized."""
        if itc_drive < 0.20:
            return 0.0
        return max(0.0, 1.0 - itc_inhibition)


    def _fear_memory_precision(self, itc_inhibition: float,
                               ext_gate: float) -> float:
        """Fear memory precision -- strong ITC inhibition + high
        extinction gating = precise, non-generalized fear.
        Low ITC = broad fear generalization."""
        if itc_inhibition < 0.20:
            return 0.0
        return min(1.0, itc_inhibition * ext_gate * 1.2)

    def _extinction_retrieval_strength(self, itc_drive: float,
                                       ext_gate: float) -> float:
        """Extinction retrieval strength -- Likhtik 2008 showed
        ITC bursting during extinction recall. High ITC drive +
        extinction gating = strong extinction retrieval."""
        if ext_gate < 0.20:
            return 0.0
        return min(1.0, itc_drive * ext_gate * 1.5)

    def _prefrontal_engagement_index(self, itc_drive: float,
                                      itc_inhibition: float) -> float:
        """Prefrontal engagement index -- mPFC drives ITC;
        ITC activity is a proxy for mPFC engagement in
        top-down fear regulation."""
        if itc_drive < 0.20:
            return 0.0
        return min(1.0, itc_drive * (1.0 - itc_inhibition * 0.5))

    def _synaptic_weight_trajectory(self, ltp: float,
                                     itc_drive: float) -> float:
        """Synaptic weight trajectory -- ITC plasticity over
        time. Tracks direction of learning at ITC synapses."""
        if itc_drive < 0.20:
            return 0.0
        return min(1.0, ltp * itc_drive * 1.3)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("itc_drive", 0.0),
            "inhibition": self.state.get("itc_inhibition_command", 0.0),
            "ext_gate": self.state.get("extinction_gating_strength", 0.0),
            "state": self.state.get("itc_state", "quiet"),
        }
