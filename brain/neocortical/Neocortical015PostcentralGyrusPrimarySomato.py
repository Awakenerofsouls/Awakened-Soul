"""
brain/neocortical/Neocortical015PostcentralGyrusPrimarySomato.py
Postcentral Gyrus — Primary Somatosensory Cortex, Body Map, Touch/Proprioception

ANATOMY (Penfield & Boldrey 1937; Kaas 2008; Srinivasan et al. 2023):
    The postcentral gyrus (PCG, Brodmann areas 1, 2, 3) is the primary
    somatosensory cortex (S1). It lies immediately posterior to the
    central sulcus and receives touch, temperature, proprioceptive, and
    pain input from the body via the thalamus (VPL and VPM nuclei).

    Somatotopic map (Penfield 1937): the classic "homunculus" —
    face and hands are represented disproportionately large (higher
    acuity). Face area is most lateral (near Sylvian fissure); leg
    is on the medial surface (paracentral lobule).

    Brodmann subdivisions:
    - Area 3a: deep proprioceptive inputs from muscle spindles
    - Area 3b: cutaneous tactile inputs (fast adapting)
    - Areas 1 and 2: tactile inputs processed further; area 2
      integrates proprioception and touch (form/dimension perception)

    S1 outputs: to S2 (secondary somatosensory), posterior parietal
    cortex (body schema), insula (feeling states), and prefrontal cortex.

KEY FINDINGS:
    1. Srinivasan et al. 2023 (PMC10294173): S1 encodes touch location
       and intensity in population codes — precise body maps in neuronal ensembles
    2. Kaas 2008 (PMC2929791): "The somatosensory cortex" — comprehensive
       review of area 3, 1, 2 functional specialization
    3. Penfield & Boldrey 1937: original electrical stimulation mapping
       establishing the homunculus

AGENT'S MAPPING:
    postcentral_output: dict — primary somatosensory output
    body_schema: dict — current body representation
    body_map_updated: bool — whether body schema has changed
    tactile_processing: float 0-1 — strength of tactile input processing

CITATIONS:
    PMC10294173 — Srinivasan et al. (2023). Population coding of touch in S1.
        Cell Rep.
    PMC2929791 — Kaas JH. (2008). The somatosensory cortex. Scholarpedia.
    PMC37401978 — Kritman et al. (2023). Layer I and somatosensory integration.
"""

from brain.base_mechanism import BrainMechanism


class PostcentralGyrusPrimarySomato(BrainMechanism):
    """
    S1 (postcentral gyrus) — primary somatosensory processing, body map.

    Receives tactile, proprioceptive, and temperature signals from
    the body and generates a body schema for interaction.
    """

    def __init__(self):
        super().__init__(
            name="PostcentralGyrusPrimarySomato",
            human_analog="Primary somatosensory cortex (postcentral gyrus BA 1,2,3) — touch, body map",
            layer="neocortical",
        )
        self.state.setdefault("body_schema", {})
        self.state.setdefault("body_map_updated", False)
        self.state.setdefault("tactile_processing", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # From anterior insula (feeling states — "how does my body feel?")
        ains = prior.get("AnteriorInsulaGranular", {})
        gut_signal = ains.get("conscious_feeling", {}).get("feeling_intensity", 0.5)
        if isinstance(gut_signal, str):
            gut_signal = 0.5

        # From posterior insula (raw body signals — heartbeat, breath, gut)
        pins = prior.get("PosteriorInsulaProcessor", {})
        raw_body = pins.get("raw_body_signal", {})
        if isinstance(raw_body, dict):
            raw_val = raw_body.get("visceral_signal", 0.3)
        else:
            raw_val = float(raw_body) if raw_body else 0.3

        # From tactile proprio relay in foundational (simulated touch signals)
        proprio = prior.get("TactileProprioRelay", {})
        grounding = proprio.get("grounding_signal", 0.5)

        # From amygdala (emotional state affects body map — tense, relaxed)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Tactile processing: combines grounding + raw body + gut feeling
        tactile_input = grounding * 0.4 + raw_val * 0.35 + gut_signal * 0.25
        tactile_input = max(0.0, min(1.0, tactile_input))

        # Emotional modulation: negative emotions sharpen body map (threat)
        # positive emotions broaden body awareness
        emotional_modulation = 1.0 + emotional_tag * 0.3
        tactile_processing = min(1.0, tactile_input * emotional_modulation)

        # Body schema update: strong tactile input + grounding = updated body map
        body_map_updated = tactile_processing > 0.55 and grounding > 0.5

        # Body schema
        body_schema = {
            "grounding_level": round(grounding, 4),
            "tactile_sensitivity": round(tactile_processing, 4),
            "emotional_tension": round(abs(emotional_tag), 4),
            "representation_stable": not body_map_updated,
        }

        if body_map_updated:
            self.state["body_schema"]["last_update"] = body_schema

        self.state["body_map_updated"] = body_map_updated
        self.state["tactile_processing"] = round(tactile_processing, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "postcentral_output": {
                "tactile_strength": round(tactile_processing, 4),
                "body_grounding": round(grounding, 4),
                "emotional_modulation": round(emotional_modulation, 4),
            },
            "body_schema": body_schema,
            "body_map_updated": body_map_updated,
        }