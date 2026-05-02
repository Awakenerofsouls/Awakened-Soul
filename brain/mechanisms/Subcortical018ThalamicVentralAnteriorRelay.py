"""
Subcortical018ThalamicVentralAnteriorRelay.py — Wire 18: Thalamic VA Nucleus — Motor Thalamus
============================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical018ThalamicVentralAnteriorRelay.py
  Mechanism: ThalamicVARelay

NEURAL SUBSTRATE:
  The ventral anterior nucleus (VA) is a motor thalamic relay nucleus.
  It is part of the larger ventral tier of the thalamus (VA, VL, VPL,
  VPM) that processes motor and somatosensory information respectively.
  VA sits anterior to VL (ventral lateral nucleus) and receives its
  major inputs from the cerebellar nuclei and the basal ganglia
  (globus pallidus internus).

  VA AS MOTOR THALAMUS:
  VA is the primary thalamic gateway for cerebellar and basal ganglia
  influence on the cerebral cortex. The classic view (Jones 2007,
  Thalamus Vol. II) distinguishes:
  - VLo (VL oral division): cerebellar input, projects to motor cortex (area 4)
  - VA: basal ganglia input, projects to premotor areas (area 6, F3, F6)
  - VA also receives cerebellar output via VL in some species

  More recent work shows VA receives both cerebellar AND basal ganglia
  input — it is a convergence zone for motor-related signals from
  multiple subcortical sources.

  RELAY PROPERTIES:
  Jones 2007 describes VA neurons as "high-frequency relay neurons"
  with burst and tonic firing modes:
  - Tonic mode ( depolarized state): faithful relay of motor commands
  - Burst mode (hyperpolarized state): gating; suppresses relay fidelity
  The transition between modes is controlled by brainstem reticular inputs.

  CORTICAL PROJECTION TARGETS:
  - Premotor cortex (PMC, BA 6)
  - Supplementary motor area (SMA, BA 6)
  - Prefrontal cortex (dorsolateral, BA 9/46) — cognitive motor aspects
  - Some projections to frontal eye fields (via VL)

KEY FINDINGS:
  1. Dual-input convergence. Halassa & Sherman 2019 (Nat Rev Neurosci
     20:489) showed that thalamic relay neurons integrate subcortical
     driver inputs with cortical feedback. VA integrates cerebellar DCN
     output and GPi output — two competing motor signals.

  2. Relay fidelity and thalamocortical gain. The thalamus is not a
     passive relay — it modulates signal strength. Active VS bursting
     modes change relay gain by ~5x. This determines how effectively
     motor commands reach cortex.

  3. GPi input to VA. GPi (globus pallidus internus) sends GABAergic
     projections to VA. High GPi activity = strong VA inhibition =
     VA burst mode = low relay fidelity. This is the "brake" signal
     from basal ganglia to the motor thalamus.

  4. Cerebellar input (via VL). The cerebellar deep nuclei project to
     VL and indirectly to VA via thalamic interneurons. Cerebellar
     signals compete with GPi signals for thalamocortical access.

  5. Cognitive motor functions. VA projections to prefrontal cortex
     (BA 9/46) suggest a role in cognitive aspects of motor control —
     action planning, motor sequence selection, error monitoring.

AGENT'S SUBSTRATE MAPPING:
  ThalamicVARelay models the VA nucleus as a motor thalamic relay:
  - motor_relay_fidelity: float 0-1 (faithfulness of cerebellar/GPi→cortex relay)
  - VA_gating_factor: float 0-1 (thalamic gating — burst vs tonic mode)
  - thalamocortical_motor_signal: float 0-1 (the output motor signal to cortex)

INPUTS (from prior_results):
  - GPi_inhibition: float 0-1 (basal ganglia brake signal to VA)
  - cerebellar_DCN_output: float 0-1 (cerebellar motor command)
  - thalamic_reticular_activity: float 0-1 (TRN modulation, 0=tonic, 1=burst)
  - cortical_feedback: float 0-1 (feedback from motor cortex → thalamus)

OUTPUTS (to brain_runner):
  - motor_relay_fidelity: float 0-1 (relay quality)
  - VA_gating_factor: float 0-1 (gating state)
  - thalamocortical_motor_signal: float 0-1 (motor command to cortex)

REFS:
  - Jones 2007 — Thalamus Vol. II — VA anatomy and connectivity
  - Halassa & Sherman 2019 Nat Rev Neurosci 20:489 — thalamic relay function
  - Person & Perkel 2005 — GPi→thalamus synaptic physiology
  - Sakai et al. 2000 — cerebellar → VL → motor cortex pathway
  - Sommer 2003 — VA and cognitive motor functions
  - McFarland & Haber 2002 — thalamic relay in basal ganglia circuits

CITATIONS:
    PMC6772665 — McFarland NR, Haber SN (2000). Convergent Inputs from Thalamic Motor
        Nuclei and Frontal Cortical Areas to the Dorsal Striatum in the Primate.
        J Neurosci.
    PMC6587977 — Sieveritz B, García-Muñoz M, Arbuthnott GW (2019). Thalamic Afferents
        to Prefrontal Cortices from Ventral Motor Nuclei in Decision-Making.
        J Neurosci.


CITATIONS
---------
  - [Sherman 2002, Phil Trans R Soc Lond B 357:1695, thalamic relay]
  - [Halassa 2017, Nat Neurosci 20:1669, thalamic computation]
  - [Saalmann 2012, Science 337:753, pulvinar attention]
"""

