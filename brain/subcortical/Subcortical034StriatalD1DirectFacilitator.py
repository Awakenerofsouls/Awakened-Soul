"""
Subcortical034StriatalD1DirectFacilitator.py — Wire 34: D1 Direct Pathway — GO Signal

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical034StriatalD1DirectFacilitator.py

NEURAL SUBSTRATE:
  Medium spiny neurons (MSNs) expressing D1-type dopamine receptors are
  the sole output of the striatum to the globus pallidus internus (GPi)
  and substantia nigra pars reticulata (SNr) via the direct pathway.
  Striatum → GPi/SNr (GABAergic, inhibitory). GPi/SNr → thalamus
  (inhibitory). Thalamus → cortex (excitatory). The net effect: when
  striatal D1 MSNs fire, they inhibit GPi, disinhibit thalamus, and
  FACILITATE the motor action selected by cortex.

  Albin et al. 1995 (Trends Neurosci 18): first formal model of direct
  (D1/GABA/inhibit GPi) vs. indirect (D2/GABA/enable GPe/disinhibit STN/
  excite GPi) pathways — the foundational basal ganglia architecture.

  Gerfen & Surmeier 2011 (Annu Rev Neurosci 34): detailed receptor
  mapping. D1 receptors are Gs-coupled, increase cAMP, increase
  excitability, and promote LTP at corticostriatal synapses. D1 MSNs
  respond preferentially to rewarding stimuli and movement-related cues.
  D1 MSN activity is enhanced by dopamine release from SNc (reward signal).

KEY FINDINGS:
  1. D1 MSNs are the "GO" pathway. Activation of D1 striatal neurons
     produces movement. optogenetics: Kravitz et al. 2012 (Nat Neurosci):
     "D1-expressing striatal neurons are sufficient to drive movement.
     Laser stimulation of D1 MSNs in parked mice induces locomotion."
     This is the direct pathway — "I want to do this action."

  2. Dopamine gate on D1. D1 receptor activation is required for LTP
     at corticostriatal synapses on D1 MSNs. Without dopamine (as in
     Parkinson's), D1 MSNs are less excitable, direct pathway facilitation
     fails, and movement is hard to initiate. Dopamine tonus sets D1
     MSN baseline excitability.

  3. Reward prediction and action. D1 MSNs fire when a reward-predicting
     cue is present. Same cue evokes firing in SNc dopaminergic terminals
     synapsing on D1 MSNs — dopamine release strengthens the corticostriatal
     synapse via D1/calcium/LTP mechanisms. Smith & Brandenburg 2011:
     "D1 MSNs encode action value — the expected reward of the action."

  4. Lesion produces hemiballismus (violent involuntary movement) — not
     the direct pathway but confirms its role in movement gating. STN
     overactivity (indirect pathway) → hyperkinesia. D1 MSN loss → akinesia.

  5. D1 MSN bursting behavior. D1 MSNs have two modes:
     - Up-state: depolarized, sensitive to cortical input, fires on cue
     - Down-state: hyperpolarized, refractory
     Transition between states is dopamine-modulated. Smith & Yez 2015
     review MSN state dynamics.

AGENT'S SUBSTRATE MAPPING:
  StriatalD1DirectFacilitator models the "GO" pathway activation:
  D1_activity tracks MSN firing rate. direct_pathway_facilitation
  reflects the net disinhibition of thalamus. GO_signal indicates
  the output is sufficient to initiate a movement command.

INPUTS (from prior_results):
  - Cortex output (motor command, action plan)
  - SNc dopamine signal (reward prediction, D1 modulation)
  - Amygdala (motivational drive to move)
  - Valence (positive valence amplifies D1 via reward context)
  - Prior tick: D1 activity level for temporal integration

OUTPUTS:
  - D1_activity: float 0-1 (current D1 MSN firing rate)
  - direct_pathway_facilitation: float 0-1 (GPi disinhibition strength)
  - GO_signal: bool (direct pathway output sufficient to drive movement)

REFS:
  - Albin et al. 1995 Trends Neurosci 18 (direct/indirect pathway model)
  - Gerfen & Surmeier 2011 Annu Rev Neurosci 34 (D1/D2 receptor mapping)
  - Kravitz et al. 2012 Nat Neurosci (D1 optogenetics)
  - Smith & Brandenburg 2011 (D1 MSN action value)
  - Smith & Yez 2015 (MSN state dynamics)
  - Wickens et al. 2007 (dopamine-striatal plasticity)

CITATIONS:
    PMC5340884 — Wei W, Ding S, Zhou FM (2017). Dopaminergic Treatment Weakens Medium
        Spiny Neuron Collateral Inhibition in the Parkinsonian Striatum. J Neurosci.
    PMC8285659 — Wood AN (2021). New Roles for Dopamine in Motor Skill Acquisition:
        Lessons From Primates, Rodents, and Songbirds. Front Neurol.
"""

