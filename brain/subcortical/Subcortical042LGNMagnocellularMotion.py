"""
Build 42: LGNMagnocellularMotion — LGN Magnocellular Pathway
===========================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical042LGNMagnocellularMotion.py
  Class:    LGNMagnocellularMotion

NEURAL SUBSTRATE:
  The lateral geniculate nucleus (LGN) of the thalamus is the
  retinothalamic relay station. It has 6 layers (in primates):
  Layers 1-2 are the magnocellular (M) layers, layers 3-6 are
  parvocellular (P). The M pathway is specialized for motion
  detection, luminance contrast, and rapid temporal processing.

KEY FINDINGS:

  1. M pathway anatomy and retinal inputs.
    Kaplan 2018 (J Physiol 596:3407): "Magnocellular neurons in
    the LGN receive input from a specialized subset of retinal
    ganglion cells (M/parasol cells in primates, Y-cells in cats).
    These M-retinal ganglion cells have large receptive fields,
    fast conduction velocities (myelinated axons), and respond
    predominantly to achromatic (luminance) contrast." Layer 1
    receives input from contralateral nasal retina; layer 2
    receives input from ipsilateral temporal retina + contralateral
    nasal (via chiasm).

  2. Motion detection in M pathway.
    Merigan & Maunsell 1993 (Annu Rev Neurosci 16:369): "Ablation
    of M layers in LGN produces severe deficits in motion perception
    while leaving color discrimination relatively intact. The M
    pathway carries the principal motion signal from retina to
    cortex." M neurons respond well to moving stimuli, have high
    temporal resolution (responds at 60+ Hz), and are sensitive
    to low spatial frequencies.

  3. Temporal processing characteristics of M neurons.
    Kaplan 2018: "M neurons have sustained receptive fields in
    some species (M/Y-type) but in primates show transient responses
    to stimulus onset/offset. Their contrast gain is high (respond
    well at low contrasts), and they saturate at moderate contrasts.
    Temporal frequency response: optimal around 10-20 Hz, with
    reduced response at very high frequencies."

  4. M pathway to V1: the blob-free route.
    In V1, M inputs terminate primarily in layer 4Cα and the
    cytochrome oxidase (CO) blobs are bypassed. The M pathway
    projects to MT (V5) for motion processing via the dorsal
    stream. Maunsell et al. 1990: "MT neurons are dominated by
    M pathway input and encode visual motion speed, direction,
    and disparity."

  5. LGN M layer physiology: contrast gain.
    Levitt et al. 2001: "M neurons in LGN have contrast gain values
    that are about 3-4× higher than P neurons. They respond
    proportionally at lower contrasts, making them good detectors
    of stimulus onset and movement onset."

AGENT'S SUBSTRATE MAPPING:
  LGNMagnocellularMotion models the M pathway as a motion-detection
  channel. Receives luminance contrast and temporal change signals,
  computes magnocellular activation, and outputs motion signal
  strength and fast pathway output.

INPUTS (from prior_results):
  - RetinalOutput.luminance_contrast (from retinal/basic sensory stage)
  - VisualAttention.temporal_change (optional)
  - ArousalRegulator.phasic_burst_active (optional)

OUTPUTS (to brain_runner):
  - magnocellular_signal: float 0-1 (M pathway activation)
  - motion_detection_strength: float 0-1 (motion-responsive output)
  - fast_pathway_output: float 0-1 (rapid achromatic signal)

REFS:
  - Kaplan 2018 J Physiol 596:3407 — M pathway physiology
  - Merigan & Maunsell 1993 Annu Rev Neurosci — M pathway motion
  - Maunsell et al. 1990 — M→MT pathway
  - Levitt et al. 2001 — contrast gain M vs P
  - Nassi & Callaway 2009 — parallel pathways from LGN to V1

CITATIONS:
    PMC20878 — Meissirel C, Wikler KC, Chalupa LM et al. (1997). Early Divergence of
        Magnocellular and Parvocellular Functional Subsystems in the Embryonic Primate
        Visual System. Proc Natl Acad Sci USA.
    PMC8794847 — Atapour N, Worthy KH, Rosa MGP (2022). Remodeling of Lateral Geniculate
        Nucleus Projections to Extrastriate Area MT Following Long-Term Lesions of
        Striate Cortex. Cereb Cortex.
"""

from brain.base_mechanism import BrainMechanism


