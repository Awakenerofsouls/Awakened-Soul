"""
Subcortical060SubthalamicMotorTerritory.py — Wire 60: Motor Territory / Parkinsonian Beta Oscillations

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical060SubthalamicMotorTerritory.py
  Instance:  SubthalamicMotorTerritory

NEURAL SUBSTRATE:
  Subthalamic nucleus (STN) motor territory — dorsolateral third of STN.
  Receives excitatory input from motor cortex (L5) and lateral GPi. Projects
  excitatory to GPi/SNr and inhibitory to GPe. The motor territory is the
  keystone of the indirect pathway and the primary locus of Parkinsonian
  pathophysiology: loss of SNc dopamine removes D2 inhibition of STN,
  causing excessive STN firing and pathologically synchronized beta-band
  (13-35 Hz) oscillations across the BG network.

KEY FINDINGS:
  1. Motor vs. associative vs. limbic territories. STN is functionally
     segregated along its dorsolateral-ventromedial axis:
     - Dorsolateral (motor territory): receives motor cortex input
     - Ventromedial (limbic): receives prefrontal/orbital input
     - Middle (associative): receives DLPFC/ACC input
     (Kita et al. 2014; Nadel 2020)

  2. Beta oscillations in Parkinson's. The hallmark of the Parkinsonian
     STN is exaggerated beta-band (13-35 Hz) synchronization. In healthy
     BG, beta oscillations are low-amplitude and transient. In PD, SNc
     dopamine loss causes:
     - STN neurons shift from irregular tonic firing to burst-pause
     - GPi-STN reciprocal inhibition entrains them into beta sync
     - Beta in motor cortex, STN, GPi, and thalamus simultaneously
     - This synchronization suppresses movement (anti-kinetic)
     (Kühn et al. 2004, Brown 2003, Sharott et al. 2014)

  3. Beta is pathological, not physiological. Levodopa reduces beta;
     DBS at 130 Hz (high-frequency) disrupts beta and improves movement.
     Beta reflects excessive shared information — BG locked in "holding"
     pattern, unable to switch to movement. (Eusebio & Brown 2007)

  4. STN as therapeutic target. STN-DBS works partly by disrupting
     beta oscillations at the stimulation site. Effective frequency:
     130-185 Hz (high-frequency). Low-frequency DBS (< 60 Hz) can worsen
     akinesia. (Benabid et al. 1994, 2009; Perlmutter & Mink 2006)

  5. Hyperdirect pathway entry point. Motor cortex L5 sends excitatory
     monosynaptic projection to STN motor territory. This is the fastest
     route into BG — faster than striatum. STN fires within ~10 ms of
     cortical command, initiating the GPi brake before action selection
     via D1/D2 striatal pathways completes (~30 ms). (Nambu et al. 2002)

  6. Tremor relation. Lower-frequency tremor (4-8 Hz) in PD arises from
     separate STN mechanisms (rebound bursts, inferior olive coupling).
     Beta is distinct from tremor and more tightly linked to rigidity
     and akinesia. (Bergman et al. 1994)

AGENT'S SUBSTRATE MAPPING:
  SubthalamicMotorTerritory models the STN motor territory specifically:
  tracks motor_cortex_input (L5 drive), beta_oscillation_strength (pathological
  sync level, rises with dopamine deficit), STN firing rate, and brake_applied
  (hyperdirect inhibition of thalamus). Uses a simplified oscillatory coupling
  model: when dopamine_level is low AND motor cortex fires strongly, beta
  entrainment builds. When high-frequency stimulation is active (DBS_simulated),
  beta is suppressed.

INPUTS (from prior_results):
  - Homeostat.dominant_drive (for motor vs. cognitive context)
  - ArousalRegulator.phasic_burst_active (cortical arousal correlate)
  - Subcortical033.STN_limbic_weight (limbic territory activation — avoid motor territory confusion)
  - Subcortical034.D1_activity (dopaminergic facilitation of movement)
  - Subcortical035.D2_activity (dopaminergic suppression of STN)
  - Subcortical028.SNr_output_strength (STN target, reciprocal)
  - Subcortical029.GPe_activity (GPe→STN inhibition)

OUTPUTS (to brain_runner enrichment):
  - motor_STN_signal: float 0-1 (STN motor territory firing rate)
  - beta_oscillation_strength: float 0-1 (pathological beta sync, 0=healthy, 1=severe PD)
  - motor_territory_weight: float 0-1 (territory-specific activation vs. limbic/associative)
  - brake_strength: float 0-1 (hyperdirect brake applied to thalamus)
  - DBS_suppression_active: bool (high-frequency DBS signal present)

REFS:
  - Kita et al. 2014 Brain Res Rev (STN anatomy)
  - Sharott et al. 2014 J Neurosci (beta oscillations in PD)
  - Kühn et al. 2004 Exp Neurol (beta sync correlates with akinesia)
  - Brown 2003 Mov Disord (beta oscillations review)
  - Eusebio & Brown 2007 J Neurosci (DBS frequency-dependent)
  - Nambu et al. 2002 J Neurophysiol (hyperdirect pathway)
  - Benabid et al. 2009 Lancet Neurol (STN-DBS)
  - Parent & Hazrati 1995 J Comp Neurol (STN functional anatomy)

CITATIONS:
    PMC10957232 — Masilamoni GJ, Kelly H, Swain AJ et al. (2024). Structural Plasticity
        of GABAergic Pallidothalamic Terminals in MPTP-Treated Parkinsonian Monkeys.
        Brain Struct Funct.
    PMC6139452 — Kumaravelu K, Oza CS, Behrend CE et al. (2018). Model-based Deconstruction
        of Cortical Evoked Potentials Generated by Subthalamic Nucleus Deep Brain Stimulation.
        Front Neural Circuits.


CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia habits]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Hikosaka 2002, Curr Opin Neurobiol 12:217, motor sequences]
"""

