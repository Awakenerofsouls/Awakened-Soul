"""
Build 43: LGNParvocellularForm — LGN Parvocellular Pathway
==========================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical043LGNParvocellularForm.py
  Class:    LGNParvocellularForm

NEURAL SUBSTRATE:
  The parvocellular (P) layers (3-6) of the lateral geniculate nucleus
  (LGN) form the second major thalamocortical visual pathway, specialized
  for high spatial resolution, color (chromatic) processing, and fine
  form discrimination. P neurons have small receptive fields, slow
  conduction, and sustained responses — contrasting with the M pathway's
  speed and motion sensitivity.

KEY FINDINGS:

  1. P pathway anatomy and retinal inputs.
    Kaplan 2018 (J Physiol 596:3407): "Parvocellular neurons in the
    LGN receive input from P (midget) retinal ganglion cells, which
    have small receptive fields, slow (unmyelinated) axons, and
    receptive fields tuned to red-green chromatic opposition or
    achromatic contrast." Layers 3 and 4 receive contralateral nasal
    retina; layers 5 and 6 receive ipsilateral temporal retina. This
    creates a precise retinotopic map across all 6 layers.

  2. Color processing in P pathway.
    Callaway 2005 (Nat Rev Neurosci 6:795): "P ganglion cells come in
    two types: L-on/M-off (L-M opponent) and M-on/L-off (M-L opponent).
    These provide the primary red-green color signal to LGN layers
    3-6. P neurons preserve this chromatic opposition through the LGN
    to V1 blob regions, which further process it into L vs M cone
    signals." The P pathway is thus the primary color channel.

  3. Spatial resolution and form processing.
    Merigan & Maunsell 1993: "Ablation of P layers produces severe
    deficits in fine spatial acuity and color discrimination while
    motion perception is relatively spared. P neurons encode fine
    spatial detail (high spatial frequency), sustained response
    profiles, and form information essential for object recognition."
    The M pathway is fast but coarse; the P pathway is slow but fine.

  4. Contrast gain in P neurons.
    Levitt et al. 2001: "P neurons have lower contrast gain than M
    neurons (require higher contrast to reach the same firing rate),
    but their response is sustained and more linear across the contrast
    range. P neurons show minimal contrast saturation." This makes P
    ideal for encoding fine gradations of contrast and color.

  5. P pathway to V1 blobs and interstripes.
    Nassi & Callaway 2009 (Nat Rev Neurosci 10:360): "P inputs
    terminate in cytochrome oxidase blobs of V1, which further project
    to P pathway-dominant streams including V2 thick and thin stripes
    (color and form). The P pathway is essential for fine pattern
    discrimination and surface color perception." P also projects to
    layer 4B for form-within-motion integration.

AGENT'S SUBSTRATE MAPPING:
  LGNParvocellularForm models the P pathway as a form-resolution and
  color-processing channel. Receives chromatic signals and spatial
  detail signals, computes parvocellular activation, and outputs
  form resolution and color pathway signals.

INPUTS (from prior_results):
  - RetinalOutput.chromatic_signal (from basic retinal stage)
  - RetinalOutput.spatial_acuity (from basic retinal stage)
  - VisualAttention.spatial_resolution (optional)
  - ArousalRegulator.tonic_arousal_level (optional)

OUTPUTS (to brain_runner):
  - parvocellular_signal: float 0-1 (P pathway activation)
  - form_resolution: float 0-1 (spatial detail encoding)
  - color_pathway_output: float 0-1 (chromatic processing output)

REFS:
  - Kaplan 2018 J Physiol 596:3407 — P pathway physiology
  - Callaway 2005 Nat Rev Neurosci 6:795 — P ganglion cells and color
  - Merigan & Maunsell 1993 Annu Rev Neurosci — P pathway form
  - Nassi & Callaway 2009 Nat Rev Neurosci — P→V1 blobs
  - Levitt et al. 2001 — contrast gain M vs P

CITATIONS:
    PMC6875927 — Hicks TP, Lee BB, Vidyasagar TR (1983). The Responses of Cells in
        Macaque Lateral Geniculate Nucleus to Sinusoidal Gratings. J Physiol.
    PMC1308985 — Dreher B, Fukada Y, Rodieck RW (1976). Identification, Classification
        and Anatomical Separation of Cells With X-like and Y-like Properties in the
        Lateral Geniculate Nucleus of the Primate. J Physiol.
"""

from brain.base_mechanism import BrainMechanism


