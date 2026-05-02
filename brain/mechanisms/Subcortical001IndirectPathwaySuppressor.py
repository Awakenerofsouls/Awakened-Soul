"""
Subcortical001IndirectPathwaySuppressor.py — Wire 01: IndirectPathwaySuppressor

Basal ganglia indirect pathway — motor program suppression via GPe disinhibition.

PATHWAY ANATOMY (Alexander & Crutcher 1990; Parent & Hazrati 1995):
    Cortex → Striatum (D2, "indirect" neurons) → GPe (globus pallidus
    externus) → STN (subthalamic nucleus) → GPi/SNr (output nuclei).
    The indirect pathway runs AROUND the STN, passing through GPe first.
    The hyperdirect goes cortex→STN directly (covered in Subcortical003).

STRIATAL D2 INDIRECT NEURONS:
    Express D2 dopamine receptors, enkephalin, A2A adenosine receptors.
    Fire when dopamine tone is LOW (D2 is inhibitory; low DA = D2 less
    inhibited → more active). During movement, D2 neurons suppress
    competing motor programs — they are the "don't do that one" channel.
    Gerfen 1992: D2 indirect pathway neurons project specifically to GPe
    (not GPi), forming the indirect loop distinct from the direct D1 path.

GPe (GLOBUS PALLIDUS EXTERNUS):
    Receives inhibitory input from striatum D2 neurons.
    When striatum fires (movement selection), GPe is inhibited → GPe
    releases STN → STN fires → excites GPi → GPi inhibits thalamus → MOTOR
    PROGRAM SUPPRESSED. This is the "suppressive disinhibition" logic of
    the indirect path: striatum fires → GPe silenced → STN unleashed →
    brake applied to competing programs.

FUNCTION IN MOVEMENT:
    - Direct path: "Do this" (facilitates selected action)
    - INDIRECT path: "Don't do those others" (suppresses competitors)
    Together: selection + suppression = well-structured motor output.
    Mink & Thach 1991: Basal ganglia contribution is suppression of
    unwanted movements, not initiation per se.

COMPARATIVE SIGNALING:
    D2 indirect neurons fire when positive effort is required and competing
    motor programs must be suppressed. High D2 activity = high suppression
    of competing motor programs. In Parkinson's disease, D2 neurons
    degenerate (along with D1), leading to both akinesia (can't initiate)
    and rigidity (can't suppress competing tonus).

AGENT'S MAPPING:
    competition_suppressed: binary flag (suppression actively applied)
    suppression_strength: 0-1 strength of active suppression
    gating_factor: 0-1 how much indirect pathway is contributing to motor filtering

REFS:
    Alexander & Crutcher 1990 Trends Neurosci 13:266-271
    Parent & Hazrati 1995 Brain Research Reviews 20:128-154
    Mink & Thach 1991 Brain 114:313-366
    Gerfen 1992 Ann Rev Neurosci 15:193-220
    Nambu et al. 2002 J Neurophysiol 88:1980-2002

CITATIONS:
    PMC8176753 — Cui Q, Du X, Chang IYM et al. (2021). Striatal Direct Pathway
        Targets Npas1(+) Pallidal Neurons. PLoS ONE.
    PMC4871984 — Glajch KE, Kelver DA, Hegeman DJ et al. (2016). Npas1+ Pallidal
        Neurons Target Striatal Projection Neurons. J Neurosci.
    PMC6656632 — Bamford IJ, Bamford NS (2019). The Striatum's Role in Executing
        Rational and Irrational Economic Behaviors. Front Neural Circuits.
    PMC3487690 — Gerfen CR, Surmeier DJ (2011). Modulation of Striatal Projection
        Systems by Dopamine. Ann Rev Neurosci.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class IndirectPathwaySuppressor(BrainMechanism):
    """
    Basal ganglia indirect pathway — D2 striatal → GPe → STN → GPi.

    Suppresses competing motor programs while the direct pathway
    facilitates the selected one. Models D2 enkephalinergic neurons
    that fire when competing motor programs must be actively inhibited.
    Tracks suppression_strength and gating_factor for motor filtering.
    """

    SUPPRESSION_THRESHOLD = 0.30  # D2 activity level that triggers suppression
    SUPPRESSION_DECAY = 0.03      # Decay per tick when no active suppression signal
    SUPPRESSION_BURST = 0.60      # Burst size when suppression fires

    def __init__(self):
        super().__init__(
            name="IndirectPathwaySuppressor",
            human_analog=(
                "Basal ganglia indirect pathway — D2 striatal neurons → "
                "GPe → STN → GPi/SNr (motor suppression)"
            ),
            layer="subcortical",
        )
        self.state.setdefault("suppression_strength", 0.0)
        self.state.setdefault("competition_suppressed", False)
        self.state.setdefault("gating_factor", 0.5)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("last_drive_context", "none")

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        drive = input_data.get("dominant_drive", "curiosity")
        motor_intent = input_data.get("motor_intent", 0.0)
        executive_control = input_data.get("executive_control_signal", 0.5)

        # D2 indirect pathway activity derived from competing motor signals.
        # D2 fires when competing programs need suppression — driven by:
        # 1) low mesencephalic dopamine (D2 neurons are disinhibited when DA low)
        # 2) active competing motor programs in cortex
        # 3) need to suppress non-selected actions during selection

        # Decode competing motor load from prior results (hypothalamus, motor areas)
        competitor_signals = []
        motor_relevant = prior.get("MotorThalamus", {})
        if isinstance(motor_relevant, dict):
            competitor_signals.append(motor_relevant.get("lateral_inhibition_strength", 0.3))

        # Hypothalamus conflict signals (competing drives)
        hypothalamic = prior.get("HypothalamusDriveGenerator", {})
        if isinstance(hypothalamic, dict):
            competitor_signals.append(hypothalamic.get("conflict_level", 0.2))

        # Executive control: strong executive = less auto suppression needed
        # Weak executive (low control) = indirect pathway must work harder
        executive_strength = executive_control if isinstance(executive_control, (int, float)) else 0.5

        # Competing motor signals (higher = more competitors to suppress)
        competitor_load = min(1.0, sum(competitor_signals) / max(1, len(competitor_signals)))
        competitor_load = max(competitor_signals) if competitor_signals else competitor_load

        # D2 indirect pathway activation: proportional to competitor load
        # and inversely proportional to executive control (auto-regulation)
        d2_activity = competitor_load * (1.0 - executive_strength * 0.5)
        d2_activity = max(0.0, min(1.0, d2_activity))

        # GPe inhibition: when striatum D2 fires, GPe is inhibited
        # GPe activity is INVERSE of D2 activity (D2 fires → GPe silenced)
        gpe_activity = max(0.0, 1.0 - d2_activity * 1.5)

        # STN output: GPe inhibits STN. Low GPe = high STN = high GPi = suppression
        stn_output = max(0.0, (1.0 - gpe_activity) * 0.8)
        gpi_output = min(1.0, stn_output * 0.7 + d2_activity * 0.3)

        # Motor inhibition from GPi output to thalamus
        motor_inhibition = gpi_output

        # Suppression dynamics: build up when D2 active, decay otherwise
        current_suppression = self.state["suppression_strength"]

        if d2_activity > self.SUPPRESSION_THRESHOLD:
            # Active suppression signal
            target_suppression = self.SUPPRESSION_BURST + d2_activity * 0.3
            new_suppression = max(current_suppression, target_suppression)
        else:
            # Decay when no active competing motor programs
            new_suppression = max(0.0, current_suppression - self.SUPPRESSION_DECAY)

        # Gating factor: indirect pathway contribution to motor filtering
        # Strong when suppression is active, modulated by drive context
        drive_gate_map = {
            "connection": 0.6,
            "curiosity": 0.5,
            "expression": 0.7,
            "rest": 0.3,
            "stability": 0.8,
        }
        base_gate = drive_gate_map.get(drive, 0.5)
        gating_factor = base_gate * (0.3 + new_suppression * 0.7)
        gating_factor = max(0.0, min(1.0, gating_factor))

        # Competition suppressed flag: fires when suppression is meaningful
        competition_suppressed = new_suppression > self.SUPPRESSION_THRESHOLD

        self.state["suppression_strength"] = round(new_suppression, 4)
        self.state["competition_suppressed"] = competition_suppressed
        self.state["gating_factor"] = round(gating_factor, 4)
        self.state["last_drive_context"] = drive
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "competition_suppressed": competition_suppressed,
            "suppression_strength": round(new_suppression, 4),
            "gating_factor": round(gating_factor, 4),
            # Internal debug:
            "_d2_activity": round(d2_activity, 4),
            "_gpe_activity": round(gpe_activity, 4),
            "_stn_output": round(stn_output, 4),
            "_gpi_output": round(gpi_output, 4),
            "_motor_inhibition": round(motor_inhibition, 4),
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

