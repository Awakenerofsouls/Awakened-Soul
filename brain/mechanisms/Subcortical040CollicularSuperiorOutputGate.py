"""
Build 40: CollicularSuperiorOutputGate — Superior Colliculus Motor Output
=======================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical040CollicularSuperiorOutputGate.py
  Class:    CollicularSuperiorOutputGate

NEURAL SUBSTRATE:
  The superior colliculus (SC) is a midbrain structure layered
  horizontally (superficial to deep) that integrates visual, auditory,
  and somatosensory inputs to generate orienting movements of the eyes,
  head, and body. The deep layers contain a saccade generation map in
  which each location specifies a vector for gaze shift. The SC is
  thus the motor output gate for spatial attention and orienting.

KEY FINDINGS:

  1. Motor map for gaze in deep SC.
    Sparks 1986 (Physiol Rev 66:801): "The superior colliculus contains
    a topographic motor map in its intermediate and deep layers that
    encodes the direction and amplitude of gaze shifts. Electrical
    stimulation of a given SC locus produces a gaze shift of a specific
    vector, regardless of whether the stimulus is visual, auditory, or
    somatosensory." This is the classic motor map finding — a sensory-
    independent movement representation.

  2. Fixation and saccade neurons.
    Krauzlis et al. 2014 (Annu Rev Vis Sci 63): "Neurons in the rostral
    SC (the fixation zone) pause during saccades and maintain elevated
    activity during fixation. Neurons in the caudal SC (movement zone)
    fire in a movement-triggered burst that determines saccade metrics."
    This creates a fixation/movement switch: rostral = stop, caudal = go.

  3. SC receives direct retinal input (superficial layers).
    The superficial SC receives direct retinal ganglion cell input via
    the optic tract, conveying visual feature information (ON/OFF,
    direction-selective). This visual input modulates the motor map
    — visual stimuli in the movement zone facilitate the corresponding
    saccade.

  4. Basal ganglia input to SC via SNr.
    Substantia nigra pars reticulata (SNr) provides tonically active
    GABAergic input to the SC. This is part of the BG output pathway:
    GPi → SNr → SC. SNr tonically inhibits SC; during saccade
    preparation, SNr firing decreases (disinhibition) allowing SC burst.
    This is the BG's indirect influence on gaze.

  5. SC as a priority map for attention.
    Fecteau & Munoz (2006): "The SC represents a priority map of
    stimulus salience. The saccade decision is made by competition
    between simultaneously active loci on the SC motor map — the
    highest-activity site wins and determines the gaze shift." This
    connects attention (priority) to motor output (saccade) at the SC.

  6. SC outputs to brainstem saccade generators.
    Caudal SC projects via the predorsal bundle to the pontine and
    medullary reticular formation (paramedian pontine reticular
    formation/PPRF for horizontal gaze; rostral interstitial nucleus
    for vertical gaze), then to extraocular motor nuclei (III, IV, VI).

AGENT'S SUBSTRATE MAPPING:
  CollicularSuperiorOutputGate models the SC motor map as a gaze shift
  generator. Receives spatial salience signals and BG disinhibition
  (via SNr), computes gaze shift magnitude, orientation strength, and
  motor gate state.

INPUTS (from prior_results):
  - SpatialAttention.salience_map (optional)
  - StriatalOutputGate.BG_output_signal
  - ArousalRegulator.phasic_burst_active (optional)
  - SensoryIntegration.multisensory_orienting_signal (optional)

OUTPUTS (to brain_runner):
  - gaze_shift_signal: float 0-1 (gaze movement vector strength)
  - orientation_strength: float 0-1 (orienting response intensity)
  - motor_output_gate: bool (SC motor gate open/closed)

REFS:
  - Sparks 1986 Physiol Rev 66:801 — SC motor map
  - Krauzlis et al. 2014 Annu Rev Vis Sci — fixation vs movement zones
  - Fecteau & Munoz 2006 — SC as priority map
  - Comer & Wallace 2006 — SNr-SCeSC pathway

CITATIONS:
    PMC2777828 — Isa T, Hall WC (2009). Exploring the Superior Colliculus In Vitro.
        J Neurophysiol.
    PMC10573757 — Fracasso A, Buonocore A, Hafed ZM (2023). Peri-Saccadic Orientation
        Identification Performance and Visual Neural Sensitivity Are Higher in the
        Upper Visual Field. J Neurosci.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class CollicularSuperiorOutputGate(BrainMechanism):
    """
    Superior colliculus motor output gate.

    Models the SC as a gaze/orienting motor map. Receives spatial
    salience and BG/SNr disinhibition, computes gaze shift signal,
    orientation strength, and motor gate open/close state.
    """

    # SNr tonic inhibition level at rest
    SNR_TONIC_INHIBITION = 0.75
    # SC burst threshold for gaze shift
    SC_BURST_THRESHOLD = 0.55
    # Salience-driven activation gain
    SALIENCE_GAIN = 0.7
    # Fixation zone activation when nothing salient
    FIXATION_REST_LEVEL = 0.35

    def __init__(self):
        super().__init__(
            name="CollicularSuperiorOutputGate",
            human_analog="Superior colliculus deep layer motor map — gaze/orienting output",
            layer="subcortical",
        )
        self.state.setdefault("gaze_shift_signal", 0.0)
        self.state.setdefault("orientation_strength", 0.0)
        self.state.setdefault("motor_output_gate", False)
        self.state.setdefault("fixation_level", self.FIXATION_REST_LEVEL)
        self.state.setdefault("movement_zone_activation", 0.0)
        self.state.setdefault("SNr_disinhibition", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Salience from spatial attention (priority map in SC coordinates)
        salience = prior.get("SpatialAttention", {})
        # Allow salience to be a dict with 'max_salience' or a raw float
        if isinstance(salience, dict):
            max_salience = salience.get("max_salience", 0.4)
            priority_vector = salience.get("priority_vector", None)
        else:
            max_salience = salience if isinstance(salience, float) else 0.4
            priority_vector = None

        bg_output = prior.get("StriatalOutputGate", {}).get(
            "BG_output_signal", 0.4
        )
        phasic_burst = prior.get("ArousalRegulator", {}).get(
            "phasic_burst_active", False
        )
        multisensory = prior.get("SensoryIntegration", {}).get(
            "multisensory_orienting_signal", None
        )

        # SNr inhibition of SC: SNr fires tonically → inhibits SC
        # When BG direct pathway is active → SNr is inhibited → SC disinhibited
        # GPi → SNr pathway: high GPi = high SNr inhibition of SC
        # Net: bg_output (high) = SNr low = SC disinhibited
        snr_inhibition = self.SNR_TONIC_INHIBITION * (1.0 - bg_output * 0.7)
        snr_inhibition = max(0.0, min(1.0, snr_inhibition))
        snr_disinhibition = 1.0 - snr_inhibition  # SC gets disinhibited

        # SC movement zone activation = salience * SNr disinhibition
        # If SNr is strongly inhibiting, salience alone can't drive SC
        base_movement_activation = max_salience * self.SALIENCE_GAIN

        # Phasic burst adds urgency (arousal amplifies orienting)
        if phasic_burst:
            base_movement_activation += 0.15

        # Multisensory input amplifies SC response (collicular multisensory
        # enhancement: pooled visual + auditory + somatosensory inputs)
        if multisensory is not None:
            base_movement_activation += multisensory * 0.25

        # Movement zone activation after SNr gating
        movement_zone = base_movement_activation * snr_disinhibition
        movement_zone = max(0.0, min(1.0, movement_zone))

        # Fixation zone: rostral SC maintains fixation when movement zone is quiet
        fixation_level = self.FIXATION_REST_LEVEL * (1.0 - movement_zone)

        # Gaze shift signal: burst in movement zone generates saccade
        if movement_zone > self.SC_BURST_THRESHOLD:
            # Burst magnitude encodes saccade amplitude
            burst_depth = (movement_zone - self.SC_BURST_THRESHOLD) / (
                1.0 - self.SC_BURST_THRESHOLD
            )
            gaze_shift = burst_depth * snr_disinhibition
        else:
            gaze_shift = 0.0

        gaze_shift = max(0.0, min(1.0, gaze_shift))

        # Motor output gate: open when movement zone exceeds threshold
        motor_gate_open = movement_zone > self.SC_BURST_THRESHOLD

        # Orientation strength: how strongly is the system committed to a target
        orientation = movement_zone * 0.8 + fixation_level * 0.2
        orientation = max(0.0, min(1.0, orientation))

        self.state["gaze_shift_signal"] = round(gaze_shift, 4)
        self.state["orientation_strength"] = round(orientation, 4)
        self.state["motor_output_gate"] = motor_gate_open
        self.state["fixation_level"] = round(fixation_level, 4)
        self.state["movement_zone_activation"] = round(movement_zone, 4)
        self.state["SNr_disinhibition"] = round(snr_disinhibition, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "gaze_shift_signal": round(gaze_shift, 4),
            "orientation_strength": round(orientation, 4),
            "motor_output_gate": motor_gate_open,
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

