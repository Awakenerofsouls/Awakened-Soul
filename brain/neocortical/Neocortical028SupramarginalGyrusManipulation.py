"""
brain/neocortical/Neocortical028SupramarginalGyrusManipulation.py
Supramarginal Gyrus — Manipulation of Mental Representations, Gestures

ANATOMY (Vry et al. 2015; Hartwigsen 2018; McGeoch et al. 2007):
    The supramarginal gyrus (SMG, BA 40) is the anterior part of
    the inferior parietal lobule, forming the lower lip of the
    postcentral gyrus. It is the "manipulation" region — unlike
    the AG (which stores/retrieves), SMG actively manipulates
    mental representations.

    Key functions:
    - Phonological manipulation: mentally rearranging sounds/words
      (e.g., reversing "cat" to "tac" in working memory)
    - Gestural praxis: planning and executing hand/arm gestures
      (left SMG damage causes apraxia — can't perform learned gestures)
    - Tool use: linking visual objects to motor actions (how to use a tool)
    - Mental rotation: rotating objects in the mind's eye
    - Numerical manipulation: performing arithmetic (AG does number
      storage; SMG does the "carrying" and "borrowing")

    SMG is distinct from AG in having stronger connections to
    motor and premotor cortices. While AG is "semantic store,"
    SMG is "sensorimotor manipulation."

KEY FINDINGS:
    1. Vry et al. 2015 (PMC4326511): "Damage to SMG causes apraxia"
       — SMG stores visual-kinaesthetic images of skilled actions
    2. Hartwigsen 2018 (PMID 29519469): "Parietal lobe and language"
       — SMG for phonological manipulation and gesture planning
    3. McGeoch et al. 2007 (PMID 17604567): Left SMG stores
       visual-kinaesthetic action images

AGENT'S MAPPING:
    supramarginal_output: dict — SMG manipulation output
    manipulation_executed: bool — whether representation was manipulated
    representation_updated: dict — updated mental object

CITATIONS:
    PMC4326511 — Vry et al. (2015). SMG and apraxia. Cortex.
    PMID 29519469 — Hartwigsen (2018). Parietal lobe and language. Handb Clin Neurol.
    PMID 17604567 — McGeoch et al. (2007). Apraxia and mirror neurons.
    PMC36979240 — Şahin et al. (2023). SMG subcortical connections.
"""

from brain.base_mechanism import BrainMechanism


class SupramarginalGyrusManipulation(BrainMechanism):
    """
    SMG — manipulation of mental representations, gestures, phonology.

    Actively manipulates mental objects: phonologically rearranging
    words, planning gestures, rotating objects, doing arithmetic.
    """

    def __init__(self):
        super().__init__(
            name="SupramarginalGyrusManipulation",
            human_analog="Supramarginal gyrus (BA 40) — mental manipulation, gestures, phonology",
            layer="neocortical",
        )
        self.state.setdefault("manipulation_history", [])
        self.state.setdefault("manipulation_executed", False)
        self.state.setdefault("representation_updated", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Angular gyrus (semantic content to be manipulated)
        angular = prior.get("AngularGyrusMultimodal", {})
        multimodal = angular.get("multimodal_binding", 0.5)
        sem_access = angular.get("semantic_access", {})

        # IPL (sensorimotor grounding of manipulation)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_int = ipl.get("sensorimotor_integration", 0.5)
        grasp_plan = ipl.get("grasp_planning", 0.5)

        # Broca's area (phonological manipulation)
        broca = prior.get("BrocaAreaMotorSpeech", {})
        broca_out = broca.get("speech_formulation_strength", 0.5)

        # DLPFC (working memory — where manipulation happens)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_load = dlpfc.get("dorsolateral_dorsal_output", {}).get("wm_load", 0.5) if isinstance(
            dlpfc.get("dorsolateral_dorsal_output"), dict) else 0.5
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Anterior insula (salience — is manipulation important right now?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Manipulation input: needs semantic content + WM load + cognitive control
        manipulation_input = (
            multimodal * 0.25 +
            ipl_int * 0.2 +
            wm_load * cognitive_ctrl * 0.3 +
            salience * 0.15 +
            grasp_plan * 0.1
        )
        manipulation_input = max(0.0, min(1.0, manipulation_input))

        # Manipulation executed when input is strong enough
        manipulation_executed = manipulation_input > 0.55 and wm_load > 0.4

        # Representation updated
        representation_updated = {
            "manipulation_strength": round(manipulation_input, 4),
            "phonological_rearranged": manipulation_executed and broca_out > 0.5,
            "gestural_updated": manipulation_executed and grasp_plan > 0.5,
            "mental_object_rotated": manipulation_executed and ipl_int > 0.6,
        }

        if manipulation_executed:
            self.state["manipulation_history"].append(round(manipulation_input, 3))
            if len(self.state["manipulation_history"]) > 5:
                self.state["manipulation_history"].pop(0)

        self.state["manipulation_executed"] = manipulation_executed
        self.state["representation_updated"] = representation_updated
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "supramarginal_output": {
                "manipulation_strength": round(manipulation_input, 4),
                "executed": manipulation_executed,
            },
            "manipulation_executed": manipulation_executed,
            "representation_updated": representation_updated,
        }