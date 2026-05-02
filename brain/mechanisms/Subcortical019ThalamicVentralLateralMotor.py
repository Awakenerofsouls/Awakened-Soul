"""
Subcortical019ThalamicVentralLateralMotor.py — Wire 19: ThalamicVLMotorRelay

Motor thalamus — cerebellar input relay to motor/premotor cortex.

Neural analog: Ventral lateral (VL) thalamic nucleus. The VL is the primary
cerebellar-recipient relay for motor cortex. Purkinje cells of the deep
cerebellar nuclei project via the superior cerebellar peduncle (SCP) to VL,
which in turn projects topographically to primary motor (M1), premotor (PMC),
and supplementary motor (SMA) cortices. This is the cerebellar-thalamo-cortical
(Cb-Th-Cx) loop underpinning coordinated movement sequencing.

ANATOMY (Jones 2007):
  - VL receives from: deep cerebellar nuclei (dentate, interposed, fastigial)
    via the decussation of the superior cerebellar peduncle
  - VL sends to: M1 (Brodmann 4), premotor cortex (BA 6), SMA
  - Two subdivisions: VLo (oralis) = cerebellar input zone; VLc = cerebellar/
    basal ganglia convergence zone
  - Receptive field organization: somatotopic, matched to the contralateral body

CEREBELLAR INPUT — what VL relays:
  - Error teaching signals from Purkinje cells (via deep nuclei)
  - Timing signals for coordinated sequences (Purkinje cells fire in
    precisely timed patterns during motor learning)
  - Forward model predictions (cerebellum as internal model of body dynamics)
  - VL amplifies cerebellar signals for cortical consumption

HALASSA & SHERMAN 2019 THALAMIC TYPES:
  First-order relays (first receipt from subcortical): e.g., MGN → V1
  Higher-order relays (first receipt from layer 5 cortex): e.g., layer 5
    motor cortex → VL. This classifies VL as a "higher-order" relay that
    receives corticothalamic input from L5 pyramidal neurons in motor cortex.
  So VL sits at the nexus of BOTH cerebellar input AND cortical feedback.

KEY FUNCTIONS:
  1. Relay strength: strength of VL signal to motor cortex (modulated by
     cerebellar firing rate and current motor state)
  2. Motor input integration: combines cerebellar teaching signals with
     cortical feedback (Cortico-thalamic loop)
  3. Motor cortex signal: drives M1/PMC activation for movement execution

CLINICAL RELEVANCE:
  - VL lesion → cerebellar ataxia (can initiate but cannot coordinate)
  - Deep brain stimulation of VL (and VLp) used for tremor (interrupts
    thalamo-cortical tremor circuits)
  - Cerebellar-thalamic pathway is key target for Parkinson's DBS

REFS:
- Jones 2007 Thalamus Vol I & II (2nd ed.) — definitive VL anatomy
- Halassa & Sherman 2019 Neuron 103:7-19 — first-order vs higher-order taxonomy
- Middleton & Strick 2001 Trends Neurosci — cerebellar output nuclei
- Gao et al. 2018 Nat Neurosci — cerebellar timing for motor sequencing
- Bostan & Strick 2018 J Neurosci — cerebellar-basal ganglia-VL loop

CITATIONS:
    PMC6695568 — Bohne P, Schwarz MK, Herlitze S et al. (2019). A New Projection From
        the Deep Cerebellar Nuclei to the Hippocampus via the Ventrolateral and
        Laterodorsal Thalamus in Mice. Front Neural Circuits.
    PMC12499924 — Lenz FA, Meeker TJ, Saffer MI et al. (2025). Neuroscience of Human
        Ventral Lateral Thalamic Nucleus Related to Movement and Movement Disorders.
        Neuroscientist.


CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia habits]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Hikosaka 2002, Curr Opin Neurobiol 12:217, motor sequences]
"""

from brain.base_mechanism import BrainMechanism