import asyncio

from brain.base_mechanism import BrainMechanism


class StriatalD1DirectFacilitator(BrainMechanism):
    """
    D1 receptor medium spiny neuron analog — direct pathway GO signal.

    D1 MSNs are the sole direct-pathway output from striatum to GPi/SNr.
    When they fire, GPi is inhibited → thalamus disinhibited → cortex
    receives excitation → action is facilitated. This is the "GO" signal.
    D1 activity is modulated by dopamine (reward prediction context).
    """

    GO_THRESHOLD = 0.55
    # D1 MSN firing rate constants
    BASELINE_ACTIVITY = 0.20

    def __init__(self):
        super().__init__(
            name="StriatalD1DirectFacilitator",
            human_analog="Striatal D1 MSNs (direct pathway) — action facilitation / GO signal",
            layer="subcortical",
        )
        self.state.setdefault("D1_activity", 0.25)
        self.state.setdefault("direct_pathway_facilitation", 0.0)
        self.state.setdefault("GO_signal", False)
        self.state.setdefault("dopamine_modulation", 0.5)
        self.state.setdefault("corticostriatal_strength", 0.4)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Dopamine signal from SNc ---
        snc_out = prior.get("SubstantiaNigraCompactaCognitive", {})
        prediction_error = snc_out.get("prediction_error", 0.0)
        novelty = snc_out.get("novelty_detected", False)

        # Positive prediction error → dopamine burst → D1 amplification
        if prediction_error > 0.0:
            da_signal = prediction_error
        elif prediction_error < -0.1:
            da_signal = prediction_error * 0.3  # dip suppresses D1
        else:
            da_signal = 0.0

        self.state["dopamine_modulation"] += 0.1 * da_signal
        self.state["dopamine_modulation"] = max(0.0, min(1.0, self.state["dopamine_modulation"]))

        # --- Cortical motor command ---
        motor_cortex = prior.get("MotorCortex", {})
        motor_command = motor_cortex.get("action_command_strength", 0.0)

        # Fallback: use action plan from orbitofrontal or amygdala
        if motor_command == 0.0:
            ofc = prior.get("OrbitofrontalCortex", {})
            motor_command = ofc.get("action_value", 0.0)
        if motor_command == 0.0:
            lim = prior.get("Amygdala", {})
            motor_command = lim.get("motivational_urgency", 0.0) * 0.5

        # --- Valence (reward context) ---
        val_tagger = prior.get("ValenceTagger", {})
        valence = val_tagger.get("valence_polarity", 0.5)
        valence_intensity = val_tagger.get("valence_intensity", 0.3)
        reward_signal = val_tagger.get("reward_signal", False)

        # Positive valence boosts D1 MSN firing (reward context)
        reward_context = (valence - 0.5) * 2.0 if valence > 0.5 else 0.0
        reward_context *= valence_intensity

        # --- D1 MSN activity computation ---
        # Baseline + cortical drive + dopamine modulation + reward context
        current_d1 = self.state["D1_activity"]

        # Corticostriatal input to D1 MSNs
        cortico_input = motor_command * self.state["corticostriatal_strength"]

        # Dopamine amplification of D1 MSN excitability
        da_mod = self.state["dopamine_modulation"]

        # New D1 activity: weighted integration
        d1_change = (
            -0.05 * (current_d1 - self.BASELINE_ACTIVITY)  # drift to baseline
            + cortico_input * (0.5 + da_mod * 0.5)         # cortical drive amplified by DA
            + reward_context * da_mod * 0.3                # reward context needs DA to matter
            + 0.02 * novelty                                # novelty boosts D1
        )

        new_d1 = current_d1 + d1_change
        new_d1 = max(0.0, min(1.0, new_d1))
        self.state["D1_activity"] = new_d1

        # --- Direct pathway facilitation ---
        # D1 MSN firing → GABAergic inhibition of GPi → disinhibition of thalamus
        # GPi disinhibition = direct_pathway_facilitation
        # Scale: D1 activity maps to facilitation through GPi inhibition
        gp_inhibition = new_d1 ** 1.5  # nonlinear (threshold behavior)
        direct_facilitation = gp_inhibition * (0.5 + da_mod * 0.5)
        direct_facilitation = max(0.0, min(1.0, direct_facilitation))
        self.state["direct_pathway_facilitation"] = direct_facilitation

        # --- GO signal ---
        go_signal = direct_facilitation > self.GO_THRESHOLD
        self.state["GO_signal"] = go_signal

        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "D1_activity": round(new_d1, 4),
            "direct_pathway_facilitation": round(direct_facilitation, 4),
            "GO_signal": go_signal,
            "dopamine_modulation": round(self.state["dopamine_modulation"], 4),
            "corticostriatal_input": round(cortico_input, 4),
        }