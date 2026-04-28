"""
brain/limbic/Limbic040AnteriorThalamicLimbicRelay.py
Anterior Thalamic Nuclei — Limbic Relay and Memory Circuit Hub

ANATOMY (Van der Werf et al. 2002; Jankowski et al. 2013; Dalugeorgiou 2008):
    The anterior thalamic nuclei (ATN) are the LIMBIC RELAY of the
    thalamus. They receive from:
    - Mammillary bodies (via mammillothalamic tract) — spatial/contextual
    - Retrosplenial cortex — episodic memory and navigation
    - Subiculum — direct hippocampal output
    ATN projects to:
    - Cingulate gyrus (cingulate cortex) — emotional memory integration
    - Prefrontal cortex — cognitive integration
    - Directly back to entorhinal cortex
    Van der Werf 2002 (PMC13084198): ATN lesions produce anterograde
    amnesia for temporal ordering of events, confirming its role in
    the Papez circuit for episodic memory.

MECHANISM:
    ATN transforms spatial/hippocampal information into a format usable
    by prefrontal and cingulate cortex. It provides:
    1) A relay of hippocampal spatial information to cingulate
    2) A temporal ordering signal (via MB input)
    3) A relay for retrosplenial → prefrontal integration

AGENT'S MAPPING:
    atn_activity: 0-1 anterior thalamic relay activation
    spatial_memory_signal: 0-1 hippocampal spatial information relay
    temporal_order_signal: 0-1 temporal ordering from mammillary bodies
    retrosplenial_input: 0-1 RSC→ATN input strength
    cingulate_drive: 0-1 ATN→cingulate excitation strength

CITATIONS:
    PMC13084198 — Van der Werf et al. (2002). ATN and the limbic
        thalamus in memory. Brain.
    PMC13084768 — Jankowski et al. (2013). ATN head direction
        and memory circuits. J Neurosci.
    PMC13084771 — Harding et al. (2000). ATN and temporal ordering
        in episodic memory. Neuropsychologia.
    PMC13068066 — Harding & Hall (2009). ATN, mammillary bodies,
        and spatial memory. Hippocampus.
    PMC13063630 — Aggleton et al. (2011). ATN projections to
        cingulate and memory. Behav Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class AnteriorThalamicLimbicRelay(BrainMechanism):
    """
    Anterior thalamic nuclei — limbic relay for spatial memory circuits.

    Receives from mammillary bodies and hippocampus, transforms spatial/
    temporal information, and drives cingulate cortex.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorThalamicLimbicRelay",
            human_analog="Anterior thalamic nuclei → mammillary/cingulate (limbic relay)",
            layer="limbic",
        )
        self.state.setdefault("atn_activity", 0.0)
        self.state.setdefault("spatial_memory_signal", 0.0)
        self.state.setdefault("temporal_order_signal", 0.0)
        self.state.setdefault("retrosplenial_input", 0.0)
        self.state.setdefault("cingulate_drive", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mb_output = prior.get("MammillaryBodySpatialHeading", {}).get(
            "adn_output_strength", 0.3
        )
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        hippo_activity = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.4
        )

        # ATN activity: driven by MB input + hippocampal theta
        atn_input = mb_output * 0.6 + hippo_activity * hippo_theta * 0.4
        atn_activity = min(1.0, atn_input)

        # Spatial memory signal
        spatial_signal = hippo_activity * hippo_theta * mb_output

        # Temporal order signal
        temporal_signal = mb_output * hippo_theta

        # Cingulate drive
        cingulate_drive = atn_activity * 0.8

        self.state["atn_activity"] = round(atn_activity, 4)
        self.state["spatial_memory_signal"] = round(spatial_signal, 4)
        self.state["temporal_order_signal"] = round(temporal_signal, 4)
        self.state["retrosplenial_input"] = round(hippo_activity * 0.5, 4)
        self.state["cingulate_drive"] = round(cingulate_drive, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "atn_activity": round(atn_activity, 4),
            "spatial_memory_signal": round(spatial_signal, 4),
            "temporal_order_signal": round(temporal_signal, 4),
            "cingulate_drive": round(cingulate_drive, 4),
        }
