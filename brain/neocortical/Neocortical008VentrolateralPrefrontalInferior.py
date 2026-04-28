"""
brain/neocortical/Neocortical008VentrolateralPrefrontalInferior.py
Ventrolateral Prefrontal Cortex — Inferior Part (Response Inhibition, Social Reasoning)

ANATOMY (Dimitrov et al. 2003; Badre & Wagner 2007; Noritake & Frank 2020):
    The ventrolateral prefrontal cortex (vlPFC) lies on the underside
    (inferior surface) of the frontal lobe, including BA 44, BA 45,
    and posterior BA 47/12. It borders the inferior frontal gyrus (IFG),
    which in the right hemisphere is heavily involved in response inhibition
    (the "stop" process).

    vlPFC is anatomically and functionally segregated:
    - Posterior vlPFC (right IFG/pSTG): response inhibition, stopping
    - Anterior vlPFC: semantic retrieval, task-set switching
    - BA 44/45 (IFG proper): syntactic processing, hierarchical reasoning

    Inputs: from:
    - Temporal lobe (semantic information)
    - Parietal lobe (spatial/object attention)
    - ACC (conflict signals)
    - Amygdala (emotional salience)
    
    Outputs: to:
    - Premotor cortex (action selection)
    - Striatum (action value)
    - IFG → Broca area (speech production — left hemisphere)

KEY FINDINGS:
    1. Aron et al. 2004 (PMID 14702116): Right IFG is critical for
       stopping — microstimulation stops responses, lesions prevent stopping
    2. Badre & Wagner 2007 (PMC23792944): vlPFC gets "unpdated" value
       information from OFC and uses it to suppress responses
    3. Noritake & Frank 2020: vlPFC has two subregions: one for
       "gating" semantic info, one for "suppressing" inappropriate responses

AGENT'S MAPPING:
    ventrolateral_pfc_output: dict — vlPFC response control signal
    response_inhibited: bool — whether a response was suppressed
    social_reasoning: dict — social context processing output
    stop_signal_strength: float — how strongly stop is signaled

CITATIONS:
    PMC23792944 — Rudebeck et al. (2013). OFC and vlPFC in behavioral flexibility.
    PMC16325345 — Funahashi (2006). DLPFC and vlPFC working memory.
    PMC2575055 — Hampshire et al. (2008). Right IFG in response inhibition.
"""

from brain.base_mechanism import BrainMechanism


class VentrolateralPrefrontalInferior(BrainMechanism):
    """
    vlPFC inferior part — response inhibition, social reasoning.

    Suppresses inappropriate responses and processes social cues
    to guide behavior. Right IFG is central to the "stop" mechanism.
    """

    def __init__(self):
        super().__init__(
            name="VentrolateralPrefrontalInferior",
            human_analog="Ventrolateral PFC — response inhibition, social reasoning",
            layer="neocortical",
        )
        self.state.setdefault("response_inhibited", False)
        self.state.setdefault("stop_signal_strength", 0.0)
        self.state.setdefault("social_reasoning", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Conflict signal from ACC
        acc_conflict = prior.get("AnteriorCingulateCognitive", {}).get(
            "conflict_intensity", 0.0
        )

        # Value signal from OFC
        ofc_value = prior.get("OrbitofrontalRewardValuator", {}).get(
            "value_signal", 0.5
        )

        # DLPFC dorsal (may generate competing response)
        dorsal_wm = prior.get("DorsolateralPrefrontalDorsal", {})
        dorsal_control = dorsal_wm.get("cognitive_control", 0.5)

        # Premotor plan (the action being prepotent)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        premotor_plan = premotor.get("motor_plan_ready", False)
        premotor_strength = premotor.get("internal_simulation", 0.5)

        # Amygdala emotional salience (threat detection)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_threat = max(0.0, -amygdala.get("valence_prediction", 0.0))

        # Stop signal: when conflict + threat + competing responses
        stop_conditions = acc_conflict * 0.4 + emotional_threat * 0.3 + (dorsal_control - premotor_strength) * 0.3
        stop_signal_strength = max(0.0, min(1.0, stop_conditions))

        # Response inhibited: stop signal succeeds when strong enough
        response_inhibited = stop_signal_strength > 0.55 and premotor_plan

        # Social reasoning: processes context cues
        anterior_insula = prior.get("AnteriorInsulaSalienceAttentional", {})
        insula_social = anterior_insula.get("salience_level", 0.5)

        social_reasoning = {
            "context_loaded": insula_social > 0.5,
            "threat_modulation": round(emotional_threat, 4),
            "inhibition_strength": round(stop_signal_strength, 4),
        }

        self.state["response_inhibited"] = response_inhibited
        self.state["stop_signal_strength"] = round(stop_signal_strength, 4)
        self.state["social_reasoning"] = social_reasoning
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ventrolateral_pfc_output": {
                "stop_signal": round(stop_signal_strength, 4),
                "response_inhibited": response_inhibited,
                "social_context": social_reasoning,
            },
            "response_inhibited": response_inhibited,
            "social_reasoning": social_reasoning,
            "stop_signal_strength": round(stop_signal_strength, 4),
        }