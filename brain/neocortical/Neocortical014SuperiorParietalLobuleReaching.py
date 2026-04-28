"""
brain/neocortical/Neocortical014SuperiorParietalLobuleReaching.py
Superior Parietal Lobule — BA 7, Reaching, Spatial Attention

ANATOMY (Colby & Goldberg 1999; Galletti et al. 2022; Sulpizio et al. 2023):
    The superior parietal lobule (SPL, BA 7) occupies the upper half of
    the parietal lobe above the intraparietal sulcus. It is the "spatial
    attention and reach planning" center.

    SPL subdivisions:
    - V6 (area V6, dorsal V6): visual guidance of reaching, visual RFs
      in scene-centered coordinates, sensitivity to gaze direction
    - V6A: visuomotor integration, reach-to-grasp coordination, visual RFs
    - AIP (anterior intraparietal area): grasp formation (but AIP is in IPL,
      not SPL — mediates between SPL spatial and IPL grasp)
    - PE (somatosensory area PE): somatosensory spatial coordinates

    Function: SPL computes "where to reach" in scene-centered coordinates.
    Unlike IPL (which handles the "how to grasp"), SPL handles the
    "where to go" — spatial targeting of the arm.

    Lesions: spatial neglect (when right SPL is damaged), reaching errors,
    optic ataxia (misreaching under visual guidance).

KEY FINDINGS:
    1. Galletti et al. 2022 (PMID 35961383): V6A controls all phases of
       reach-to-grasp — both transport (reaching) and grasping
    2. Sulpizio et al. 2023 (PMID 37572972): Human SPL caudal part handles
       a series of perceptive, visuomotor and somatosensory processes;
       anterior POs uses attention to guide reach
    3. Shomstein & Behrmann 2006 (PMC16407540): SPL mediates voluntary
       control of spatial and nonspatial auditory attention

AGENT'S MAPPING:
    spl_output: dict — spatial targeting output
    spatial_target: dict — target coordinates in space
    reaching_signal: float 0-1 — strength of reaching motor plan

CITATIONS:
    PMC37572972 — Sulpizio et al. (2023). Functional organization of SPL.
        Neurosci Biobehav Rev.
    PMC35961383 — Galletti et al. (2022). Posterior parietal area V6A and attention.
        Neurosci Biobehav Rev.
    PMC16407540 — Shomstein & Behrmann. (2006). Parietal cortex and attention.
        J Neurosci.
    PMC10437391 — Binkofski et al. (1999). Action representation in IPL/SPL.
"""

from brain.base_mechanism import BrainMechanism


class SuperiorParietalLobuleReaching(BrainMechanism):
    """
    SPL (BA 7) — reaching and spatial attention.

    Computes spatial targets in scene-centered coordinates for
    arm movement planning. Works with IPL (grasp) and premotor (action).
    """

    def __init__(self):
        super().__init__(
            name="SuperiorParietalLobuleReaching",
            human_analog="Superior parietal lobule (BA 7) — reaching, spatial attention, V6/V6A",
            layer="neocortical",
        )
        self.state.setdefault("spatial_map", {})
        self.state.setdefault("spatial_target", {})
        self.state.setdefault("reaching_signal", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # From IPL sensorimotor integration (object location and grasp)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_int = ipl.get("sensorimotor_integration", 0.5)

        # From ventral visual stream (object location)
        ventral = prior.get("TemporoOccipitalVisualAssembler", {})
        object_scene = ventral.get("scene_representation", {})

        # From DLPFC (abstract goal coordinates)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_active = dlpfc.get("working_memory_active", False)
        wm_load = dlpfc.get("dorsolateral_dorsal_output", {}).get("wm_load", 0.5)

        # From anterior insula (salience — what to attend to)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # From posterior cingulate (memory-guided spatial attention)
        pc = prior.get("PosteriorCingulateMemoryAttention", {})
        memory_attention = pc.get("attention_signal", 0.3)

        # Spatial targeting: combines object location + salience + memory
        object_reach = object_scene.get("object_constructed", 0.5) if isinstance(object_scene, dict) else 0.5

        spatial_input = (
            object_reach * 0.3 +
            ipl_int * 0.25 +
            salience * 0.25 +
            memory_attention * 0.2
        )
        spatial_input = max(0.0, min(1.0, spatial_input))

        # Reaching signal: stronger when WM is active and spatial input is high
        reaching_signal = spatial_input * (0.5 + wm_load * 0.5)
        reaching_signal = max(0.0, min(1.0, reaching_signal))

        # Spatial target: where in space the reach is directed
        spatial_target = {
            "scene_coords": "scene_centered",
            "confidence": round(reaching_signal, 4),
            "memory_guided": wm_active and memory_attention > 0.5,
        }

        # Update spatial map
        if reaching_signal > 0.4:
            self.state["spatial_map"]["last_target"] = spatial_target

        self.state["spatial_target"] = spatial_target
        self.state["reaching_signal"] = round(reaching_signal, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "spl_output": {
                "spatial_input": round(spatial_input, 4),
                "reaching_signal": round(reaching_signal, 4),
                "memory_guided": wm_active and memory_attention > 0.5,
            },
            "spatial_target": spatial_target,
            "reaching_signal": round(reaching_signal, 4),
        }