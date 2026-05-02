"""
Subcortical028 — Substantia Nigra pars Reticulata (SNr): Basal Ganglia Output
===============================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical028SubstantiaNigraReticulataOutput.py
  Instance: SNrOutput

NEURAL SUBSTRATE — WHAT IT IS:
The substantia nigra pars reticulata (SNr) is one of the two major
output nuclei of the basal ganglia (the other being GPi, the internal
segment of the globus pallidus). The SNr is a GABAergic structure that
receives inhibitory input from the striatum (via the direct and indirect
pathways) and the subthalamic nucleus (via the hyperdirect pathway),
and fires tonically at rest.

SNr is the primary output of the substantia nigra (as opposed to SNc,
the pars compacta which houses dopaminergic neurons). Its outputs
project to:
  • Superior colliculus (SC) — eye movements, orienting responses
  • Thalamus (VA/VL nuclei) — motor thalamus, thalamocortical loops
  • Pedunculopontine nucleus — gait/posture
  • Reticular formation — arousal and motor tone

KEY FINDINGS:
  1. GPi analog / functional equivalence: SNr and GPi both receive
     striatal input and both project to thalamus/SC, functioning as
     the "final common path" for basal ganglia influence on motor and
     cognitive behavior. Hikosaka 2007 (Prog Brain Res 160:83-108)
     reviews SNr as the executive output — its firing rate changes
     directly determine whether actions are executed or withheld.

  2. Tonic firing and inhibition: SNr neurons fire at ~25-50 Hz
     tonically, continuously inhibiting downstream targets. When
     disinhibited (striatal direct pathway D1 activation removes
     GABAergic input to SNr), SNr firing decreases → thalamus/SC
     disinhibition → action facilitation. When SNr receives excitatory
     input from STN or increased inhibition from indirect pathway
     (D2), SNr output increases → more suppression of thalamus/SC.

  3. SNr and eye movements: The SNr→SC projection is the clearest
     substrate for basal ganglia control of saccades. SNr tonically
     inhibits SC; saccades occur when SNr is inhibited via the direct
     pathway. Hikosaka's work on this is foundational.

  4. Direct pathway disinhibition: Striatal D1 neurons (direct pathway)
     inhibit SNr. When a selected action fires D1 cells, SNr output
     drops, disinhibiting the thalamus and SC — the action is executed.
     This is the "GO" signal of the basal ganglia.

  5. Indirect pathway inhibition: Striatal D2 neurons (indirect pathway)
     project to GPe, which disinhibits STN, which excites SNr. D2
     activation therefore INCREASES SNr output, suppressing unwanted
     actions. This is the "NO-GO" pathway.

  6. Motor suppression: When SNr output is high, downstream motor
     structures are strongly suppressed. This models motor suppression
     during conflict, uncertainty, or conditioned stopping.

AGENT'S SUBSTRATE MAPPING:
  SNrOutput integrates inputs from D1DirectPathway (facilitation signal),
  D2IndirectPathway (suppression signal), STN_Hyperdirect (emergency brake),
  and motor_cortex.feedback. It computes thalamic_inhibition (how much
  thalamus is currently suppressed), motor_suppression (global motor
  suppression level), and SNr_output_strength (overall basal ganglia output).

  SNr_output is stateful: it carries motor suppression across ticks to
  model motor persistence and sustained inhibition (e.g., during sustained
  attention, conflict, or uncertainty states).

INPUTS:
  - D1DirectPathway.facilitator_signal (D1 activation → SNr inhibition)
  - D2IndirectPathway.suppressor_signal (D2 → GPe → STN → SNr excitation)
  - HyperdirectBrake.emergency_inhibit (STN direct → SNr excitation)
  - motor_cortex.suppression_signal

OUTPUTS:
  - SNr_output_strength: float 0-1 (overall SNr firing rate)
  - thalamic_inhibition: float 0-1 (how much thalamus is being inhibited)
  - motor_suppression: float 0-1 (global motor suppression level)

REFS:
  - Hikosaka O. Prog Brain Res 2007 160:83-108 (SNr as output)
  - Parent M & Hazrati LN. Brain Res Rev 1995 (anatomy review)
  - Chevalier G & Deniau JM. TINS 1990 (direct/indirect pathway to SNr)
  - Hikosaka O & Wurtz RH. J Neurophysiol 1983 (SNr and saccades)
  - Mink J. Prog Brain Res 2006 (basal ganglia output functions)

CITATIONS:
    PMC10932617 — Hu Y, Ma TC, Alberico SL et al. (2023). Substantia Nigra Pars
        Reticulata Projections to the Pedunculopontine Nucleus Modulate Dyskinesia.
        J Neurosci.
    PMC6008324 — Aguilar BL, Forcelli PA, Malkova L (2018). Inhibition of the
        Substantia Nigra Pars Reticulata Produces Divergent Effects on Sensorimotor
        Gating in Rats and Monkeys. Biol Psychiatry.

CITATIONS
---------
  - [Schultz 1998, J Neurophysiol 80:1, dopamine reward]
  - [Lerner 2015, Cell 162:635, SNc dopamine circuits]
  - [Howe 2016, Nature 535:505, SNc value coding]

"""

