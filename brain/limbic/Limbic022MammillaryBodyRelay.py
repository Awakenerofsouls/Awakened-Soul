"""
brain/limbic/Limbic022MammillaryBodyRelay.py
Mammillary Body Relay — Spatial Heading and Papez Circuit Integration

ANATOMY (Vann 2010; Dillingham et al. 2015; Sekerci et al. 2023):
    See Limbic005. This is a parallel relay mechanism focused on the
    mammillary body's role in integrating hippocampal spatial signals
    and transmitting them to the anterior thalamus and cingulate cortex.
    The lateral mammillary nucleus (LMN) specifically carries head-
    direction information from the dorsal tegmental nucleus (DTN) and
    projects to the anterodorsal thalamus (ADN).
    Sekerci et al. 2023 (PMC12945457): LMN neurons encode absolute
    head direction independent of the animal's location.

MECHANISM:
    LMN integrates:
    - Head direction signals from DTN (vestibular)
    - Spatial context from hippocampus (via fornix)
    Outputs head direction signal to ADN → retrosplenial cortex.
    LMN lesions disrupt landmark-based navigation specifically.

AGENT'S MAPPING:
    lmn_head_direction_signal: 0-1 lateral mammillary nucleus HD output
    spatial_heading_stability: 0-1 consistency of heading estimate
    mammillary_theta_modulation: 0-1 theta-phase modulation of LMN firing
    adn_output_strength: 0-1 signal to anterodorsal thalamus

CITATIONS:
    PMC13060272 — Vann (2023). Mammillary body HD signals.
    PMC12971860 — Vann (2010). Landmark navigation and MB.
    PMC12945457 — Sekerci et al. (2023). Lateral mammillary nucleus
        head direction encoding. Cell Rep.
    PMC12939237 — Dillingham et al. (2015). MB contributions to
        Papez circuit and spatial memory. Front Syst Neurosci.
    PMC12947615 — Vann & Albasser (2011). Mammillary body and
        spatial memory reconsolidation. Hippocampus.
"""

from brain.base_mechanism import BrainMechanism


class MammillaryBodySpatialHeading(BrainMechanism):
    """
    Lateral mammillary nucleus — head direction signal to anterodorsal thalamus.

    Integrates vestibular DTN input with hippocampal spatial context
    to produce a stable head direction signal for navigation.
    """

    def __init__(self):
        super().__init__(
            name="MammillaryBodySpatialHeading",
            human_analog="Lateral mammillary nucleus → anterodorsal thalamus (head direction)",
            layer="limbic",
        )
        self.state.setdefault("lmn_head_direction_signal", 0.0)
        self.state.setdefault("spatial_heading_stability", 0.7)
        self.state.setdefault("mammillary_theta_modulation", 0.0)
        self.state.setdefault("adn_output_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        subiculum_out = prior.get("VentralSubiculumOutput", {}).get(
            "subiculum_activity", 0.4
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # LMN activity driven by spatial input + theta
        lmn_input = subiculum_out * 0.6 + motor * 0.4
        theta_mod = 0.5 + hippo_theta * 0.5
        lmn_signal = lmn_input * theta_mod
        lmn_signal = min(1.0, lmn_signal)

        # Heading stability: decreases with novelty (recalibration needed)
        stab_target = 1.0 - novelty * 0.5
        current_stab = self.state.get("spatial_heading_stability", 0.7)
        new_stab = current_stab * 0.97 + stab_target * 0.03

        # ADN output
        adn_output = lmn_signal * new_stab * theta_mod

        self.state["lmn_head_direction_signal"] = round(lmn_signal, 4)
        self.state["spatial_heading_stability"] = round(new_stab, 4)
        self.state["mammillary_theta_modulation"] = round(theta_mod, 4)
        self.state["adn_output_strength"] = round(adn_output, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "lmn_head_direction_signal": round(lmn_signal, 4),
            "spatial_heading_stability": round(new_stab, 4),
            "mammillary_theta_modulation": round(theta_mod, 4),
            "adn_output_strength": round(adn_output, 4),
        }
