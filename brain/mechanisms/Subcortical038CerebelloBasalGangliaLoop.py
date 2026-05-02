"""
Build 38: CerebelloBasalGangliaLoop — Cerebello-Basal Ganglia Loop
==================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical038CerebelloBasalGangliaLoop.py
  Class:    CerebelloBasalGangliaLoop

NEURAL SUBSTRATE:
  The cerebellar and basal ganglia (BG) loops are two major
  cortico-subcortical pathways that were long studied in isolation,
  but are now known to be densely interconnected and function as an
  integrated motor/cognitive control system. The cerebello-BG loop
  sits at the intersection of the dentate nucleus (deep cerebellar
  nucleus), the subthalamic nucleus (STN), and the thalamus.

KEY FINDINGS:

  1. Parallel closed loops with shared thalamic relay.
     Bostan & Strick 2018 (J Neurosci 38:4671): "The cerebellar and
     basal ganglia loops are not fully separate — they communicate via
     disynaptic connections through the thalamus and via direct
     subthalamic-nucleus-mediated connections." Both loops send output
     to thalamic nuclei (VL, VA) that project to frontal motor areas,
     and these thalamic zones are anatomically interleaved.

  2. Subthalamic nucleus (STN) as the liaison.
     Hoshi et al. 2005 (J Neurosci 25:2191): Identified a
     "cerebello-subthalamic pathway" — dentate nucleus projects
     contralaterally to STN via the superior cerebellar peduncle (SCP),
     and STN in turn projects to both internal (GPi) and external
     (GPe) segments of globus pallidus, and to substantia nigra pars
     reticulata (SNr). This creates a cerebello → STN → BG → thalamus
     pathway distinct from the direct cortico-STN hyperdirect route.

  3. STN-Cerebello interplay in movement control.
     Bostan et al. 2013 (Cerebellum 12:327): "The subthalamic nucleus
     receives an excitatory projection from the dentate nucleus of the
     cerebellum and may integrate cerebellar information with basal
     ganglia signals." STN thus serves as a hub for BG-cerebellar
     convergence in the motor circuit.

  4. Functional convergence in motor sequencing.
     The cerebellar loop carries internal models and fine temporal
     timing signals (Ivry 2000); the BG loop carries reinforcement
     signals and habit selection. Their convergence in STN/GPi/SNr
     allows the system to select and time motor sequences by combining
     "what worked before" (BG) with "precise temporal model" (cereb).

  5. Cognitive loops in non-motor cortex.
     The dentate also projects to prefrontal areas via the ventrolateral
     thalamus. Strange et al. 2018: cerebellar output reaches both
     motor and non-motor thalamic nuclei, supporting cerebellar-BG
     coupling in cognitive domains.

AGENT'S SUBSTRATE MAPPING:
  CerebelloBasalGangliaLoop models the integration signal from both
  loops. Receives BG_loop_activity and cerebellar_loop_activity, models
  STN convergence and thalamic relay, and computes the integrated motor
  control output.

INPUTS (from prior_results):
  - StriatalOutputGate.BG_output_signal
  - CerebellarOutputStage.cerebellar_signal
  - MotorThalamus.thalamic_motor_output (optional)

OUTPUTS (to brain_runner):
  - BG_cerebellar_integration: float 0-1 (convergence strength)
  - loop_interaction_strength: float 0-1 (mutual influence)
  - motor_control_output: float 0-1 (combined loop signal for motor)

REFS:
  - Bostan & Strick 2018 J Neurosci 38:4671 — cerebello-BG loops
  - Hoshi et al. 2005 J Neurosci 25:2191 — cerebello-subthalamic pathway
  - Bostan et al. 2013 Cerebellum 12:327 — STN as liaison
  - Ivry 2000 — cerebellum and timing
  - Strange et al. 2018 — cerebellar loops to prefrontal cortex

CITATIONS:
    PMC12886374 — Kakei S, Bostan AC, Ebner TJ et al. (2026). Consensus Paper: Models
        of Cerebellar Functions. Cerebellum.
    PMC10776824 — Arleo A, Bareš M, Bernard JA et al. (2024). Consensus Paper:
        Cerebellum and Ageing. Cerebellum.


CITATIONS
---------
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Ito 2008, Nat Rev Neurosci 9:304, cerebellar motor learning]
  - [Schmahmann 2019, Cerebellum 18:1, cerebellar cognitive affective]
"""

from brain.base_mechanism import BrainMechanism