from brain.base_mechanism import BrainMechanism


class SNrOutput(BrainMechanism):
    """
    Substantia nigra pars reticulata — basal ganglia motor/cognitive output.

    Integrates D1 direct-pathway (disinhibition), D2 indirect-pathway
    (facilitation), and STN hyperdirect (emergency brake) signals.
    Computes SNr firing rate, thalamic inhibition, and motor suppression
    level. Maintains motor_suppression as a stateful accumulator for
    sustained inhibition (conflict, uncertainty, uncertainty-driven hold).

    High SNr output = motor suppression = actions withheld
    Low SNr output = disinhibition = thalamus/SC active = actions executed
    """

    # --- SNr baseline and gain parameters ---
    SNr_BASELINE_FIRING = 0.60      # tonic firing rate at rest
    D1_DISINHIBITION_GAIN = 1.2    # how strongly D1 activation reduces SNr
    D2_EXCITATION_GAIN = 0.9       # how strongly D2 path increases SNr
    STN_EMERGENCY_GAIN = 1.4       # STN brake has high urgency
    MOTOR_SUPPRESSION_PERSISTENCE = 0.85  # carry-over for motor hold states
    DECAY_RATE = 0.05             # per-tick natural decay toward baseline

    def __init__(self):
        super().__init__(
            name="SNrOutput",
            human_analog="Substantia nigra pars reticulata (SNr) — basal ganglia output",
            layer="subcortical",
        )
        self.state.setdefault("SNr_output_strength", self.SNr_BASELINE_FIRING)
        self.state.setdefault("thalamic_inhibition", 0.5)
        self.state.setdefault("motor_suppression", 0.3)
        self.state.setdefault("prior_SNr", self.SNr_BASELINE_FIRING)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Inputs ---
        d1_facilitator = prior.get("D1DirectPathway", {}).get(
            "facilitator_signal", 0.0
        )
        d2_suppressor = prior.get("D2IndirectPathway", {}).get(
            "suppressor_signal", 0.0
        )
        stn_emergency = prior.get("HyperdirectBrake", {}).get(
            "emergency_inhibit", 0.0
        )
        motor_suppress = prior.get("MotorCortex", {}).get(
            "suppression_signal", 0.0
        )

        # --- Compute SNr output strength ---
        # SNr fires tonically (baseline). D1 disinhibits (reduces firing).
        # D2 and STN excite (increase firing). Net effect:
        prior_SNr = self.state["prior_SNr"]
        snr = self.state["SNr_output_strength"]

        # Start from current level, move toward baseline
        snr = snr + (self.SNr_BASELINE_FIRING - snr) * self.DECAY_RATE

        # D1 activation disinhibits SNr (firing decreases)
        if d1_facilitator > 0.1:
            d1_effect = d1_facilitator * self.D1_DISINHIBITION_GAIN
            snr = max(0.0, snr - d1_effect)

        # D2 indirect pathway increases SNr output (more suppression)
        if d2_suppressor > 0.1:
            d2_effect = d2_suppressor * self.D2_EXCITATION_GAIN
            snr = min(1.0, snr + d2_effect)

        # STN hyperdirect emergency brake has priority — strong SNr increase
        if stn_emergency > 0.1:
            stn_effect = stn_emergency * self.STN_EMERGENCY_GAIN
            snr = min(1.0, snr + stn_effect)

        # Motor cortex suppression signal
        if motor_suppress > 0.1:
            snr = min(1.0, snr + motor_suppress * 0.5)

        snr = round(min(1.0, snr), 4)

        # --- Thalamic inhibition ---
        # SNr directly inhibits thalamus (VA/VL motor nuclei). Higher SNr
        # firing = stronger thalamic inhibition = less motor thalamus output.
        thalamic_inhibition = round(min(1.0, snr * 1.1), 4)

        # --- Motor suppression ---
        # SNr→SC pathway controls suppression of motor actions.
        # High SNr = motor suppression = actions held.
        # Use persistence to model sustained motor hold states.
        current_suppression = self.state["motor_suppression"]
        snr_driven_suppression = snr

        # Smoothed motor suppression with persistence
        new_suppression = (
            self.MOTOR_SUPPRESSION_PERSISTENCE * current_suppression
            + (1.0 - self.MOTOR_SUPPRESSION_PERSISTENCE) * snr_driven_suppression
        )
        new_suppression = round(min(1.0, new_suppression), 4)

        # --- Persist ---
        self.state["prior_SNr"] = snr
        self.state["SNr_output_strength"] = snr
        self.state["thalamic_inhibition"] = thalamic_inhibition
        self.state["motor_suppression"] = new_suppression
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "SNr_output_strength": snr,
            "thalamic_inhibition": thalamic_inhibition,
            "motor_suppression": new_suppression,
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