class LGNMagnocellularMotion(BrainMechanism):
    """
    LGN magnocellular (M) pathway — motion detection channel.

    Models M layers 1-2 of the LGN as a high-sensitivity,
    high-speed achromatic motion detection pathway. Receives
    luminance contrast and temporal change signals, outputs
    magnocellular activation and motion signal.
    """

    # M pathway contrast gain (higher than P)
    M_CONTRAST_GAIN = 1.4
    # Temporal response cutoff (normalized)
    TEMPORAL_CUTOFF = 0.75
    # Minimum luminance contrast needed to activate M pathway
    M_CONTRAST_THRESHOLD = 0.08
    # M pathway high-speed gain
    M_SPEED_GAIN = 0.8

    def __init__(self):
        super().__init__(
            name="LGNMagnocellularMotion",
            human_analog="LGN magnocellular layers 1-2 — motion detection, fast achromatic pathway",
            layer="subcortical",
        )
        self.state.setdefault("magnocellular_signal", 0.0)
        self.state.setdefault("motion_detection_strength", 0.0)
        self.state.setdefault("fast_pathway_output", 0.0)
        self.state.setdefault("last_luminance_contrast", 0.0)
        self.state.setdefault("temporal_derivative", 0.0)
        self.state.setdefault("M_layer_activation", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Luminance contrast from retinal stage (achromatic contrast)
        luminance_contrast = prior.get("RetinalOutput", {}).get(
            "luminance_contrast", 0.2
        )
        # Also accept raw contrast from basic sources
        if luminance_contrast == 0.2:
            # Check for raw contrast signal
            luminance_contrast = prior.get("SensoryIntegration", {}).get(
                "contrast_strength", luminance_contrast
            )

        # Temporal change (motion = temporal derivative of contrast)
        temporal_change = prior.get("VisualAttention", {}).get(
            "temporal_change", None
        )
        if temporal_change is None:
            # Compute temporal derivative from successive contrast samples
            prev_contrast = self.state["last_luminance_contrast"]
            temporal_change = abs(luminance_contrast - prev_contrast)

        # Arousal amplifies M pathway responsiveness (neuromodulatory)
        phasic = prior.get("ArousalRegulator", {}).get(
            "phasic_burst_active", False
        )

        # M pathway activation:
        # M neurons respond to luminance contrast above threshold
        # They have high contrast gain and saturate at moderate contrasts
        if luminance_contrast > self.M_CONTRAST_THRESHOLD:
            # Normalized contrast above threshold
            norm_contrast = (luminance_contrast - self.M_CONTRAST_THRESHOLD) / (
                1.0 - self.M_CONTRAST_THRESHOLD
            )
            # M pathway activation: contrast × gain
            m_base = norm_contrast * self.M_CONTRAST_GAIN
        else:
            m_base = 0.0

        # Motion detection: temporal change (movement) strongly activates M
        # M neurons are particularly sensitive to stimulus motion/change
        if temporal_change is not None:
            # Motion signal from temporal derivative
            motion_signal = temporal_change * self.M_SPEED_GAIN
            # M neurons respond to temporal change even without net contrast
            if luminance_contrast <= self.M_CONTRAST_THRESHOLD:
                m_base = max(m_base, motion_signal * 0.5)
            else:
                m_base += motion_signal * 0.5

        # Phasic burst amplifies M pathway
        if phasic:
            m_base = min(1.0, m_base * 1.25)

        # Layer activation: layers 1-2 M pathway (separate from P)
        m_layer = max(0.0, min(1.0, m_base))

        # Magnocellular signal: the LGN M layer output
        magnocellular = m_layer

        # Motion detection strength: M pathway output specialized for motion
        # Scale by temporal cutoff — only higher temporal frequencies count as motion
        motion_detection = magnocellular * min(1.0, temporal_change / self.TEMPORAL_CUTOFF)
        motion_detection = max(0.0, min(1.0, motion_detection))

        # Fast pathway output: M pathway to MT (V5) for motion
        # This is the achromatic fast channel — no color, just speed
        fast_output = magnocellular * 0.7 + motion_detection * 0.3
        fast_output = max(0.0, min(1.0, fast_output))

        self.state["magnocellular_signal"] = round(magnocellular, 4)
        self.state["motion_detection_strength"] = round(motion_detection, 4)
        self.state["fast_pathway_output"] = round(fast_output, 4)
        self.state["last_luminance_contrast"] = luminance_contrast
        self.state["temporal_derivative"] = round(temporal_change, 4)
        self.state["M_layer_activation"] = round(m_layer, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "magnocellular_signal": round(magnocellular, 4),
            "motion_detection_strength": round(motion_detection, 4),
            "fast_pathway_output": round(fast_output, 4),
        }