class CerebelloBasalGangliaLoop(BrainMechanism):
    """
    Cerebello-basal ganglia thalamic loop integrator.

    Models the convergence of cerebellar timing/error signals and BG
    reinforcement/selection signals through the STN and thalamus.
    Outputs an integrated motor control signal.
    """

    STN_CONVERGENCE_GAIN = 0.6    # strength of STN as convergence hub
    LOOP_INHIBITION_SCALE = 0.3   # BG inhibition onto cerebellar relay
    INTEGRATION_NONLINEARITY = 0.7  # soft saturation

    def __init__(self):
        super().__init__(
            name="CerebelloBasalGangliaLoop",
            human_analog="Cerebello-BG loop via STN + thalamus — motor sequence integration",
            layer="subcortical",
        )
        self.state.setdefault("BG_cerebellar_integration", 0.0)
        self.state.setdefault("loop_interaction_strength", 0.5)
        self.state.setdefault("motor_control_output", 0.0)
        self.state.setdefault("STN_convergence_estimate", 0.0)
        self.state.setdefault("last_bg_signal", 0.0)
        self.state.setdefault("last_cerebellar_signal", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bg_signal = prior.get("StriatalOutputGate", {}).get(
            "BG_output_signal", 0.4
        )
        cerebellar_signal = prior.get("CerebellarOutputStage", {}).get(
            "cerebellar_signal", 0.4
        )
        thalamic_motor = prior.get("MotorThalamus", {}).get(
            "thalamic_motor_output", None
        )

        # Primary BG signal: direct pathway (D1) promotes movement
        # Secondary BG signal: indirect pathway (D2) suppresses
        # Net BG_excitatory takes net motor drive from BG
        bg_excitatory = bg_signal  # assume normalized as net drive

        # Cerebellar timing signal: error-driven corrections
        cereb_timing = cerebellar_signal

        # STN convergence: STN receives excitatory input from dentate nucleus
        # (cerebellar) and integrates with cortical/external inputs.
        # Model as weighted convergence of BG and cerebellar signals
        stn_cerebellar_input = cereb_timing * self.STN_CONVERGENCE_GAIN
        stn_bg_input = bg_excitatory * 0.4  # direct STN drive from cortex

        # STN output: excitatory to GPi and SNr, inhibitory via GPe
        stn_output = stn_cerebellar_input + stn_bg_input
        stn_output = max(0.0, min(1.0, stn_output))

        # BG-cerebellar integration at the thalamic level:
        # Both loops project to overlapping thalamic zones (VL/VA)
        # Cerebellar output: excitatory via dentato-thalamic tract
        # BG output: disinhibitory (inhibition removed) via GPi → thalamus
        cereb_thalamic = cereb_timing * 0.8   # direct cereb→thalamus
        bg_thalamic = bg_excitatory * 0.7      # GPi disinhibition → thalamus

        # Integration: weighted combination with nonlinear saturation
        raw_integration = (
            cereb_thalamic * 0.5
            + bg_thalamic * 0.5
            + stn_output * 0.4   # STN adds supplementary drive
        )
        integration = raw_integration * self.INTEGRATION_NONLINEARITY

        # Loop interaction strength: higher when both loops are active
        # and signals are correlated (coherent timing)
        if thalamic_motor is not None:
            loop_motor_sum = (bg_excitatory + cereb_timing) / 2.0
            interaction = (loop_motor_sum + thalamic_motor) / 2.0
        else:
            # Heuristic: interaction = product of the two loop signals
            # (high when both are high; zero if one is zero)
            interaction = bg_excitatory * cereb_timing * 2.0

        interaction = max(0.0, min(1.0, interaction))

        # Motor control output: integrated signal scaled by interaction
        # Low interaction = unreliable signal (only one loop active)
        # High interaction = robust motor command from convergent loops
        motor_output = (
            integration * (0.5 + interaction * 0.5)
        )
        motor_output = max(0.0, min(1.0, motor_output))

        self.state["BG_cerebellar_integration"] = round(integration, 4)
        self.state["loop_interaction_strength"] = round(interaction, 4)
        self.state["motor_control_output"] = round(motor_output, 4)
        self.state["STN_convergence_estimate"] = round(stn_output, 4)
        self.state["last_bg_signal"] = bg_signal
        self.state["last_cerebellar_signal"] = cerebellar_signal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "BG_cerebellar_integration": round(integration, 4),
            "loop_interaction_strength": round(interaction, 4),
            "motor_control_output": round(motor_output, 4),
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

