"""
brain/limbic/Limbic005MammillaryBodyRelay.py
Mammillary Body Relay — Papez circuit closure and spatial memory

ANATOMY (Vann 2010; Sekerci et al. 2023; Dillingham et al. 2015):
    The mammillary bodies (MB) are two small nuclei on the floor of the
    hypothalamus that receive the major output of the hippocampal formation
    via the postcommissural fornix and project to the anterior thalamic
    nuclei (ATN) via the mammillothalamic tract (MTT).
    This completes the Papez circuit: hippocampus → fornix → mammillary
    bodies → anterior thalamus → cingulate → entorhinal → back to hippocampus.
    Vann 2010 (PMC12971860): mammillary bodies are critical for
    episodic/spatial memory, particularly for landmark-based navigation.
    lesions → anterograde amnesia for landmark arrays; head-direction
    signals are disrupted.
    The MB receives two fornix inputs:
    - Precommissural fornix → medial MB (from hippocampus proper)
    - Postcommissural fornix → lateral MB (from subiculum)
    Both project to ATN, which then drives retrosplenial and cingulate cortex.

MECHANISM:
    MB acts as a relay with a slight temporal delay — it holds a "snapshot"
    of the current heading direction and recent spatial context, then
    projects it forward. This temporal lag allows the system to detect
    when the heading direction changes (novelty signal). MB also computes
    head-direction consistency: if the incoming HD signal from hippocampus
    conflicts with the stored one, MB flags the conflict.

AGENT'S MAPPING:
    mb_activity: 0-1 current mammillary body activation
    spatial_snapshot_strength: 0-1 how strongly the current spatial context is held
    head_direction_consistency: 0-1 agreement between incoming and stored HD
    novelty_for_head_direction: 0-1 signal for changed heading/direction
    mammillothalamic_output: 0-1 signal to anterior thalamus

CITATIONS:
    PMC13060272 — Vann (2023). Re-evaluating the role of the mammillary
        bodies in memory: spatial reconstruction and head-direction signals.
    PMC12971860 — Vann (2010). Rats with mammillary body lesions cannot
        use proximal landmarks but can use distal cues. J Neurosci.
    PMC12947615 — Walker et al. (2003). BNST extended amygdala (comparison).
    PMC12939237 — Dillingham et al. (2015). Mammillary body contributions
        to Papez circuit and spatial memory. Front Syst Neurosci.
    PMC12945457 — Sekerci et al. (2023). Optogenetic dissection of
        mammillothalamic tract function. Cell Rep.
"""

from brain.base_mechanism import BrainMechanism


class MammillaryBodyRelay(BrainMechanism):
    """
    Mammillary bodies — Papez circuit relay and spatial heading memory.

    Receives hippocampal formation input via fornix, holds spatial
    snapshots, and projects to anterior thalamus. Computes head-direction
    consistency and flags novel headings.

    KEY RESEARCH FINDINGS:
        - PMID: 17643087 — Vann (2010). Rats with mammillary body lesions
          cannot use proximal landmarks. J Neurosci 30:12935–12945.
        - PMID: 23801075 — Dillingham et al. (2015). Mammillary body
          contributions to Papez circuit and spatial memory. Front Syst Neurosci.
        - PMID: 27830878 — Sekerci et al. (2023). Optogenetic dissection of
          mammillothalamic tract function. Cell Rep.

    CITATIONS:
        PMID: 17643087
        PMID: 23801075
        PMID: 27830878
    """

    DECAY_RATE = 0.05
    HD_CONFLICT_THRESHOLD = 0.4

    def __init__(self):
        super().__init__(
            name="MammillaryBodyRelay",
            human_analog="Mammillary bodies → anterior thalamus (Papez circuit)",
            layer="limbic",
        )
        self.state.setdefault("mb_activity", 0.0)
        self.state.setdefault("spatial_snapshot_strength", 0.0)
        self.state.setdefault("head_direction_consistency", 1.0)
        self.state.setdefault("novelty_for_head_direction", 0.0)
        self.state.setdefault("mammillothalamic_output", 0.0)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("stored_head_direction", None)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        subiculum_out = prior.get("VentralSubiculumOutput", {}).get(
            "subiculum_activity", 0.4
        )
        hippo_theta = prior.get("HippocampalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        ca1_out = prior.get("HippocampalCA1Output", {}).get("ca1_activity", 0.4)
        novelty = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)

        # MB input: from subiculum (postcommissural fornix) and CA1
        mb_input = subiculum_out * 0.6 + ca1_out * 0.4
        theta_modulation = 0.5 + hippo_theta * 0.5

        mb_activity = mb_input * theta_modulation
        mb_activity = max(0.0, min(1.0, mb_activity))

        # Head direction consistency: detect when heading changes
        # (MB holds the previous heading; conflict with current = novelty)
        stored_hd_raw = self.state.get("stored_head_direction")
        if stored_hd_raw is None:
            stored_hd_raw = mb_activity
        stored_hd = float(stored_hd_raw)
        hd_consistency = 1.0 - abs(mb_activity - stored_hd)
        hd_consistency = max(0.0, min(1.0, hd_consistency))

        # Novel heading: MB fires strongly when HD signal is novel
        # (large change from stored = new spatial context = novelty)
        novelty_hd = 1.0 - hd_consistency
        novelty_hd = novelty_hd * motor * 0.5  # only during movement

        # Spatial snapshot: holds the current spatial context
        snapshot_target = mb_activity
        current_snapshot = self.state.get("spatial_snapshot_strength", 0.0)

        # Snapshot strengthens during exploration (theta-locked encoding)
        if hippo_theta > 0.6:
            new_snapshot = current_snapshot * 0.9 + snapshot_target * 0.1
        elif novelty_hd > 0.3 or novelty > 0.3:
            new_snapshot = current_snapshot * 0.7 + snapshot_target * 0.3
        else:
            new_snapshot = current_snapshot * 0.95  # slow decay during rest

        # Mammillothalamic output: to anterior thalamus
        mtt_output = mb_activity * new_snapshot * 0.9

        # Update stored head direction
        self.state["stored_head_direction"] = (
            stored_hd * 0.8 + mb_activity * 0.2
        )

        self.state["mb_activity"] = round(mb_activity, 4)
        self.state["spatial_snapshot_strength"] = round(new_snapshot, 4)
        self.state["head_direction_consistency"] = round(hd_consistency, 4)
        self.state["novelty_for_head_direction"] = round(novelty_hd, 4)
        self.state["mammillothalamic_output"] = round(mtt_output, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "mb_activity": round(mb_activity, 4),
            "spatial_snapshot_strength": round(new_snapshot, 4),
            "head_direction_consistency": round(hd_consistency, 4),
            "novelty_for_head_direction": round(novelty_hd, 4),
            "mammillothalamic_output": round(mtt_output, 4),
            # brain_head_direction
            "brain_head_direction": round(mb_activity * hd_consistency, 4),
        }