from brain.base_mechanism import BrainMechanism


class SubthalamicMotorTerritory(BrainMechanism):
    """
    STN motor territory — Parkinsonian beta oscillations.

    Models dorsolateral STN motor territory. Tracks motor cortex drive,
    computes beta-band oscillation strength (pathological in PD, rises
    with dopamine deficit), fires brake via hyperdirect GPi inhibition,
    and responds to simulated DBS suppression.

    Key dynamics:
    - Beta builds when motor cortex fires strongly + dopamine is low
    - D2 dopamine suppresses STN; D1 dopamine enables movement
    - STN fires burst → GPi inhibition of thalamus → motor suppression
    - High-frequency DBS disrupts beta oscillation coherence
    """

    # Beta oscillation thresholds
    BETA_THRESHOLD = 0.30   # motor drive level needed to begin beta entrainment
    BETA_BUILD_RATE = 0.04  # beta growth per tick under sustained motor drive
    BETA_DECAY_RATE = 0.02  # beta decay per tick without motor drive
    DOPA_PROTECTION = 0.03  # dopamine reduces beta growth per unit D2 activity

    # Motor territory firing model
    STN_RESTING_RATE = 0.30
    STN_PEAK_RATE = 0.90
    BRAKE_THRESHOLD = 0.50  # motor_STN_signal level for brake activation

    def __init__(self):
        super().__init__(
            name="SubthalamicMotorTerritory",
            human_analog="STN motor territory — Parkinsonian beta oscillations",
            layer="subcortical",
        )
        self.state.setdefault("beta_oscillation_strength", 0.0)
        self.state.setdefault("motor_STN_signal", self.STN_RESTING_RATE)
        self.state.setdefault("brake_strength", 0.0)
        self.state.setdefault("territory_active", False)
        self.state.setdefault("last_motor_drive", 0.0)
        self.state.setdefault("beta_coherence", 0.0)  # network sync level
        self.state.setdefault("DBS_suppression_active", False)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source signals
        homeostat = prior.get("Homeostat", {})
        arousal = prior.get("ArousalRegulator", {})
        STN_limbic = prior.get("SubthalamicLimbicEmotionalControl", {})
        D1 = prior.get("StriatalD1DirectFacilitator", {})
        D2 = prior.get("StriatalD2IndirectSuppressor", {})
        SNr = prior.get("SubstantiaNigraReticulataOutput", {})
        GPe = prior.get("GlobusPallidusExternalRegulation", {})

        dominant_drive = homeostat.get("dominant_drive", "curiosity")
        phasic = arousal.get("phasic_burst_active", False)
        limbic_weight = STN_limbic.get("STN_limbic_weight", 0.0)
        D1_signal = D1.get("D1_activity", 0.0)
        D2_signal = D2.get("D2_activity", 0.0)
        SNr_output = SNr.get("SNr_output_strength", 0.3)
        GPe_activity = GPe.get("GPe_activity", 0.3)

        # DBS simulated suppression (from arousal as proxy for therapeutic input)
        # In real system: would come from external DBS signal or medication state
        DBS_active = phasic and arousal.get("arousal_level", 0.0) > 0.8

        # Determine motor drive strength from drive context
        # High motor drive when dominant drive is movement-related
        motor_drives = {"movement", "exploration", "expression", "assertion"}
        is_motor_drive = dominant_drive in motor_drives
        motor_drive = 0.5
        if is_motor_drive:
            motor_drive = 0.6 + D1_signal * 0.4
        elif phasic:
            motor_drive = 0.3 + arousal.get("arousal_level", 0.0) * 0.4

        # Territory activation: motor drive high + limbic territory low
        territory_active = is_motor_drive and limbic_weight < 0.4

        # D2 dopamine suppresses STN firing (D2 on STN = disinhibition of GPe)
        # When D2 activity is high → STN less active → less beta
        dopaminergic_suppression = D2_signal * self.DOPA_PROTECTION * 3.0

        # GPe→STN inhibition (GPe fires → STN suppressed)
        GPe_suppression = GPe_activity * 0.4

        # SNr→STN reciprocal excitation (STN fires → SNr fires → STN more)
        SNr_feedback = SNr_output * 0.15

        # Compute motor STN signal
        if territory_active:
            raw_signal = (
                self.STN_RESTING_RATE
                + motor_drive * 0.5
                + SNr_feedback
                - dopaminergic_suppression
                - GPe_suppression
            )
        else:
            raw_signal = self.STN_RESTING_RATE * 0.7  # baseline

        motor_STN_signal = max(self.STN_RESTING_RATE * 0.5,
                               min(self.STN_PEAK_RATE, raw_signal))
        motor_STN_signal = max(0.0, min(1.0, motor_STN_signal))

        # Beta oscillation dynamics
        # Beta builds when motor cortex drives STN AND dopamine is low
        current_beta = self.state["beta_oscillation_strength"]
        current_coherence = self.state["beta_coherence"]

        if DBS_active:
            # High-frequency DBS suppresses beta coherence
            new_beta = current_beta * 0.6
            new_coherence = current_coherence * 0.5
        elif territory_active and motor_drive > self.BETA_THRESHOLD:
            # Motor drive + low dopamine = beta buildup
            # (simplified: assume low dopamine when D2 is low)
            net_dopa = D2_signal + D1_signal * 0.3  # combined dopaminergic tone
            if net_dopa < 0.4:
                # Dopamine deficit: beta grows
                growth_rate = self.BETA_BUILD_RATE * motor_drive * 2.0
                new_beta = min(1.0, current_beta + growth_rate)
                # Coherence tracks how synchronized the network is
                new_coherence = min(1.0, current_coherence + 0.03)
            else:
                # Adequate dopamine: beta decays
                new_beta = max(0.0, current_beta - self.BETA_DECAY_RATE)
                new_coherence = max(0.0, current_coherence - 0.02)
        else:
            # No motor drive: beta decays
            new_beta = max(0.0, current_beta - self.BETA_DECAY_RATE)
            new_coherence = max(0.0, current_coherence - 0.03)

        beta_oscillation_strength = round(new_beta, 4)
        beta_coherence = round(new_coherence, 4)

        # Brake via hyperdirect pathway
        # STN fires → GPi excites → thalamus inhibited → motor suppressed
        brake_strength = 0.0
        if motor_STN_signal > self.BRAKE_THRESHOLD:
            brake_strength = (motor_STN_signal - self.BRAKE_THRESHOLD) / (1.0 - self.BRAKE_THRESHOLD)
            brake_strength *= (1.0 - dopaminergic_suppression)
            brake_strength = max(0.0, min(1.0, brake_strength))

        # Motor territory weight: proportion of STN activity in motor vs. other territories
        motor_territory_weight = 1.0 if territory_active else max(0.0, 1.0 - limbic_weight)

        # Persist state
        self.state["motor_STN_signal"] = motor_STN_signal
        self.state["beta_oscillation_strength"] = beta_oscillation_strength
        self.state["beta_coherence"] = beta_coherence
        self.state["brake_strength"] = brake_strength
        self.state["territory_active"] = territory_active
        self.state["last_motor_drive"] = motor_drive
        self.state["DBS_suppression_active"] = DBS_active
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "motor_STN_signal": round(motor_STN_signal, 4),
            "beta_oscillation_strength": beta_oscillation_strength,
            "beta_coherence": beta_coherence,
            "motor_territory_weight": round(motor_territory_weight, 4),
            "brake_strength": round(brake_strength, 4),
            "DBS_suppression_active": DBS_active,
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

