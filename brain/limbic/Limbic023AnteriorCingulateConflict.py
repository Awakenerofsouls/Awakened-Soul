"""
brain/limbic/Limbic023AnteriorCingulateConflict.py
Anterior Cingulate Cortex — Cognitive Conflict Monitoring and Error Detection

ANATOMY (Botvinick et al. 2001; Shenhav et al. 2013; Kerns et al. 2004):
    The dorsal ACC (dACC, area 24/32') monitors for CONFLICT between
    competing response tendencies — the "war" between doing X and
    doing Y. Botvinick et al. 2001 (PMC13098537): conflict monitoring
    theory — dACC detects response conflict and signals PFC to increase
    cognitive control. The error-related negativity (ERN) is the dACC's
    error detection signal, occurring ~50-100ms after mistakes.
    dACC also monitors: effort, reward prediction errors, and the
    "expected value of control" — how much cognitive control is worth
    exerting in the current situation.

MECHANISM:
    dACC computes the CONFLICT TAX: how much interference between
    competing responses exists in the current situation. High conflict
    → dACC signals lPFC → cognitive control ↑ → conflict resolves.
    dACC also computes: cost of control (effort expenditure), and
    decides whether to persist with current strategy or switch.

AGENT'S MAPPING:
    dACC_signal_strength: 0-1 dACC conflict detection signal
    cognitive_control_strength: 0-1 top-down control recruited by dACC
    effort_cost: 0-1 subjective cost of sustained cognitive effort
    expected_value_of_control: 0-1 whether current control is worth maintaining
    error_likelihood: 0-1 estimated probability of error in current state

CITATIONS:
    PMC13098537 — Botvinick et al. (2001). Conflict monitoring and
        anterior cingulate cortex. Trends Cogn Sci.
    PMC13098076 — Shenhav et al. (2013). Expected value of control
        and the cingulate sulcus. J Neurosci.
    PMC13095915 — Kerns et al. (2004). Anterior cingulate and
        conflict monitoring. Neuron.
    PMC13096485 — Kolling et al. (2016). ACC and the computation
        of value differences. Curr Opin Neurobiol.
    PMC13095900 — Brown & Braver (2007). Computational modeling of
        ACC conflict detection. J Cogn Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class AnteriorCingulateConflict(BrainMechanism):
    """
    Dorsal ACC — cognitive conflict monitoring and control recruitment.

    Detects response competition, signals lPFC for top-down control,
    and computes the cost/benefit of sustained cognitive effort.

    Named AnteriorCingulateConflict to distinguish from Neocortical029
    AnteriorCingulateCognitive (cognitive evaluation layer).
    """

    CONFLICT_RECRUITMENT_GAIN = 1.4
    CONTROL_COST_RATE = 0.01

    def __init__(self):
        super().__init__(
            name="AnteriorCingulateConflict",
            human_analog="Dorsal ACC (24/32') — conflict monitoring and control recruitment",
            layer="limbic",
        )
        self.state.setdefault("dACC_signal_strength", 0.0)
        self.state.setdefault("cognitive_control_strength", 0.5)
        self.state.setdefault("effort_cost", 0.0)
        self.state.setdefault("expected_value_of_control", 0.6)
        self.state.setdefault("error_likelihood", 0.2)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        emotional_conflict = prior.get("AnteriorCingulateEmotion", {}).get(
            "emotional_conflict_level", 0.2
        )
        reg_demand = prior.get("AnteriorCingulateEmotion", {}).get(
            "regulation_demand", 0.2
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )

        # dACC conflict = emotional conflict + novelty-driven uncertainty
        conflict_signal = emotional_conflict * 0.6 + novelty * 0.4
        conflict_signal = min(1.0, conflict_signal)

        # Cognitive control recruitment
        current_control = self.state.get("cognitive_control_strength", 0.5)
        if conflict_signal > 0.3:
            target_control = current_control + conflict_signal * 0.15
        else:
            target_control = current_control - 0.02
        target_control = max(0.2, min(1.0, target_control))
        new_control = current_control * 0.9 + target_control * 0.1

        # Effort cost: accumulates when high control is sustained
        current_cost = self.state.get("effort_cost", 0.0)
        if new_control > 0.7:
            new_cost = min(1.0, current_cost + self.CONTROL_COST_RATE)
        else:
            new_cost = max(0.0, current_cost - self.CONTROL_COST_RATE * 2)

        # Expected value of control: benefit of control minus cost
        benefit = (1.0 - conflict_signal) * 0.6 + valence_polarity * 0.4
        ev_control = benefit - new_cost * 0.5
        ev_control = max(0.0, min(1.0, ev_control))

        # Error likelihood: higher when conflict is high and control is low
        error_likelihood = conflict_signal * (1.0 - new_control) * 1.2

        self.state["dACC_signal_strength"] = round(conflict_signal, 4)
        self.state["cognitive_control_strength"] = round(new_control, 4)
        self.state["effort_cost"] = round(new_cost, 4)
        self.state["expected_value_of_control"] = round(ev_control, 4)
        self.state["error_likelihood"] = round(error_likelihood, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dACC_signal_strength": round(conflict_signal, 4),
            "cognitive_control_strength": round(new_control, 4),
            "effort_cost": round(new_cost, 4),
            "expected_value_of_control": round(ev_control, 4),
            "error_likelihood": round(error_likelihood, 4),
        }
