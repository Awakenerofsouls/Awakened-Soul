"""
Subcortical056StriatalLowThresholdSpikeInterneurons.py — Wire 56: LTS Interneurons

Neural substrate: Striatal low-threshold spiking (LTS) interneurons.

LTS interneurons are a distinct class of striatal GABAergic interneurons
characterized by their low-threshold calcium spikes and slow-spiking
firing pattern (10-20 Hz). They are neuropeptide Y (NPY) positive and
somatostatin (SOM) positive, distinguishing them from FSIs (PV+) and
TANs (choline). Kawaguchi 1993 first characterized them in the rat
striatum; Beatty et al. 2012 demonstrated their role in network
integration and behavioral state modulation.

KEY RESEARCH FINDINGS:
1. Anatomical identity. Kawaguchi 1993: LTS neurons (NPY/SOM+) are
   ∼1% of striatal neurons, with extended dendritic trees spanning
   up to 300 μm. They receive input from cortical pyramidal cells
   (like FSIs) but have slower kinetics and broader integration windows.
   They inhibit MSNs via GABA_A receptors with slower kinetics than
   FSI-mediated IPSCs.

2. Low-threshold calcium spike (LTS). The defining characteristic:
   LTS neurons have a lower threshold for calcium spike generation
   than FSIs. They exhibit a "plateau" afterhyperpolarization and
   can fire at lower depolarization levels. This makes them responsive
   to convergent inputs from multiple cortical areas.

3. Network integration role. Beatty 2012: "LTS neurons integrate
   information across a broader temporal and spatial window than
   FSIs." They act as integrators of behavioral state — their firing
   reflects the integration of multiple concurrent signals (cognitive,
   emotional, motor). This makes them suited for state-dependent
   modulation of striatal output.

4. Slow inhibition and network dynamics. LTS-mediated inhibition has
   a slower time course (50-200 ms decay) compared to FSI (10-30 ms).
   This creates a "slow gating" effect: LTS inhibition can suppress
   MSN firing for hundreds of milliseconds after activation, implementing
   a broad temporal filter. This is important for sustained behavioral
   states (maintaining posture, sustained attention).

5. Integration with cholinergic system. LTS neurons receive input from
   TANs (tonically active cholinergic interneurons). ACh from TANs
   activates muscarinic receptors on LTS neurons, modulating their
   excitability. The cholinergic snapshot (timestamped events in
   the striatum, Apex 2013) can activate LTS neurons, which then
   provide a slow inhibitory gating of MSNs following the cholinergic
   signal — linking reward prediction errors to motor suppression.

6. Behavioral state modulation. LTS neurons fire during sustained
   behavioral states: immobility, sustained attention, grooming
   sequences. Their slow inhibition maintains MSN suppression during
   these states, effectively implementing a "hold" function — 
   "don't move while I'm doing this."

7. Synchrony in theta/alpha band. LTS neurons show rhythmic firing
   in the theta/alpha band (4-14 Hz) during network-level oscillations.
   This is slower than FSI gamma — LTS coordinates slower state
   transitions (e.g., shifting between behavioral modes).

8. NPY modulation. NPY is co-released with GABA from LTS neurons.
   NPY acts on Y1 receptors on MSNs to reduce excitability, providing
   a slower neuromodulatory effect in addition to fast GABAergic
   inhibition.

OUTPUTS:
  LTS_activity: float 0-1 — current LTS interneuron activation
  network_integration_signal: float 0-1 — degree of multi-domain integration
  slow_inhibition_strength: float 0-1 — strength of the slow MSN suppression

INPUTS:
  cortical_convergence: multiple cortical inputs converging
  cholinergic_signal: TAN activity (cholinergic "snapshot")
  behavioral_state: sustained vs. phasic behavioral mode
  emotional_input: limbic/emotional convergence

CITATIONS:
    PMC6507406 — Assous M, Tepper JM (2019). Excitatory Extrinsic Afferents to
        Striatal Interneurons and Interactions With Striatal Microcircuitry.
        Front Syst Neurosci.
    PMC5477498 — Assous M, Kaminer J, Shah F et al. (2017). Differential Processing
        of Thalamic Information Via Distinct Striatal Interneuron Circuits.
        J Neurosci.


CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia]
  - [Yin 2006, Nat Rev Neurosci 7:464, dorsal striatum]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

from brain.base_mechanism import BrainMechanism


class StriatalLowThresholdSpikeInterneurons(BrainMechanism):
    """
    Striatal low-threshold spiking (LTS) interneurons.

    Provide slow, integrative inhibition across striatal MSNs.
    Unlike FSIs (fast, precise), LTS neurons integrate over broader
    temporal/spatial windows and implement slow gating for sustained
    behavioral states.
    """

    LTS_FIRING_RATE = 0.25
    INTEGRATION_WINDOW = 0.40  # temporal window for integration
    SLOW_INHIBITION_TAU = 180.0  # ms decay time for LTS inhibition
    SLOW_DECAY_RATE = 0.015
    THETA_FREQ = 8.0  # Hz — LTS theta rhythm

    def __init__(self):
        super().__init__(
            name="StriatalLowThresholdSpikeInterneurons",
            human_analog="Striatal LTS/NPY/SOM+ interneurons — slow integrative inhibition",
            layer="subcortical",
        )
        self.state.setdefault("LTS_activity", 0.0)
        self.state.setdefault("network_integration_signal", 0.5)
        self.state.setdefault("slow_inhibition_strength", 0.0)
        self.state.setdefault("theta_phase", 0.0)
        self.state.setdefault("slow_inhibition_accumulator", 0.0)
        self.state.setdefault("sustained_suppression", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        cortical_convergence = input_data.get("cortical_convergence", 0.4)
        cholinergic_signal = input_data.get("cholinergic_signal", 0.3)
        behavioral_state = input_data.get("behavioral_state", "phasic")
        emotional_input = input_data.get("emotional_input", 0.5)
        motor_convergence = input_data.get("motor_convergence", 0.3)

        # --- LTS activation ---
        # LTS fires when multiple convergent inputs sum above threshold
        # (low-threshold = less drive needed to reach spike)
        cortical_contribution = cortical_convergence * 0.35
        cholinergic_contribution = cholinergic_signal * 0.25  # ACh activates LTS via mAChRs
        emotional_contribution = (emotional_input - 0.5) * 0.20  # centered
        motor_contribution = motor_convergence * 0.15

        total_convergence = (
            cortical_contribution
            + cholinergic_contribution
            + emotional_contribution
            + motor_contribution
        )

        # LTS has low threshold — fires at lower activation than FSI
        raw_activity = self.LTS_FIRING_RATE + total_convergence
        LTS_activity = max(0.0, min(1.0, raw_activity))

        # --- Network integration signal ---
        # Network integration is the degree to which multiple domains converge
        # Higher integration = LTS fires more, providing stronger slow inhibition
        integration_composite = (
            cortical_convergence * 0.3
            + (cholinergic_signal > 0.5) * 0.25  # boolean: cholinergic snapshot detected
            + emotional_input * 0.25
            + motor_convergence * 0.20
        )

        # EMA smoothing of integration signal
        new_integration = self.state["network_integration_signal"] * 0.85 + integration_composite * 0.15
        self.state["network_integration_signal"] = max(0.0, min(1.0, new_integration))

        # --- Theta rhythm ---
        # LTS neurons fire in theta band — slower than FSI gamma
        theta_increment = (self.THETA_FREQ / 60.0) * 360.0
        new_theta_phase = (self.state["theta_phase"] + theta_increment) % 360.0
        self.state["theta_phase"] = new_theta_phase

        theta_wave = 0.5 * (1.0 + (1.0 if new_theta_phase < 180 else -1.0))
        theta_modulation = 0.08 * theta_wave

        # --- Slow inhibition ---
        # LTS inhibition is slow (50-200 ms decay) — a sustained effect
        # The slow_inhibition_strength accumulates with LTS firing
        # and decays slowly over time
        if LTS_activity > 0.3:
            inhibition_increment = LTS_activity * 0.08 * (1.0 + theta_modulation)
            new_accumulator = min(1.0, self.state["slow_inhibition_accumulator"] + inhibition_increment)
        else:
            # Decay of slow inhibition
            new_accumulator = self.state["slow_inhibition_accumulator"] * (1.0 - self.SLOW_DECAY_RATE)

        self.state["slow_inhibition_accumulator"] = max(0.0, min(1.0, new_accumulator))

        # Sustained suppression: increases in "sustained" behavioral states
        if behavioral_state == "sustained":
            sustained_delta = 0.03 * LTS_activity
            self.state["sustained_suppression"] = min(
                1.0, self.state["sustained_suppression"] + sustained_delta
            )
        else:
            self.state["sustained_suppression"] *= 0.98

        # Combined slow inhibition strength
        slow_inhibition_strength = (
            self.state["slow_inhibition_accumulator"] * 0.7
            + self.state["sustained_suppression"] * 0.3
        )

        self.state["LTS_activity"] = LTS_activity
        self.state["slow_inhibition_strength"] = slow_inhibition_strength
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "LTS_activity": round(LTS_activity, 4),
            "network_integration_signal": round(new_integration, 4),
            "slow_inhibition_strength": round(slow_inhibition_strength, 4),
            "theta_phase_degrees": round(new_theta_phase, 2),
            "sustained_suppression": round(self.state["sustained_suppression"], 4),
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

