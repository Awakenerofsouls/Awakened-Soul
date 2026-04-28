"""
Subcortical052PutamenSensorimotorAutomation.py — Wire 52: Putamen Automation

Neural substrate: Putamen — sensorimotor loop, habit formation.

The putamen is the lateral component of the dorsal striatum (together
with caudate forming the striatum). It is the somatotopic motor portion
of the striatum — receiving dense input from M1, SMA, and premotor
cortex, and heavily involved in movement execution, skill automation,
and habit formation.

Graybiel 2008 is the landmark paper on habit formation: "Habituation
is a basic process by which organisms come to ignore neutral stimuli
and focus on salient ones, but habit learning in the basal ganglia
is not just a process of ignoring — it is an active process of
building behavioral programs." Yin 2009 established putamen as the
dorsolateral striatum (DLS) — the habit system complementary to
caudate's (DMS) goal-directed system.

KEY RESEARCH FINDINGS:
1. Somatotopic organization. The putamen has a complex somatotopic
   map. Hoover & Strick 1993: motor cortex projects somatotopically
   to putamen — arm representation dorsally, face/head ventrally. 
   Miyachi et al. 1997: different body parts are processed in
   different regions of putamen. The face area is most ventral.

2. Sensorimotor loop (Loop V). Alexander et al. 1986: the fifth
   cortico-striatal loop involves premotor/M1 → putamen → GPi/SNr →
   VA/VLo thalamus → M1/SMA. This is the "motor" loop, distinct
   from the cognitive loop (caudate). The putamen is the entry stage.

3. Habit formation and automation. Yin et al. 2004: "The dorsolateral
   striatum (putamen) is necessary for habit formation." Lesions of
   DLS prevent development of habitual lever pressing in rats even
   after extensive training. Habits become automated via DA-dependent
   plasticity at cortico-striatal synapses in putamen.

4. Chunking of motor sequences. Graybiel 1998: putamen-dependent
   chunking produces "motor chunks" — sequences of elementary movements
   bundled into a single behavioral unit. Once chunked, the sequence
   executes without conscious attention. "The putamen may be the
   locus of habit learning because it chunks sequences." (Graybiel
   2008)

5. Automation and deconnection from cognitive control. Hardwick
   et al. 2019 (meta-analysis, n=164): "Motor skill learning produces
   systematic, domain-specific changes in putamen activity." The
   putamen becomes increasingly active during early skill learning
   (cognitive phase) then becomes less active once habit is formed
   (automatic phase) — the "automatization" process.

6. Beta band oscillations. Brittain et al. 2012: putamen generates
   beta (13-30 Hz) oscillations during automatic movement. Excessive
   beta is a marker of Parkinson's (see STN). In healthy putamen,
   beta power increases during motor automaticity — reflecting
   "motor routine" engagement.

7. Automation strength tracking. The putamen can track how "ready"
   a motor program is for automatic execution. Once procedural 
   learning reaches asymptotic performance, the putamen signals 
   that the program can run with minimal cortical oversight.

8. Putamen in OCD and Tourette. The putamen is implicated in both:
   hyperactivity in OCD (symptom generation), hypoactivity in
   Parkinson's (bradykinesia), and abnormal activity in Tourette's
   (motor tics).

OUTPUTS:
  putamen_sensorimotor_signal: float 0-1 — putamen activation for movement
  habit_formation_weight: float 0-1 — cumulative habit strength
  automation_strength: float 0-1 — readiness for automatic execution

INPUTS:
  motor_cortex_input: M1/SMA activation
  reinforcement_signal: DA reward signal
  skill_repetition: repeated same action → automation
  motor_context: current movement phase (acquisition vs automatic)

CITATIONS:
    PMC2862890 — Ashby FG, Turner BO, Horvitz JC (2010). Cortical and Basal Ganglia
        Contributions to Habit Learning and Automaticity. Trends Cogn Sci.
    PMC8675130 — Alm PA (2021). The Dopamine System and Automatization of Movement
        Sequences: A Review With Relevance for Speech and Stuttering. Front Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class PutamenSensorimotorAutomation(BrainMechanism):
    """
    Putamen — sensorimotor loop, habit formation, skill automation.

    Implements the motor striatal loop (Loop V), supporting skill
    acquisition, chunking of motor sequences, and automatic execution.
    Dorsolateral striatum (DLS) emphasis.
    """

    MOTOR_ACTIVATION_RATE = 0.18
    HABIT_LEARNING_RATE = 0.03
    AUTOMATION_DECAY = 0.02
    SKILL_THRESHOLD = 0.65
    BETA_BAND_FREQ = 20.0  # Hz — motor automaticity marker

    def __init__(self):
        super().__init__(
            name="PutamenSensorimotorAutomation",
            human_analog="Putamen — sensorimotor striatum (DLS), habit system",
            layer="subcortical",
        )
        self.state.setdefault("putamen_sensorimotor_signal", 0.0)
        self.state.setdefault("habit_formation_weight", 0.3)
        self.state.setdefault("automation_strength", 0.0)
        self.state.setdefault("beta_power", 0.0)
        self.state.setdefault("chunk_strength", 0.0)
        self.state.setdefault("motor_automaticity", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor_cortex_input = input_data.get("motor_cortex_input", 0.4)
        reinforcement_signal = input_data.get("reinforcement_signal", 0.0)
        skill_repetition = input_data.get("skill_repetition", 0.0)
        motor_context = input_data.get("motor_context", "acquisition")
        motor_learning_rate = input_data.get("motor_learning_rate", 0.1)

        # --- Sensorimotor signal ---
        # Putamen fires with motor cortex input, amplified by DA reinforcement
        DA_gain = 1.0 + reinforcement_signal * 0.5
        base_signal = motor_cortex_input * DA_gain * 0.7
        skill_boost = skill_repetition * self.state["habit_formation_weight"] * 0.3
        raw_signal = base_signal + skill_boost
        putamen_sensorimotor_signal = max(0.0, min(1.0, raw_signal))

        # --- Habit formation ---
        # Repetition + reinforcement = habit weight increase (Yin 2009)
        # Habit develops during "acquisition" phase, consolidates in "automatic"
        if motor_context == "acquisition":
            habit_delta = self.HABIT_LEARNING_RATE * skill_repetition * reinforcement_signal
            # Repetition drives habit (Graybiel chunking)
            habit_delta += self.HABIT_LEARNING_RATE * 0.5 * skill_repetition
        else:
            # Automatic phase — habit already formed, stabilize
            habit_delta = 0.0

        new_habit_weight = self.state["habit_formation_weight"] + habit_delta
        self.state["habit_formation_weight"] = max(0.1, min(0.95, new_habit_weight))

        # --- Chunk formation ---
        # When motor pattern repeats, a chunk forms (Graybiel 2008)
        if skill_repetition > 0.6 and motor_cortex_input > 0.5:
            chunk_growth = 0.08 * self.state["habit_formation_weight"]
            self.state["chunk_strength"] = min(1.0, self.state["chunk_strength"] + chunk_growth)
        else:
            self.state["chunk_strength"] *= 0.97

        # --- Automation strength ---
        # Automation increases when: habit is strong + behavior is automatic context
        # Decreases when: motor novelty (new skill learning) disrupts habits
        if motor_context == "automatic" and self.state["chunk_strength"] > self.SKILL_THRESHOLD:
            # Skill ready for automatic execution
            auto_delta = 0.05 * self.state["chunk_strength"]
        else:
            auto_delta = -self.AUTOMATION_DECAY

        # Beta power: increases during automatic motor execution
        beta_phase = (self.state["tick_count"] * self.BETA_BAND_FREQ / 60.0) % 1.0
        beta_oscillation = 0.5 * (1.0 + (1.0 if beta_phase < 0.5 else -1.0))
        new_beta = beta_oscillation * (0.3 + 0.7 * self.state["motor_automaticity"])
        self.state["beta_power"] = max(0.0, min(1.0, new_beta))

        # Automation state
        new_auto = self.state["motor_automaticity"] + auto_delta
        if motor_learning_rate > 0.5:
            # New learning — temporarily disrupts automation
            new_auto -= 0.1
        self.state["motor_automaticity"] = max(0.0, min(1.0, new_auto))
        automation_strength = self.state["motor_automaticity"]

        self.state["putamen_sensorimotor_signal"] = putamen_sensorimotor_signal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "putamen_sensorimotor_signal": round(putamen_sensorimotor_signal, 4),
            "habit_formation_weight": round(self.state["habit_formation_weight"], 4),
            "automation_strength": round(automation_strength, 4),
            "beta_power": round(self.state["beta_power"], 4),
            "chunk_strength": round(self.state["chunk_strength"], 4),
            "motor_automaticity": round(self.state["motor_automaticity"], 4),
        }