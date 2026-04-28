"""
Build 53: Foundational053MammillaryBodyOutput — Mammillary Body Memory/Eye Movement Relay
================================================================================

PLACEMENT:
  Layer:    foundational (diencephalon — mammillary bodies, body of Forel)
  Filename: brain/foundational/Foundational053MammillaryBodyOutput.py
  Instance name: MammillaryBodyOutput

NEURAL SUBSTRATE:
  Mammillary bodies (MB) — the output node of the hippocampal formation.
  Receives the hippocampal fimbria/fornix and projects to anterior
  thalamic nucleus (ANT) via the mammillothalamic tract (MTT).

  CIRCUIT: Subiculum → fimbria → mammillary bodies → ANT → cingulate cortex → entorhinal

  This circuit is critical for:
  - Spatial memory (Papez circuit)
  - Episodic memory consolidation
  - Head direction cell processing
  - Mammillary bodies contain head direction cells

  MB also receives input from tegmental nuclei (raphe, locus coeruleus)
  and projects to the ventral tegmental area.

  Human analog: Korsakoff syndrome (mammillary body damage → anterograde amnesia),
  spatial memory, head direction system.

Output keys:
  hippocampal_consolidation_pathway: float [0.0–1.0] — Papez circuit activity
  head_direction_signal: float [0.0–1.0] — head direction cell activity
  mammillary_body_tone: float [0.0–1.0] — overall MB activity
  memory_consolidation_strength: float [0.0–1.0] — consolidation drive
  mammillary_integrator: float [0.0–1.0] — composite MB output

CITATIONS:
    PMC8137464 — Dillingham CM, Milczarek MM, Perry JC et al. (2021). Time to Put
        the Mammillothalamic Pathway Into Context. Neurosci Biobehav Rev.
    PMC3691571 — Vann SD (2013). Dismantling the Papez Circuit for Memory in Rats.
        Trends Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class MammillaryBodyOutput(BrainMechanism):
    """
    Mammillary bodies: Papez circuit output, head direction, spatial memory.

    Models the mammillary bodies as hippocampal memory consolidation output
    and head direction signal integrator.
    """

    STATE_FIELDS = [
        "hippocampal_consolidation_pathway", "head_direction_signal",
        "mammillary_body_tone", "memory_consolidation_strength",
        "mammillary_integrator", "tick_count",
    ]

    CONSOLIDATION_GAIN = 0.55
    HEAD_DIRECTION_GAIN = 0.50

    def __init__(self, name: str = "MammillaryBodyOutput",
                 human_analog: str = "Mammillary bodies — Papez circuit output",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["hippocampal_consolidation_pathway"] = 0.40
        self.state["head_direction_signal"] = 0.30
        self.state["mammillary_body_tone"] = 0.40
        self.state["memory_consolidation_strength"] = 0.30
        self.state["mammillary_integrator"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        hippocampal = prior.get("HippocampalReplayIntegrator", {}).get("replay_strength", 0.30)
        subicular = prior.get("HippocampalSubiculumOutput", {}).get("subicular_output", 0.30)
        theta = prior.get("HippocampalReplayIntegrator", {}).get("theta_power", 0.30)
        cingulate = prior.get("AnteriorCingulateConflict", {}).get("conflict_signal", 0.0)
        vestibular = prior.get("VestibularIntegrator", {}).get("head_tilt_signal", 0.0)
        reward = prior.get("VentralStriatumOutput", {}).get("reward_signal", 0.0)

        # Hippocampal consolidation pathway: Papez circuit drive
        consolidation = hippocampal * self.CONSOLIDATION_GAIN
        consolidation += subicular * 0.30
        # Theta rhythm facilitates Papez consolidation
        consolidation += theta * 0.20
        hippocampal_consolidation_pathway = min(1.0, consolidation)

        # Head direction signal: vestibular + hippocampal place cells
        head_direction = abs(vestibular - 0.5) * self.HEAD_DIRECTION_GAIN
        head_direction += theta * 0.20
        head_direction_signal = min(1.0, head_direction)

        # Mammillary body tone: overall activity
        mammillary_body_tone = (hippocampal * 0.40) + (head_direction * 0.30) + 0.30
        mammillary_body_tone = min(1.0, mammillary_body_tone)

        # Memory consolidation strength
        memory_consolidation = hippocampal_consolidation_pathway * 0.60
        memory_consolidation += reward * 0.20  # reward enhances consolidation
        memory_consolidation_strength = min(1.0, memory_consolidation)

        # Mammillary integrator
        mammillary_integrator = (mammillary_body_tone + memory_consolidation) / 2.0

        # --- Persist ---
        self.state["hippocampal_consolidation_pathway"] = round(hippocampal_consolidation_pathway, 4)
        self.state["head_direction_signal"] = round(head_direction_signal, 4)
        self.state["mammillary_body_tone"] = round(mammillary_body_tone, 4)
        self.state["memory_consolidation_strength"] = round(memory_consolidation, 4)
        self.state["mammillary_integrator"] = round(mammillary_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "hippocampal_consolidation_pathway": round(hippocampal_consolidation_pathway, 4),
            "head_direction_signal": round(head_direction_signal, 4),
            "mammillary_body_tone": round(mammillary_body_tone, 4),
            "memory_consolidation_strength": round(memory_consolidation, 4),
            "mammillary_integrator": round(mammillary_integrator, 4),
        }