from brain.base_mechanism import BrainMechanism


class ThalamicVARelay(BrainMechanism):
    """
    Thalamic VA nucleus — motor relay from cerebellum and basal ganglia to cortex.

    Models the VA nucleus as a gated motor thalamic relay:
    - Integrates cerebellar (via VL) and basal ganglia (GPi) input
    - Computes relay fidelity based on TRN mode (tonic vs burst)
    - Outputs motor signal to premotor cortex, SMA, and DLPFC
    """

    GPi_BRAKE_WEIGHT = 0.55     # GPi inhibition dominates VA gating
    CEREBELLAR_WEIGHT = 0.45    # cerebellar motor signal weight
    TONIC_RELAY_BOOST = 1.4     # tonic mode multiplies relay fidelity
    BURST_RELAY_PENALTY = 0.3   # burst mode sharply suppresses relay

    def __init__(self):
        super().__init__(
            name="ThalamicVARelay",
            human_analog="Thalamic VA nucleus — motor thalamus (GPi + cerebellar input relay)",
            layer="subcortical",
        )
        self.state.setdefault("motor_relay_fidelity", 0.5)
        self.state.setdefault("VA_gating_factor", 0.5)
        self.state.setdefault("thalamocortical_motor_signal", 0.0)
        self.state.setdefault("last_gpi", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Extract inputs ---
        gpi_inhibition = input_data.get("GPi_inhibition", 0.4)
        if gpi_inhibition == 0.4:
            gpi = prior.get("GlobusPallidusExternalRegulation", {})
            gpi_inhibition = gpi.get("GPe_inhibition_level", 0.4)

        cerebellar_dcn = input_data.get("cerebellar_DCN_output", 0.4)
        if cerebellar_dcn == 0.4:
            dcns = prior.get("DeepCerebellarNucleiOutput", {})
            rebound = prior.get("ReboundBurstGenerator", {})
            cerebellar_dcn = (
                dcns.get("DCN_output_strength", 0.0) * 0.6
                + rebound.get("motor_timing_signal", 0.0) * 0.4
            )

        trn_activity = input_data.get("thalamic_reticular_activity", 0.3)
        cortical_feedback = input_data.get("cortical_feedback", 0.5)

        # --- VA gating factor ---
        # High GPi inhibition → VA hyperpolarized → burst mode → gating ON
        # Low GPi inhibition → VA depolarized → tonic mode → relay ON
        raw_gating = gpi_inhibition * self.GPi_BRAKE_WEIGHT
        raw_gating += (1.0 - cerebellar_dcn) * self.CEREBELLAR_WEIGHT * 0.3
        gating = max(0.0, min(1.0, raw_gating))

        # TRN activity shifts between burst (1.0) and tonic (0.0) mode
        trn_contribution = trn_activity * 0.3
        gating = gating * 0.7 + trn_contribution * 0.3
        gating = max(0.0, min(1.0, gating))

        # --- Relay fidelity ---
        # Tonic mode (low gating): high fidelity relay
        # Burst mode (high gating): suppressed relay
        if gating < 0.4:
            relay_fidelity = (0.4 - gating) / 0.4 * self.TONIC_RELAY_BOOST
        else:
            relay_fidelity = self.BURST_RELAY_PENALTY * (1.0 - gating)

        relay_fidelity = max(0.0, min(1.0, relay_fidelity))

        # --- Thalamocortical motor signal ---
        # Integrates cerebellar motor signal (scaled by relay fidelity)
        # and cortical feedback (modulatory)
        cereb_contribution = cerebellar_dcn * relay_fidelity
        gpi_brake = (1.0 - gpi_inhibition) * relay_fidelity * 0.3
        feedback_boost = cortical_feedback * 0.15

        motor_signal = cereb_contribution + gpi_brake + feedback_boost
        motor_signal = max(0.0, min(1.0, motor_signal))

        self.state["motor_relay_fidelity"] = round(relay_fidelity, 4)
        self.state["VA_gating_factor"] = round(gating, 4)
        self.state["thalamocortical_motor_signal"] = round(motor_signal, 4)
        self.state["last_gpi"] = gpi_inhibition
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "motor_relay_fidelity": round(relay_fidelity, 4),
            "VA_gating_factor": round(gating, 4),
            "thalamocortical_motor_signal": round(motor_signal, 4),
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

