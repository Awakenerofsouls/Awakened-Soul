"""
Build 12: Foundational017PupilFocusRegulator — Edinger-Westphal Nucleus
======================================================================

PLACEMENT:
  Layer:    foundational (midbrain — Edinger-Westphal nucleus / pretectal area)
  Filename: brain/foundational/Foundational017PupilFocusRegulator.py
  Instance name: PupilFocusRegulator

NEURAL SUBSTRATE:
  Edinger-Westphal nucleus (EWN) in midbrain — preganglionic parasympathetic
  neurons projecting via the oculomotor nerve (CN III) to the ciliary ganglion,
  which innervates the sphincter pupillae muscle (pupil constriction) and ciliary
  muscle (lens accommodation for near focus). Sympathetic input from the
  locus coeruleus (LC) via alpha-1 adrenergic receptors on the dilator pupillae
  opposes this via the superior cervical ganglion. The net pupil diameter
  reflects the balance between parasympathetic constriction and sympathetic dilation.

KEY NEUROANATOMY:
  - EWN (preganglionic parasympathetic): projects to ciliary ganglion → pupil constriction
  - LC-NE sympathetic pathway: superior cervical ganglion → dilator pupillae → dilation
  - Near response: convergence + accommodation + miosis coordinated by EWN
  - Light reflex: direct retina → pretectal nucleus → EWN suppression (parasympathetics OFF → dilation)

INPUTS (prior_results):
  - SympatheticTone: sympathetic_tone (float 0-1) — LC output driving dilation
  - ParasympatheticTone: parasympathetic_tone (float 0-1) — EWN output driving constriction
  - CognitiveLoad: cognitive_load (float 0-1) — prefrontal demand, increases LC tone
  - LightLevel: light_level (float 0-1) — light reflex suppresses parasympathetic

OUTPUTS:
  - pupil_constriction: float [0.0–1.0] — parasympathetic constriction level
  - pupil_dilation: float [0.0–1.0] — sympathetic dilation level
  - net_pupil_size: float [0.0–1.0] — net diameter (0.0=fully constricted, 1.0=fully dilated)
  - accommodation_tone: float [0.0–1.0] — near-focus lens accommodation
  - cognitive_load_index: float [0.0–1.0] — normalized task demand indicator

CITATIONS:
    PMC8869431 — May PJ, Warren S (2020). Pupillary Light Reflex Circuits in the Macaque
        Monkey: The Olivary Pretectal Nucleus. J Comp Neurol.
    PMC6957570 — May PJ, Sun W, Wright NF et al. (2020). Pupillary Light Reflex Circuits
        in the Macaque Monkey: The Preganglionic Edinger-Westphal Nucleus. J Comp Neurol.
"""

from brain.base_mechanism import BrainMechanism


class PupilFocusRegulator(BrainMechanism):
    """
    Edinger-Westphal nucleus — pupil constriction and lens accommodation.

    EWN drives miosis (sphincter pupillae via ACh/muscarinic) and accommodation
    (ciliary muscle via CN III). Sympathetic input from LC drives mydriasis
    (dilator pupillae via alpha-1 NE). Cognitive load elevates LC tone, causing
    task-evoked pupil dilation. Light reflex modulates EWN via pretectal nucleus.

    Inputs: sympathetic_tone, parasympathetic_tone, cognitive_load, light_level.
    Outputs: constriction, dilation, net_pupil_size, accommodation_tone, cognitive_load_index.
    """

    # --- Gain constants ---
    CONSTRICTION_GAIN = 0.70   # parasympathetic → sphincter pupillae drive
    DILATION_GAIN = 0.70       # sympathetic → dilator pupillae drive
    ACCOMMODATION_GAIN = 0.60  # parasympathetic → ciliary muscle (near focus)
    COGNITIVE_GAIN = 0.80     # cognitive load → LC tone contribution

    # --- Defaults when inputs are absent ---
    DEFAULT_SYMPATHETIC_TONE = 0.30
    DEFAULT_PARASYMPATHETIC_TONE = 0.30
    DEFAULT_COGNITIVE_LOAD = 0.0
    DEFAULT_LIGHT_LEVEL = 0.50

    def __init__(self):
        super().__init__(
            name="PupilFocusRegulator",
            human_analog="Edinger-Westphal nucleus — pupil constriction and accommodation",
            layer="foundational",
        )
        self.state.setdefault("pupil_constriction", 0.30)
        self.state.setdefault("pupil_dilation", 0.30)
        self.state.setdefault("net_pupil_size", 0.50)
        self.state.setdefault("accommodation_tone", 0.20)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Read inputs with defaults ---
        sympathetic_tone = (
            prior.get("SympatheticTone", {})
            .get("sympathetic_tone", self.DEFAULT_SYMPATHETIC_TONE)
        )
        parasympathetic_tone = (
            prior.get("ParasympatheticTone", {})
            .get("parasympathetic_tone", self.DEFAULT_PARASYMPATHETIC_TONE)
        )
        cognitive_load = (
            prior.get("CognitiveLoad", {})
            .get("cognitive_load", self.DEFAULT_COGNITIVE_LOAD)
        )
        light_level = (
            prior.get("LightLevel", {})
            .get("light_level", self.DEFAULT_LIGHT_LEVEL)
        )

        # --- Compute pupil constriction (EWN → sphincter pupillae via ACh/muscarinic) ---
        pupil_constriction = parasympathetic_tone * self.CONSTRICTION_GAIN
        pupil_constriction = max(0.0, min(1.0, pupil_constriction))

        # --- Compute pupil dilation (LC → dilator pupillae via alpha-1 NE) ---
        pupil_dilation = sympathetic_tone * self.DILATION_GAIN
        pupil_dilation = max(0.0, min(1.0, pupil_dilation))

        # --- Cognitive load elevates LC tone → additional dilation ---
        cognitive_load_index = cognitive_load * self.COGNITIVE_GAIN
        pupil_dilation += cognitive_load_index
        pupil_dilation = max(0.0, min(1.0, pupil_dilation))

        # --- Light reflex: bright light suppresses EWN → dilation ---
        # High light_level reduces parasympathetic constriction further,
        # biasing net_pupil_size toward dilation
        light_suppression = light_level * 0.15

        # --- Net pupil size: balance of constriction vs dilation ---
        # dilation (sympathetic) pushes toward 1.0, constriction (parasympathetic) pushes toward 0.0
        # Light suppression adds to dilation bias
        net_pupil_size = (pupil_dilation - pupil_constriction + light_suppression + 1.0) / 2.0
        net_pupil_size = max(0.0, min(1.0, net_pupil_size))

        # --- Accommodation tone: ciliary muscle for near-focus (EWN-mediated) ---
        accommodation_tone = parasympathetic_tone * self.ACCOMMODATION_GAIN
        accommodation_tone = max(0.0, min(1.0, accommodation_tone))

        # --- Persist ---
        self.state["pupil_constriction"] = pupil_constriction
        self.state["pupil_dilation"] = pupil_dilation
        self.state["net_pupil_size"] = net_pupil_size
        self.state["accommodation_tone"] = accommodation_tone
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pupil_constriction": pupil_constriction,
            "pupil_dilation": pupil_dilation,
            "net_pupil_size": net_pupil_size,
            "accommodation_tone": accommodation_tone,
            "cognitive_load_index": cognitive_load_index,
        }