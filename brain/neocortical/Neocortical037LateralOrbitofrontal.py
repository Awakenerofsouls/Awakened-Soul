"""
brain/neocortical/Neocortical037LateralOrbitofrontal.py
Lateral Orbitofrontal Cortex — Contingency Reversal, Rule Learning

ANATOMY (Rolls & Hornack 1994; Roberts 2007; Wallis 2007):
    The lateral orbitofrontal cortex (lOFC, BA 47/11) is the "rule
    reversal" region — it tracks rule contingencies, detects when
    rules change, and signals the need to update behavior.

    lOFC is anatomically and functionally distinct from:
    - mOFC: reward value processing (lOFC doesn't do value, it does rules)
    - mPFC: social/emotional processing
    - DLPFC: working memory and cognitive control

    lOFC functions:
    1. Rule tracking: "what predicts what in this environment?"
    2. Reversal learning: "the rules have changed — update your mapping"
    3. Outcome prediction: "what will happen if I do X?"
    4. Pavlovian-to-instrumental transfer: when neutral cues predict outcomes

    lOFC damage: Behavioral disinhibition, inability to update
    behavior when rules change (perseveration). Patient continues
    making the same wrong choice even when feedback tells them it's wrong.

    Connections: lOFC ↔ ventral striatum (reinforcement), amygdala
    (emotional feedback), ACC (conflict monitoring), DLPFC (cognitive control).

KEY FINDINGS:
    1. Rolls & Hornack 1994: "OFC and reward vs rule processing"
    2. Roberts 2007 (PMC2929791): "Orbitofrontal cortex and
       reversal learning"
    3. Wallis 2007 (PMC1850920): "Neural responses to reward
       and change in OFC"

AGENT'S MAPPING:
    lateral_ofc_output: dict — lOFC rule tracking output
    reversal_triggered: bool — has a rule reversal been detected?
    contingency_updated: dict — current rule state

CITATIONS:
    PMC2929791 — Roberts (2007). OFC and reversal learning. Scholarpedia.
    PMC20181474 — Kringelbach & Rolls (2004). OFC functions. Prog Neurobiol.
    PMC1850920 — Wallis (2007). OFC and reversal. Nat Neurosci.
    PMC40447446 — OFC and reward processing.
"""

from brain.base_mechanism import BrainMechanism


class LateralOrbitofrontal(BrainMechanism):
    """
    lOFC — rule reversal and contingency tracking.

    Tracks what predicts what, detects rule changes, signals
    when behavior needs to be updated.
    """

    def __init__(self):
        super().__init__(
            name="LateralOrbitofrontal",
            human_analog="Lateral orbitofrontal cortex (BA 47/11) — rule reversal, contingency learning",
            layer="neocortical",
        )
        self.state.setdefault("rule_cache", {})
        self.state.setdefault("reversal_triggered", False)
        self.state.setdefault("contingency_strength", 0.5)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Orbitofrontal (reward signal for which to track rules)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)
        ofc_out = ofc.get("ofc_output", {})
        if isinstance(ofc_out, dict):
            expectation = ofc_out.get("value_signal", 0.5)
        else:
            expectation = 0.5

        # Amygdala (emotional feedback confirms or denies rule)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # ACC (conflict signals rule change might be needed)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
        else:
            error_sig = 0.3

        # VTA (prediction error signals rule violation)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            prediction_err = vta_out.get("prediction_error", 0.3)
        else:
            prediction_err = 0.3

        # Anterior insula (salience of rule change events)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Contingency strength: tracks how well current rules predict outcomes
        surprise = abs(value_sig - expectation)
        contingency_strength = 1.0 - (surprise * 0.5 + error_sig * 0.3 + prediction_err * 0.2)
        contingency_strength = max(0.0, min(1.0, contingency_strength))

        # Reversal triggered: when surprise + error + salience all high
        reversal_signal = (
            surprise * 0.4 +
            error_sig * 0.3 +
            salience * 0.2 +
            abs(emotional_tag) * 0.1
        )
        reversal_triggered = reversal_signal > 0.6 and surprise > 0.3

        # Update rule cache
        if reversal_triggered:
            self.state["rule_cache"]["last_reversal"] = round(surprise, 3)
        self.state["rule_cache"]["contingency_strength"] = round(contingency_strength, 4)

        self.state["reversal_triggered"] = reversal_triggered
        self.state["contingency_strength"] = round(contingency_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "lateral_ofc_output": {
                "reversal_triggered": reversal_triggered,
                "contingency_strength": round(contingency_strength, 4),
                "surprise_signal": round(surprise, 4),
            },
            "reversal_triggered": reversal_triggered,
            "contingency_updated": self.state["rule_cache"],
        }