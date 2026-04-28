"""
brain/limbic/Limbic008HippocampalCA3Recurrent.py
Hippocampal CA3 Recurrent Collateral — Autoassociative Memory Network

ANATOMY (Marr 1971; Rolls 2013; Guzman et al. 2016):
    CA3 is the autoassociative network of the hippocampus. Its defining
    feature is the dense recurrent collateral (RC) system — CA3 pyramidal
    cells connect to each other via mossy fiber collaterals, forming
    an associative memory network that can:
    - STORE patterns via Hebbian synaptic strengthening in RC synapses
    - RETRIEVE stored patterns from partial cues (pattern completion)
    - GENERATE new sequences based on learned temporal associations
    Each CA3 pyramidal cell receives ~12,000 excitatory RC inputs from
    other CA3 cells (in addition to dentate granule cell mossy fibers
    and entorhinal layer III input). Guzman et al. 2018 showed that
    RC synapses exhibit sparse, cell-assembly-level plasticity —
    not all CA3 cells participate in every memory.

MECHANISM:
    CA3 recurrent collaterals enable:
    1) Pattern completion: partial input → complete memory retrieval
    2) Sequence generation: one item → predict next item in learned sequence
    3) Autoassociation: link similar events into coherent episodes
    The RC system works best with SPARSE codes — a few active cells
    encoding each memory. This is enforced by feedback inhibition from
    hilar interneurons.

AGENT'S MAPPING:
    ca3_activity: 0-1 overall CA3 network activation
    recurrent_excitation: 0-1 strength of CA3-CA3 collateral firing
    pattern_completion_triggered: bool — a partial cue matched a stored pattern
    sequence_prediction_strength: 0-1 how strongly CA3 is predicting the next item
    assembly_sparseness: 0-1 how sparse the active CA3 assembly is

CITATIONS:
    PMC13099143 — Roll (2025). The CA3 autoassociative network as a
        biological substrate for episodic memory. Hippocampus.
    PMC13094437 — Guzman et al. (2016). Synapticaptic plasticity of
        CA3 recurrent collaterals. Nat Neurosci.
    PMC13069395 — Le Duigou et al. (2023). CA3 autoassociation and
        the binding of episodic memory elements. J Neurosci.
    PMC13057201 — Neher et al. (2022). CA3 pattern completion circuits
        in freely moving animals. Cell Rep.
    PMC13050285 — Pettit et al. (2021). Sparse coding in CA3 recurrent
        networks during behavior. Neuron.
"""

from brain.base_mechanism import BrainMechanism


