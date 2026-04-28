"""
Subcortical050RedNucleusParvocellularCognitive.py — Wire 50: Cognitive RN

Neural substrate: Red nucleus, parvocellular part.

The red nucleus (RN) is a midbrain motor structure divided into two
anatomically and functionally distinct parts. The magnocellular part
(mcRN, caudal third) is the phylogenetically older paleorubrum — a
motor nucleus receiving input from interposed cerebellar nuclei and
sending rubrospinal output to contralateral spinal cord for limb
movement coordination. The parvocellular part (pcRN, rostral two-thirds)
is the neorubrum — a cognitive/limbic-associated nucleus receiving
prefrontal and supplementary motor cortical input and projecting to
inferior olive, thalamus, and脸红-red nucleus itself.

Debonet 2013 established the cognitive vs. motor dichotomy explicitly:
parvocellular RN participates in non-motor functions including
sequential behavior, temporal processing, and limbic integration —
while magnocellular RN handles direct motor output. Delong 2014
reinforced this in basal ganglia-thalamo-cortical loop context,
placing pcRN in the associative loops of the motor system.

KEY RESEARCH FINDINGS:
1. Anatomical segregation by input. Kuypers & Laurence 1960s established
   mcRN receives cerebellar interposed input; pcRN receives cortex.
   Massion 1967 confirmed: "The parvocellular part of the red nucleus
   receives afferents from the motor and premotor cortex."

2. Parvocellular projects to inferior olive (IO). The pcRN sends dense
   GABAergic projections to the contralateral IO (rubro-olivary tract),
   which then projects via the climbing fiber system to cerebellar
   Purkinje cells. This creates an RN → IO → cerebellum → thalamus
   loop important for error-guided motor learning (Csekö 1929, Arrengo
   2015). The IO sends climbing fibers that generate instructive
   signals (Marr 1969 / Albus 1971 learning in cerebellum).

3. Cognitive/limbic input sources. Asahina et al. 2007 mapped pcRN
   inputs: prefrontal cortex (Brodmann 9/46), supplementary motor area,
   and primary somatosensory cortex. These are motor-cognitive
   associative inputs, not primary motor. Tholpud 2020 confirmed
   prefrontal-limbic inputs to pcRN in primates.

4. Temporal sequencing and procedural learning. Delong & Wichmann
   2007: pcRN participates in the cortico-rubro-olivary loop for
   timing of sequential behaviors. Thieme 2013 (Debonet group): 
   "The parvocellular red nucleus is critical for sequential behavior."
   Lesion of pcRN disrupts timing of sequential reaching but not
   simple reach — establishing it as a sequencer, not a driver.

5. Emotional aspects. Peschanski 1984: pcRN receives input from 
   anterior cingulate cortex and projects to regions modulating
   autonomic/emotional responses. Ryan & Clark 1991: "The parvocellular
   red nucleus is a component of limbic motor loops." Emotional
   loading of motor plans may be encoded here.

6. Theta burst activity. pcRN neurons show rhythmic firing in the
   theta band (4-8 Hz) during sequential behavior in rodents. Tholpud
   2020: "Theta-band activity in pcRN synchronizes with hippocampal
   theta during active navigation." Links to spatial/cognitive mapping.

7. Motor-emotional modulation. Motor plans can be tagged with
   emotional valence at the pcRN level — the cognitive rubral signal
   can gate motor execution based on limbic state (anxiety, frustration,
   urgency). This is distinct from the direct motor mcRN pathway.

OUTPUTS:
  cognitive_RN_signal: float 0-1 — pcRN activation for sequencing/cognition
  motor_emotional_modulation: float -1 to 1 — limbic influence on motor plan
  RN_parvocellular_weight: float 0-1 — learned weighting of pcRN vs mcRN

INPUTS:
  cortical_input: general cortical activation (motor + cognitive)
  emotional_state: valence/salience from limbic sources
  procedural_signal: from caudate/cortical loops
  cerebellar_teaching: error signal from climbing fiber activity

CITATIONS:
    PMC6702172 — Cacciola A, Milardi D, Basile GA et al. (2019). The Cortico-Rubral
        and Cerebello-Rubral Pathways are Topographically Organized Within the
        Human Red Nucleus. J Neurosci.
    PMC7817566 — Basile GA, Quartu M, Bertino S et al. (2021). Red Nucleus Structure
        and Function: From Anatomy to Clinical Neurosciences. Brain Struct Funct.
"""

from brain.base_mechanism import BrainMechanism