class ThalamicVentralLateralMotor(BrainMechanism):
    """
    Motor thalamus — cerebellar input relay to M1/premotor cortex.

    Receives cerebellar teaching signals (from deep cerebellar nuclei),
    integrates with cortical feedback from layer 5 motor neurons, and
    relays a processed motor coordination signal to motor cortex.

    This is the VL: highest-fidelity cerebellar relay in the thalamus.
    """

    # Relay parameters
    RELAY_GAIN = 0.80          # VL signal amplification
    CORTICAL_FEEDBACK_WEIGHT = 0.30  # Layer 5 cortical influence on VL
    MOTOR_BASELINE = 0.25      # Baseline motor readiness
    DECAY_RATE = 0.05           # Signal decay per tick
    MOTOR_THRESHOLD = 0.35     # Threshold for motor_cortex_signal output

    def __init__(self):
        super().__init__(
            name="ThalamicVentralLateralMotor",
            human_analog="Ventral lateral (VL) thalamus — cerebellar motor relay",
            layer="subcortical",
        )
        self.state.setdefault("VL_relay_strength", 0.0)
        self.state.setdefault("cerebellar_motor_input", 0.0)
        self.state.setdefault("motor_cortex_signal", 0.0)
        self.state.setdefault("cortical_feedback_level", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("cerebellar_history", [])

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source 1: Cerebellar deep nuclei output (via SCP decussation)
        # Deep Cerebellar Nuclei Output fires with learned timing signals
        cerebellar_output = prior.get("DeepCerebellarNucleiOutput", {})
        cerebellar_signal = cerebellar_output.get("nuclear_output_strength", 0.0)

        # Source 2: SCP relay (superior cerebellar peduncle)
        scp_relay = prior.get("SuperiorCerebellarPeduncleRelay", {})
        scp_signal = scp_relay.get("SCP_signal_strength", 0.0)

        # Source 3: Purkinje error signals (from cerebellar learning)
        purkinje = prior.get("PurkinjeCellErrorLearning", {})
        purkinje_error = purkinje.get("error_signal_strength", 0.0)

        # Combine cerebellar inputs
        combined_cerebellar = (
            cerebellar_signal * 0.50
            + scp_signal * 0.30
            + purkinje_error * 0.20
        )

        # Source 4: Layer 5 cortical feedback (VL = higher-order relay)
        # Motor cortex L5 sends efference copy back to VL
        cortical_fb = prior.get("CorticothalamicLayer5Feedback", {})
        cortical_strength = cortical_fb.get("layer5_efference_strength", 0.0)

        # VL relay strength: amplified cerebellar input + cortical modulation
        raw_relay = (
            combined_cerebellar * self.RELAY_GAIN
            + cortical_strength * self.CORTICAL_FEEDBACK_WEIGHT
        )
        vl_relay = max(0.0, min(1.0, raw_relay))

        # Motor cortex signal: gated by motor readiness baseline
        # Only fires if VL relay is strong enough
        motor_signal = 0.0
        if vl_relay > self.MOTOR_THRESHOLD:
            motor_signal = max(
                0.0,
                min(1.0, (vl_relay - self.MOTOR_THRESHOLD) * 2.0 + self.MOTOR_BASELINE)
            )

        # Decay VL relay if no strong cerebellar input
        if combined_cerebellar < 0.1:
            vl_relay = max(0.0, vl_relay - self.DECAY_RATE)

        # Update state
        self.state["VL_relay_strength"] = round(vl_relay, 4)
        self.state["cerebellar_motor_input"] = round(combined_cerebellar, 4)
        self.state["motor_cortex_signal"] = round(motor_signal, 4)
        self.state["cortical_feedback_level"] = round(cortical_strength, 4)
        self.state["tick_count"] += 1

        # Track cerebellar history for diagnostic
        hist = list(self.state["cerebellar_history"])
        hist.append(round(combined_cerebellar, 3))
        if len(hist) > 10:
            hist = hist[-10:]
        self.state["cerebellar_history"] = hist

        self.persist_state()

        return {
            "VL_relay_strength": round(vl_relay, 4),
            "cerebellar_motor_input": round(combined_cerebellar, 4),
            "motor_cortex_signal": round(motor_signal, 4),
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

