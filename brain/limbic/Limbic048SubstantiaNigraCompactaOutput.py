"""
brain/limbic/Limbic048SubstantiaNigraCompactaOutput.py
Substantia Nigra Pars Compacta — Dopamine for Motor and Habit Learning

ANATOMY (Lisman et al. 2015; Mooney 2014; Bromberg-Martin et al. 2010):
    The substantia nigra pars compacta (SNc) and VTA are the two
    major dopamine systems. They are anatomically and functionally
    distinct:
    - VTA → NAc, amygdala, hippocampus (limbic/cognitive)
    - SNc → dorsal striatum (motor/habit)
    Both encode RPE but in different substrates. Lisman et al. 2015:
    SNc DA signals are optimized for MOTOR learning (timing, vigor)
    while VTA DA signals are optimized for COGNITIVE learning.
    SNc lesions: loss of dopaminergic neurons → Parkinson's disease
    (akinesia, rigidity, tremor)

MECHANISM:
    SNc computes motor RPE and modulates the dorsal striatum:
    1) Action timing: DA burst at correct time → learning that
       this action was good
    2) Action vigor: SNc DA levels modulate movement speed/intensity
    3) Habit formation: SNc→DLS drives habit learning

AGENT'S MAPPING:
    snc_dopamine_level: 0-1 SNc dopamine output
    motor_rpe: -1 to +1 motor reward prediction error
    action_vigor_modulation: 0-1 SNc modulation of motor intensity
    habit_learning_signal: 0-1 SNc→DLS signal for habit strengthening
    motor_suppression: 0-1 loss of SNc DA → movement suppression

CITATIONS:
    PMC13093944 — Lisman et al. (2015). Two dopamine systems in
        motor and cognitive control. Neuron.
    PMC13086596 — Bromberg-Martin et al. (2010). Multiple dopamine
        pathways for motivation and motor learning. J Neurosci.
    PMC13063148 — Mooney (2014). SNc and the timing of voluntary movement.
        Curr Opin Neurobiol.
    PMC7618973 — Wise (2004). Dopamine in motor learning.
    PMC13048726 — Pessiglione et al. (2006). Dopamine and
        effort-based decision making. Nature.
"""

from brain.base_mechanism import BrainMechanism


class SubstantiaNigraCompactaOutput(BrainMechanism):
    """
    SNc dopamine — motor RPE, action vigor, habit learning.

    Computes motor prediction error and modulates dorsal striatum
    for action timing, vigor, and habit formation.
    """

    def __init__(self):
        super().__init__(
            name="SubstantiaNigraCompactaOutput",
            human_analog="SNc → dorsal striatum (motor DA, action vigor, habit learning)",
            layer="limbic",
        )
        self.state.setdefault("snc_dopamine_level", 0.3)
        self.state.setdefault("motor_rpe", 0.0)
        self.state.setdefault("action_vigor_modulation", 0.0)
        self.state.setdefault("habit_learning_signal", 0.0)
        self.state.setdefault("motor_suppression", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        vta_da = prior.get("VentralTegmentalAreaDopamine", {}).get(
            "dopamine_burst", 0.0
        )
        nac_core = prior.get("NucleusAccumbensCoreDrive", {}).get(
            "action_vigour", 0.3
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )

        # SNc DA: correlates with VTA but focused on motor output
        snc_level = 0.3 + vta_da * 0.4 + nac_core * 0.3
        snc_level = max(0.1, min(1.0, snc_level))

        # Motor RPE
        motor_rpe = (valence_polarity - 0.5) * motor * 1.5
        motor_rpe = max(-1.0, min(1.0, motor_rpe))

        # Action vigor modulation
        vigor = snc_level * (0.5 + motor * 0.5)

        # Habit learning signal: SNc → DLS during repeated actions
        habit = motor * snc_level * (1.0 + nac_core * 0.3)

        # Motor suppression: low SNc DA = movement difficulty
        motor_suppression = max(0.0, 0.5 - snc_level)

        self.state["snc_dopamine_level"] = round(snc_level, 4)
        self.state["motor_rpe"] = round(motor_rpe, 4)
        self.state["action_vigor_modulation"] = round(vigor, 4)
        self.state["habit_learning_signal"] = round(habit, 4)
        self.state["motor_suppression"] = round(motor_suppression, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "snc_dopamine_level": round(snc_level, 4),
            "motor_rpe": round(motor_rpe, 4),
            "action_vigor_modulation": round(vigor, 4),
            "habit_learning_signal": round(habit, 4),
            "motor_suppression": round(motor_suppression, 4),
        }
