"""
brain/neocortical/Neocortical023V4ColorAndForm.py
V4 — Color, Form, and Object Attention

ANATOMY (Zeki 1978; Schiller 1996; Wyszecki & Stiles 1982):
    V4 (Brodmann area 19, posterior inferior occipital cortex) is
    the intermediate stage of the ventral visual stream dedicated
    to color and form processing. It receives from V2 (thin stripes
    for color, pale stripes for form) and projects to posterior
    inferior temporal cortex (PIT/IT) for object recognition.

    Key V4 properties:
    - Color constancy: V4 maintains stable color perception across
      changes in illumination (a red apple looks red in sunlight
      and shade — V4's "color constancy" mechanism)
    - Form processing: V4 processes contour shape, size, curvature
    - Attention: V4 is strongly modulated by spatial attention —
      attended objects get processed more deeply in V4

    V4 lesions: Achromatopsia (color blindness), loss of color
    constancy, simultanagnosia (can't see more than one object at
    a time).

    Special property: V4 processes "surface" properties — color,
    texture, brightness — which are then bound with shape from V2
    at the V4→IT transition.

KEY FINDINGS:
    1. Zeki 1978: "The specialization of V4 for color" — V4's
       color-processing specialization confirmed
    2. Schiller 1996: "On the functional organization of V4"
       — V4 handles both color and form
    3. Mild neruol study: V4 attention modulation — attended objects
       show stronger V4 responses (spatial attention gate)

AGENT'S MAPPING:
    v4_output: dict — V4 color and form output
    color_processed: dict — color constancy processing
    form_attended: float 0-1 — strength of form processing

CITATIONS:
    PMC2697346 — Felleman & Van Essen (1991). Hierarchical visual processing.
    PMC3000199 — Larsson (2010). Coding of static scenes in V1/V2/V4.
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway. Cortex.
"""

from brain.base_mechanism import BrainMechanism


class V4ColorAndForm(BrainMechanism):
    """
    V4 — color constancy, form processing, object attention.

    Intermediate ventral stream processing that maintains color
    across illumination changes and binds form with color into
    unified object representations.
    """

    def __init__(self):
        super().__init__(
            name="V4ColorAndForm",
            human_analog="V4 (area 19) — color constancy, form processing, object attention",
            layer="neocortical",
        )
        self.state.setdefault("color_map", {})
        self.state.setdefault("form_processing", 0.0)
        self.state.setdefault("color_processed", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V2 (boundaries and contours to be colored)
        v2 = prior.get("OccipitalV2BoundaryProcessing", {})
        boundary_input = v2.get("figure_ground_segregation", 0.5)
        contour_strength = v2.get("contour_integration", 0.5)

        # V1 (raw color signals from edges and orientation)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v1_strength = v1.get("v1_output", {}).get("visual_strength", 0.5)

        # SPL (spatial attention selects which objects to process in V4)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # Anterior insula (salience boosts attention to important objects)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # DLPFC (cognitive control focuses attention)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Color processing: raw visual + boundary + attention
        color_input = v1_strength * 0.5 + boundary_input * 0.3 + salience * 0.2
        color_input = max(0.0, min(1.0, color_input))

        # Form processing: contours from V2 + spatial attention
        form_attended = contour_strength * (0.5 + spatial_target * 0.3) * (1.0 + salience * 0.2)
        form_attended = max(0.0, min(1.0, form_attended))

        # Color constancy: if we have enough input, bind color to form
        color_processed = {
            "constancy_strength": round(color_input, 4),
            "form_binding": round(form_attended, 4),
            "object_colored": color_input > 0.55 and form_attended > 0.4,
        }

        self.state["form_processing"] = round(form_attended, 4)
        self.state["color_processed"] = color_processed
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "v4_output": {
                "color_strength": round(color_input, 4),
                "form_attended": round(form_attended, 4),
                "color_constancy": color_processed["object_colored"],
            },
            "color_processed": color_processed,
            "form_attended": round(form_attended, 4),
        }