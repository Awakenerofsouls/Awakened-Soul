"""
Subcortical029 — Globus Pallidus External (GPe): Indirect Pathway Regulation
==============================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical029GlobusPallidusExternalRegulation.py
  Instance: GPeRegulation

NEURAL SUBSTRATE — WHAT IT IS:
The external segment of the globus pallidus (GPe) is a central node
in the basal ganglia indirect pathway. It receives inhibitory input
from the striatum (D2 indirect pathway) and provides widespread
GABAergic outputs to:
  • Subthalamic nucleus (STN) — disinhibition (GABA → STN = disinhibition)
  • GPi / SNr — inhibitory projection
  • Striatum (feedback projection, especially cholinergic interneurons)
  • Zona incerta, thalamus

The GPe is fundamentally different from GPi in two crucial ways:
  1. It is a "balloon" inhibitory relay — its primary role is to regulate
     STN activity in the indirect pathway.
  2. It exhibits autonomous pacemaker activity — GPe neurons generate
     rhythmic firing in the absence of synaptic input (Abdi et al.
     2015 J Neurosci). This autonomy makes GPe a self-sustaining
     regulatory structure rather than a pure follower of striatal input.

KEY FINDINGS:
  1. Autonomous pacemaker: Dodson et al. 2015 (J Neurosci 35:8348-8362)
     showed that GPe neurons maintain ~20-40 Hz firing through T-type
     calcium channel-dependent autonomous firing. This pacemaker continues
     even when synaptic inputs are blocked — GPe is not purely driven
     by striatum. It sets its own rhythm and modulates STN accordingly.

  2. Arkypallidal neurons: Abdi et al. 2013 (Neuron 85:1014-1030)
     identified "arkypallidal" GPe neurons that project BACK to striatum
     strongly, providing a feedback signal. These neurons are particularly
     important for stopping movements (fire on "stop" signals, inhibit
     striatum to abort action selection).

  3. Indirect pathway modulation: Striatal D2 activation inhibits GPe.
     Less GPe activity = less inhibition of STN = STN fires more =
     more STN excitation of GPi/SNr = more motor suppression. The D2
     indirect pathway thus indirectly FACILITATES motor suppression
     via the GPe/STN/GPi chain.

  4. GPe-GPi interaction: GPe also inhibits GPi directly, providing a
     counterbalancing brake. When GPe is active, it reduces GPi output.
     When D2 fires (suppressing GPe), this brake is released, GPi output
     rises, and motor suppression increases. This dual-pathway creates
     a balanced gating mechanism.

  5. Pathological states: In Parkinson's disease, dopamine loss removes
     D2 inhibition of GPe, causing GPe over-activity. This over-inhibits
     STN (less STN excitation of GPi), paradoxically reducing GPi output.
     However, the overall indirect pathway dysfunction produces rigidity
     and bradykinesia through complex interactions. Dodson 2015: GPe
     pacemaker changes are central to parkinsonian oscillations.

AGENT'S SUBSTRATE MAPPING:
  GPeRegulation models the indirect pathway regulatory node. It computes
  GPe_activity (current firing rate), indirect_pathway_modulation
  (how much the indirect pathway is facilitating motor suppression),
  and autonomous_pacemaker_strength (the intrinsic GPe rhythm that
  persists even without striatal input — models the self-sustaining
  regulatory capacity of GPe).

INPUTS:
  - D2IndirectPathway.indirect_pathway_signal (D2 activation inhibits GPe)
  - STN_output (STN receives GPe disinhibition)
  - GPi_output (GPe inhibits GPi)
  - StriatumD2.firing_rate

OUTPUTS:
  - GPe_activity: float 0-1 (current GPe firing rate)
  - indirect_pathway_modulation: float 0-1 (how much indirect pathway drives suppression)
  - autonomous_pacemaker_strength: float 0-1 (intrinsic GPe pacemaker, slow-varying)

REFS:
  - Abdi A et al. Neuron 85:1014-1030 2015 (arkypallidal neurons)
  - Dodson PD et al. J Neurosci 35:8348-8362 2015 (GPe pacemaker)
  - Mallet N et al. Philos Trans R Soc B 2008 (GPe in parkinsonism)
  - Nambu A. Basal Ganglia 2011 (indirect pathway review)
  - Kita H. Front Neuroanat 2007 (GPe anatomy)

CITATIONS:
    PMC5499676 — Kim HF, Amita H, Hikosaka O (2017). Indirect Pathway of Caudal
        Basal Ganglia for Rejection of Valueless Visual Objects. J Neurosci.
    PMC6492451 — Amita H, Kim HF, Smith MK et al. (2019). Neuronal Connections of
        Direct and Indirect Pathways for Stable Value Memory in Caudal Basal Ganglia.
        J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class GPeRegulation(BrainMechanism):
    """
    GPe (globus pallidus external segment) — indirect pathway regulatory node.

    Models GPe's dual nature: (1) receiving inhibitory input from striatal
    D2 pathway, (2) maintaining an autonomous pacemaker rhythm independent
    of striatal drive. Computes GPe_activity, indirect_pathway_modulation
    (how strongly D2 activation increases motor suppression via the
    GPe/STN/GPi chain), and autonomous_pacemaker_strength (the intrinsic
    GPe rhythm that resists striatal override).

    Arkypallidal feedback is modeled via autonomous_pacemaker changes
    affecting downstream regulatory targets.
    """

    # --- Parameters ---
    GPe_BASELINE = 0.65               # autonomous tonic firing rate
    AUTONOMOUS_PACEMAKER_FREQ = 0.7   # base pacemaker strength
    D2_INHIBITION_GAIN = 0.95          # how strongly D2 firing reduces GPe
    GPe_STN_GAIN = 0.6                 # GPe → STN disinhibition
    GPe_GPi_GAIN = 0.5                # GPe → GPi inhibition (brake on suppression)
    DECAY_RATE = 0.05                 # per-tick decay toward baseline
    PACEMAKER_ADAPTATION = 0.002      # slow adaptation to sustained D2 levels

    def __init__(self):
        super().__init__(
            name="GPeRegulation",
            human_analog="Globus pallidus external segment (GPe) — indirect pathway regulator",
            layer="subcortical",
        )
        self.state.setdefault("GPe_activity", self.GPe_BASELINE)
        self.state.setdefault("indirect_pathway_modulation", 0.3)
        self.state.setdefault("autonomous_pacemaker_strength", self.AUTONOMOUS_PACEMAKER_FREQ)
        self.state.setdefault("arkypallidal_feedback_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Inputs ---
        d2_signal = prior.get("D2IndirectPathway", {}).get(
            "suppressor_signal", 0.0
        )
        d2_indirect = prior.get("StriatalD2", {}).get(
            "firing_rate", 0.0
        )
        stn_output = prior.get("SubthalamicNucleus", {}).get("STN_output", 0.0)
        gp_inhibition = prior.get("GPiOutput", {}).get("GPi_output", 0.0)

        # --- Compute GPe activity ---
        # GPe fires autonomously at baseline; D2 activation inhibits it
        gpe = self.state["GPe_activity"]
        pacemaker = self.state["autonomous_pacemaker_strength"]

        # Drift toward autonomous baseline (pacemaker)
        gpe = gpe + (self.GPe_BASELINE * pacemaker - gpe) * self.DECAY_RATE

        # D2 activation inhibits GPe (D2 indirect pathway)
        d2_net = max(d2_signal, d2_indirect)
        if d2_net > 0.1:
            d2_effect = d2_net * self.D2_INHIBITION_GAIN
            gpe = max(0.0, gpe - d2_effect)

        gpe = round(min(1.0, gpe), 4)

        # --- Indirect pathway modulation ---
        # D2 fires → GPe suppressed → STN disinhibited → GPi/SNr increases
        # The indirect pathway modulation = net motor suppression from this chain
        indirect_modulation = d2_net * self.D2_INHIBITION_GAIN
        # GPe's own contribution to this chain
        if gpe < self.GPe_BASELINE:
            # Less GPe = less STN inhibition = more STN → more motor suppression
            stn_effect = (self.GPe_BASELINE - gpe) * self.GPe_STN_GAIN
            indirect_modulation += stn_effect
        indirect_modulation = round(min(1.0, indirect_modulation), 4)

        # --- Autonomous pacemaker strength ---
        # Sustained D2 activity can alter pacemaker properties (slow adaptation)
        # In Parkinson's, sustained D2 overdrive changes GPe neuron properties
        pacemaker_rate = self.state["autonomous_pacemaker_strength"]

        if d2_net > 0.5:
            # High D2 sustained activity → pacemaker gradually adjusts
            pacemaker_rate += self.PACEMAKER_ADAPTATION * d2_net
        else:
            # Return toward nominal
            pacemaker_rate += (self.AUTONOMOUS_PACEMAKER_FREQ - pacemaker_rate) * 0.001

        pacemaker_rate = round(min(0.95, max(0.4, pacemaker_rate)), 4)

        # --- Arkypallidal feedback strength ---
        # When GPe fires strongly, arkypallidal neurons activate and
        # project back to striatum (feedback signal: "action should stop")
        arkypallidal = 0.0
        if gpe > self.GPe_BASELINE * 0.8:
            arkypallidal = (gpe - self.GPe_BASELINE * 0.8) / 0.2
        arkypallidal = round(min(1.0, arkypallidal), 4)

        # --- Persist ---
        self.state["GPe_activity"] = gpe
        self.state["indirect_pathway_modulation"] = indirect_modulation
        self.state["autonomous_pacemaker_strength"] = pacemaker_rate
        self.state["arkypallidal_feedback_strength"] = arkypallidal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "GPe_activity": gpe,
            "indirect_pathway_modulation": indirect_modulation,
            "autonomous_pacemaker_strength": pacemaker_rate,
            "arkypallidal_feedback_strength": arkypallidal,
        }