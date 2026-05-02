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

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