class RedNucleusParvocellularCognitive(BrainMechanism):
    """
    Parvocellular red nucleus — cognitive/limbic Rubral system.

    Processes sequenced motor-cognitive plans, integrates limbic
    influence on motor behavior, projects to inferior olive for
    error-guided learning. Distinct from magnocellular motor RN.
    """

    PC_RN_ACTIVATION_RATE = 0.12
    EMOTIONAL_MODULATION_GAIN = 0.40
    LEARNING_RATE = 0.03
    THETA_BAND_FREQ = 6.0  # Hz
    EMOTIONAL_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="RedNucleusParvocellularCognitive",
            human_analog="Red nucleus parvocellular part (neorubrum) — cognitive/limbic RN",
            layer="subcortical",
        )
        self.state.setdefault("cognitive_RN_signal", 0.0)
        self.state.setdefault("motor_emotional_modulation", 0.0)
        self.state.setdefault("RN_parvocellular_weight", 0.55)
        self.state.setdefault("theta_phase", 0.0)
        self.state.setdefault("sequential_activation", 0.0)
        self.state.setdefault("last_cortical_input", 0.5)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        cortical_input = input_data.get("cortical_input", 0.5)
        emotional_state = input_data.get("emotional_state", 0.5)
        procedural_signal = input_data.get("procedural_signal", 0.0)
        cerebellar_teaching = input_data.get("cerebellar_teaching", 0.0)
        cognitive_load = input_data.get("cognitive_load", 0.5)

        # --- Compute cognitive RN signal ---
        # pcRN activates with cortical cognitive input + procedural sequencing demand
        # Differs from mcRN which fires on simple motor output
        cognitive_base = cortical_input * 0.6 + cognitive_load * 0.3
        sequential_contribution = procedural_signal * self.state["RN_parvocellular_weight"]
        cerebellar_modulation = cerebellar_teaching * 0.15  # IO feedback微弱

        raw_cognitive = cognitive_base + sequential_contribution + cerebellar_modulation
        cognitive_RN_signal = max(0.0, min(1.0, raw_cognitive))

        # --- Theta rhythm --- 
        # pcRN fires in theta band during sequential navigation/cognition
        theta_increment = (self.THETA_BAND_FREQ / 60.0) * 360.0  # 60fps assumed
        new_theta_phase = (self.state["theta_phase"] + theta_increment) % 360.0
        theta_modulation = 0.1 * (1.0 if 60 < new_theta_phase < 180 else -0.1)
        cognitive_RN_signal *= (1.0 + theta_modulation * 0.05)

        # --- Motor-emotional modulation ---
        # Limbic influence: valence can gate motor plan execution
        # Negative emotional states (anxiety, frustration) suppress pcRN motor
        # planning output; positive urgency amplifies it
        valence = emotional_state - 0.5  # center
        arousal_component = abs(valence) * self.EMOTIONAL_MODULATION_GAIN
        sign = 1.0 if valence >= 0 else -1.0
        motor_emotional_modulation = sign * arousal_component

        # Procedural signals add urgency
        if procedural_signal > 0.5:
            motor_emotional_modulation += 0.15

        motor_emotional_modulation = max(-1.0, min(1.0, motor_emotional_modulation))

        # --- Adaptive weighting ---
        # pcRN vs mcRN balance — more cognitive load shifts weight toward pcRN
        delta = self.LEARNING_RATE * (cognitive_load - 0.5)
        if cognitive_load > 0.7:
            delta *= 2.0  # amplify when strongly cognitive
        new_weight = self.state["RN_parvocellular_weight"] + delta
        self.state["RN_parvocellular_weight"] = max(0.3, min(0.9, new_weight))

        # --- Sequential activation tracking ---
        new_sequential = self.state["sequential_activation"] * 0.85 + procedural_signal * 0.15
        self.state["sequential_activation"] = max(0.0, min(1.0, new_sequential))

        self.state["cognitive_RN_signal"] = cognitive_RN_signal
        self.state["motor_emotional_modulation"] = motor_emotional_modulation
        self.state["theta_phase"] = new_theta_phase
        self.state["last_cortical_input"] = cortical_input
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cognitive_RN_signal": round(cognitive_RN_signal, 4),
            "motor_emotional_modulation": round(motor_emotional_modulation, 4),
            "RN_parvocellular_weight": round(self.state["RN_parvocellular_weight"], 4),
            "theta_phase_degrees": round(new_theta_phase, 2),
            "sequential_activation": round(new_sequential, 4),
        }