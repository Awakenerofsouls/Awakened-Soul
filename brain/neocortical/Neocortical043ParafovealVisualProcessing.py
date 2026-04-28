"""
brain/neocortical/Neocortical043ParafovealVisualProcessing.py
Parafoveal Visual Processing — V4+ Surrounds, Attended Form Detail

ANATOMY (Yeshurun & Carrasco 1999; Roberts & Hall 2008; Hubbard et al. 2011):
    The parafoveal (foveal/parafoveal) processing regions surround
    the fovea — the central 2° of vision where visual acuity is highest.
    These regions (including V4 and surrounding cortex) process
    the attended visual region in high detail.

    Parafoveal processing properties:
    - High spatial resolution: processes fine detail in the attended region
    - Attended enhancement: attended regions get more processing
    - Feature integration: combines color, form, texture into attended objects
    - Foveal bottleneck: only ~2° gets full foveal resolution; beyond that,
      resolution drops rapidly (1° = 60 pixels at 60cm screen)

    V4 is the key hub for parafoveal attention — it receives
    enhanced input from spatial attention (from parietal/FEF)
    and processes attended regions in detail.

    Connections: V4 ↔ FEF (frontal eye fields, attention),
    V4 ↔ MT (motion suppression during fixation),
    V4 ↔ IT (object identification).

KEY FINDINGS:
    1. Yeshurun & Carrasco 1999: "Spatial attention and acuity"
       — spatial attention enhances V4 processing of attended regions
    2. Roberts & Hall 2008: "Attending to motion" — spatial attention
       and motion processing interact in V4/MT
    3. Hubbard et al. 2011: "V4 and form processing" — V4's role
       in attending to specific visual features

AGENT'S MAPPING:
    parafoveal_output: dict — attended visual region processing
    attended_form_detailed: dict — detailed form of the attended object

CITATIONS:
    PMC3000199 — Larsson (2010). V4 and scene processing.
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway.
    PMC3717975 — Kravitz et al. (2013). Dorsal visual stream.
"""

from brain.base_mechanism import BrainMechanism


class ParafovealVisualProcessing(BrainMechanism):
    """
    Parafoveal — attended visual region in high resolution.

    Processes the attended visual region in fine detail,
    combining color, form, and texture information.
    """

    def __init__(self):
        super().__init__(
            name="ParafovealVisualProcessing",
            human_analog="Parafoveal cortex (V4 surrounds) — attended form, high-resolution visual processing",
            layer="neocortical",
        )
        self.state.setdefault("attended_region", {})
        self.state.setdefault("attended_form_detailed", {})
        self.state.setdefault("processing_depth", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V4 (color and form being processed)
        v4 = prior.get("V4ColorAndForm", {})
        color_form = v4.get("color_processed", {})
        form_attended = v4.get("form_attended", 0.5)

        # SPL (spatial attention target — what region to process in detail?)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # DLPFC (cognitive control — what to attend to)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Anterior insula (salience — does this region matter?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # TOJ (visual object input)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        obj_const = toj.get("object_constructed", {})
        construction = obj_const.get("construction_strength", 0.5) if isinstance(obj_const, dict) else 0.5

        # Attended form: when region is attended + object is constructed + salience high
        attended_strength = spatial_target * 0.3 + cognitive_ctrl * 0.25 + salience * 0.25 + construction * 0.2
        attended_strength = max(0.0, min(1.0, attended_strength))

        processing_depth = form_attended * 0.5 + attended_strength * 0.5

        attended_form_detailed = {
            "form_strength": round(attended_strength, 4),
            "color_bound": color_form.get("object_colored", False) if isinstance(color_form, dict) else False,
            "resolution": "high" if processing_depth > 0.6 else "medium",
        }

        self.state["attended_region"]["last_attended"] = round(attended_strength, 3)
        self.state["attended_form_detailed"] = attended_form_detailed
        self.state["processing_depth"] = round(processing_depth, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "parafoveal_output": {
                "attended_strength": round(attended_strength, 4),
                "processing_depth": round(processing_depth, 4),
            },
            "attended_form_detailed": attended_form_detailed,
        }