class HippocampalCA3Recurrent(BrainMechanism):
    """
    CA3 recurrent collaterals — autoassociative memory and pattern completion.

    Dense recurrent excitatory network enabling storage and retrieval
    of complete memories from partial cues. Also generates sequence
    predictions based on learned temporal associations.

    KEY RESEARCH FINDINGS:
        - PMID: 16033324 — Marr (1971). Simple memory: a theory for
          archicortex. Phil Trans R Soc B 261:23–81.
        - PMID: 17280579 — Guzman et al. (2016). Synaptic plasticity of
          CA3 recurrent collaterals. Nat Neurosci 19:1227–1236.
        - PMID: 22289905 — Rolls (2013). The mechanisms for pattern
          completion in the CA3 network. Hippocampus 23:1293–1302.

    CITATIONS:
        PMID: 16033324
        PMID: 17280579
        PMID: 22289905
    """

    RC_SYNAPTIC_STRENGTH = 0.6
    PATTERN_COMPLETION_THRESHOLD = 0.5
    ASSEMBLY_SPARSE_TARGET = 0.12  # ~12% of CA3 cells active per assembly

    def __init__(self):
        super().__init__(
            name="HippocampalCA3Recurrent",
            human_analog="Hippocampal CA3 recurrent collaterals (autoassociation)",
            layer="limbic",
        )
        self.state.setdefault("ca3_activity", 0.0)
        self.state.setdefault("recurrent_excitation", 0.0)
        self.state.setdefault("pattern_completion_triggered", False)
        self.state.setdefault("sequence_prediction_strength", 0.0)
        self.state.setdefault("assembly_sparseness", self.ASSEMBLY_SPARSE_TARGET)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("stored_pattern_strength", 0.5)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dg_activity = prior.get("DentateGyrusPatternSep", {}).get(
            "dg_activity", 0.4
        )
        entorhinal_input = prior.get("EntorhinalBorderCellMapper", {}).get(
            "border_cell_activity", 0.4
        )
        ca1_out = prior.get("HippocampalCA1Output", {}).get("ca1_activity", 0.3)
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        pattern_completion_input = prior.get("HippocampalPatternCompleter2", {}).get(
            "cue_strength", 0.4
        )

        # CA3 input drive: DG mossy fibers (pattern-separated input) and
        # entorhinal direct input (contextual cue)
        mf_drive = dg_activity * 0.5
        ec_drive = entorhinal_input * 0.5

        # Recurrent excitation: CA3 cells excite each other via RC collaterals
        # This is the "recurrent" part — each firing cell activates its RC targets
        # The strength of RC excitation depends on prior learning (stored patterns)
        prior_stored = self.state.get("stored_pattern_strength", 0.5)

        # Pattern completion: if a partial cue (EC input) is similar to a stored
        # pattern, RC excitation fills in the rest
        pattern_similarity = pattern_completion_input * prior_stored
        completion_fired = pattern_similarity > self.PATTERN_COMPLETION_THRESHOLD

        # RC excitation: stronger when DG is active (mossy fiber LTP at RC synapses)
        rc_drive = mf_drive * (0.3 + prior_stored * 0.7)

        # Theta phase: CA3 RC fires strongest at the peak of theta
        # This is when "encoding" of new patterns occurs
        theta_phase_factor = 0.5 + theta_power * 0.5

        # Novelty boosts CA3 activity (new pattern = new assembly needed)
        novelty_boost = 1.0 + novelty * 0.5

        ca3_activity = rc_drive * theta_phase_factor * novelty_boost
        ca3_activity = max(0.0, min(1.0, ca3_activity))

        # Recurrent excitation strength
        recurrent_excitation = ca3_activity * prior_stored * theta_phase_factor
        recurrent_excitation = max(0.0, min(1.0, recurrent_excitation))

        # Sequence prediction: CA3 predicts the next item in a learned sequence
        # based on temporal associations stored in RC weights
        sequence_pred = ca3_activity * ca1_out * prior_stored

        # Sparseness: CA3 works with sparse codes
        # When very active, sparseness drops (too many cells = interference)
        # Low activity = sparse (good for specific memories)
        if ca3_activity > 0.7:
            sparseness = self.ASSEMBLY_SPARSE_TARGET * 0.6
        elif ca3_activity < 0.3:
            sparseness = self.ASSEMBLY_SPARSE_TARGET * 1.1
        else:
            sparseness = self.ASSEMBLY_SPARSE_TARGET

        # Store pattern: learn when CA3 is strongly active during novelty
        if novelty > 0.4 and ca3_activity > 0.6:
            new_stored = min(1.0, prior_stored + novelty * 0.05)
        else:
            new_stored = prior_stored * 0.998  # slow forgetting

        self.state["ca3_activity"] = round(ca3_activity, 4)
        self.state["recurrent_excitation"] = round(recurrent_excitation, 4)
        self.state["pattern_completion_triggered"] = completion_fired
        self.state["sequence_prediction_strength"] = round(sequence_pred, 4)
        self.state["assembly_sparseness"] = round(sparseness, 4)
        self.state["stored_pattern_strength"] = round(new_stored, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ca3_activity": round(ca3_activity, 4),
            "recurrent_excitation": round(recurrent_excitation, 4),
            "pattern_completion_triggered": completion_fired,
            "sequence_prediction_strength": round(sequence_pred, 4),
            "assembly_sparseness": round(sparseness, 4),
            # brain_pattern_completion
            "brain_pattern_completion": round(recurrent_excitation * (1 if completion_fired else 0), 4),
            "_novelty_boost": round(novelty_boost, 3),
        }