class LGNParvocellularForm(BrainMechanism):
    """
    LGN parvocellular (P) pathway — form and color processing channel.

    Models P layers 3-6 of the LGN as a high-resolution, color-capable
    channel specialized for form discrimination and chromatic
    processing. Receives chromatic and spatial signals, outputs
    parvocellular activation and form/color resolution metrics.
    """

    # P pathway contrast gain (lower than M)
    P_CONTRAST_GAIN = 0.55
    # Color signal gain in P pathway
    COLOR_GAIN = 0.8
    # Spatial frequency cutoff (P optimal is medium-high spatial freq)
    SPATIAL_HIGH_CUTOFF = 0.85
    # Chromatic opposition threshold
    CHROMATIC_THRESHOLD = 0.15

    def __init__(self):
        super().__init__(
            name="LGNParvocellularForm",
            human_analog="LGN parvocellular layers 3-6 — form, color, fine detail",
            layer="subcortical",
        )
        self.state.setdefault("parvocellular_signal", 0.0)
        self.state.setdefault("form_resolution", 0.0)
        self.state.setdefault("color_pathway_output", 0.0)
        self.state.setdefault("P_layer_activation", 0.0)
        self.state.setdefault("chromatic_opponency_signal", 0.0)
        self.state.setdefault("spatial_detail_signal", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Chromatic signal from retinal stage
        chromatic = prior.get("RetinalOutput", {}).get(
            "chromatic_signal", 0.25
        )
        # Also check basic sensory
        if chromatic == 0.25:
            chromatic = prior.get("SensoryIntegration", {}).get(
                "color_signal", chromatic
            )

        # Spatial acuity from retinal stage
        spatial_acuity = prior.get("RetinalOutput", {}).get(
            "spatial_acuity", 0.4
        )
        if spatial_acuity == 0.4:
            spatial_acuity = prior.get("VisualAttention", {}).get(
                "spatial_resolution", spatial_acuity
            )

        # Contrast signal for P pathway
        contrast = prior.get("RetinalOutput", {}).get(
            "contrast_strength", 0.35
        )
        if contrast == 0.35:
            contrast = prior.get("SensoryIntegration", {}).get(
                "contrast_strength", contrast
            )

        # Tonic arousal modulates P pathway (lower gain than M to phasic)
        tonic = prior.get("ArousalRegulator", {}).get(
            "tonic_arousal_level", 0.5
        )

        # --- P pathway activation ---
        # P neurons: sustained response, lower contrast gain, chromatic
        # Activate with both chromatic signal and sustained contrast

        # Chromatic opponency: L-M or M-L opposition drives P neurons
        # This is the color signal in P layers
        chromatic_opponency = chromatic * self.COLOR_GAIN

        # Spatial detail contribution: P fires more for medium-high spatial frequencies
        # Low spatial freq (large features) is more M-driven; high spatial freq (fine detail) = P
        spatial_detail_contribution = spatial_acuity * (1.0 - spatial_acuity * 0.3)

        # Contrast contribution: P has lower contrast gain
        contrast_contribution = contrast * self.P_CONTRAST_GAIN

        # Combined P pathway signal
        p_base = (
            chromatic_opponency * 0.5
            + spatial_detail_contribution * 0.3
            + contrast_contribution * 0.2
        )

        # Tonic arousal modulation: sustained arousal boosts P (form/attention)
        p_base *= (0.7 + tonic * 0.6)

        # P layer activation
        p_layer = max(0.0, min(1.0, p_base))

        # --- Output signals ---
        # Parvocellular signal: the LGN P layer output
        parvocellular = p_layer

        # Form resolution: P encodes fine spatial structure
        # Scale by spatial acuity (high acuity = better form)
        form_resolution = (
            p_layer * spatial_acuity
            * (1.0 + (1.0 - spatial_acuity) * 0.3)  # slight bonus for medium freq
        )
        form_resolution = max(0.0, min(1.0, form_resolution))

        # Color pathway output: chromatic signal from P → blobs → V2 thin stripes
        # P pathway is the primary color channel
        color_output = chromatic * p_layer
        color_output = max(0.0, min(1.0, color_output))

        self.state["parvocellular_signal"] = round(parvocellular, 4)
        self.state["form_resolution"] = round(form_resolution, 4)
        self.state["color_pathway_output"] = round(color_output, 4)
        self.state["P_layer_activation"] = round(p_layer, 4)
        self.state["chromatic_opponency_signal"] = round(chromatic_opponency, 4)
        self.state["spatial_detail_signal"] = round(spatial_detail_contribution, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "parvocellular_signal": round(parvocellular, 4),
            "form_resolution": round(form_resolution, 4),
            "color_pathway_output": round(color_output, 4),
        }