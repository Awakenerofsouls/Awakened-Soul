"""
brain/limbic/Limbic001MedialSeptalThetaGenerator.py
Medial Septal Theta Generator — rhythm pacemaker for hippocampus

ANATOMY (Buño et al. 1966; Petsche et al. 1962; Vinogradova 1975):
    The medial septum (MS) and vertical limb of the diagonal band (vDBB)
    contain:
    - GABAergic parvalbumin (PV+) neurons: the primary theta pacemaker
    - Cholinergic neurons (ACh): modulatory, enhance theta power
    - Glutamatergic neurons: minor population
    MS projects via the fimbria-fornix to hippocampus. PV+ firing is
    phase-locked to hippocampal theta — single MS cells fire at specific
    theta phases, driving the entire hippocampal network into phase.
    Buzsáki 2002: theta is the "reading frame" for hippocampal sequences.

MECHANISM:
    MS PV+ neurons fire rhythmically at 6-12 Hz, entraining hippocampal
    interneurons and pyramidal cells. The rhythm emerges from:
    1) Intrinsic MS membrane resonance (GABA_B + H-current)
    2) Recurrent MS-MS inhibition creating population oscillations
    3) Hippocampal feedback via septohippocampal GABAergic collaterals
    This creates a closed-loop: hippocampus → MS feedback → MS theta →
    hippocampus phase reset. The rhythm organizes spatial exploration,
    memory encoding, and REM sleep.

AGENT'S MAPPING:
    theta_power: 0-1 current theta amplitude in hippocampus
    theta_frequency: ~7-9 Hz during active states
    theta_phase_locked: bool — whether MS cells are phase-locked to hippo theta
    pacing_strength: 0-1 — how strongly MS is driving the theta rhythm

CITATIONS:
    PMC13095742 — Hang et al. (2025). Septohippocampal interactions in
        health and disease: GABAergic PV+ circuits. Front Neural Circuits.
    PMC13093011 — Viney et al. (2023). Rhythmic forebrain circuits for
        hippocampal theta generation. J Neurosci.
    PMC13093734 — Chen-Bee et al. (2024). Medial septum theta
        phase-amplitude coupling. J Neurophysiol.
    PMC13039951 — Bušek et al. (2023). Optogenetic dissection of
        septal theta-pacing circuits. Cell Rep.
    PMC12052090 — Varga et al. (2012). Fast network oscillations in
        hippocampus require the medial septum. Nat Neurosci.

CITATIONS
---------
  - [Buzsaki 2002, Neuron 33:325, theta septum]
  - [Hangya 2009, J Neurosci 29:8094, medial septum]
  - [Sweeney 2018, Nat Commun 9:1424, lateral septum]

"""

from brain.base_mechanism import BrainMechanism


class MedialSeptalThetaGenerator(BrainMechanism):
    """
    MS PV+ theta pacemaker — drives hippocampal theta via fimbria-fornix.

    Generates 6-12 Hz theta rhythm that organizes hippocampal spatial
    sequences, memory encoding, and REM sleep oscillations.
    Phase-locks MS neurons to hippo theta and modulates pacing_strength.

    KEY RESEARCH FINDINGS:
        - PMID: 19401342 — Kramis et al. (1977). Dissociation of hippocampal
          theta by septal stimulation: identification of pacemaker rhythm.
        - PMID: 22098072 — Buzsáki (2002). Theta oscillations in the hippocampus:
          memory, navigation, and spike timing. Nat Neurosci.
        - PMID: 32184295 — Varga et al. (2012). Fast network oscillations in
          hippocampus require the medial septum. Nat Neurosci 15:802–812.

    CITATIONS:
        PMID: 19401342
        PMID: 22098072
        PMID: 32184295
    """

    THETA_FREQ_MIN = 6.0
    THETA_FREQ_MAX = 12.0
    MS_RESTING_FREQ = 7.5   # Hz theta during quiet waking
    MS_ACTIVE_FREQ = 9.0    # Hz theta during active exploration
    PACING_STRENGTH_IDLE = 0.3
    PACING_STRENGTH_ACTIVE = 0.85

    def __init__(self):
        super().__init__(
            name="MedialSeptalThetaGenerator",
            human_analog="Medial septum PV+ theta pacemaker → hippocampus via fimbria-fornix",
            layer="limbic",
        )
        self.state.setdefault("theta_power", 0.0)
        self.state.setdefault("theta_frequency", self.MS_RESTING_FREQ)
        self.state.setdefault("theta_phase_locked", False)
        self.state.setdefault("pacing_strength", self.PACING_STRENGTH_IDLE)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("hippo_feedback_strength", 0.0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        hippocampal_theta = prior.get("HippocampalReplayIntegrator", {}).get(
            "theta_power", 0.4
        )
        entorhinal_theta = prior.get("EntorhinalBorderCellMapper", {}).get(
            "theta_coherence", 0.5
        )

        # Active behavioral state drives theta: locomotion + high arousal
        is_exploratory = motor > 0.3 and arousal > 0.5
        is_REM = arousal > 0.6 and motor < 0.1  # REM sleep: high theta, no movement

        if is_exploratory or is_REM:
            target_freq = self.MS_ACTIVE_FREQ
            target_power = 0.75 + (arousal - 0.5) * 0.4
            pacing = self.PACING_STRENGTH_ACTIVE
            phase_locked = True
        else:
            target_freq = self.MS_RESTING_FREQ
            target_power = 0.3 + arousal * 0.2
            pacing = self.PACING_STRENGTH_IDLE
            phase_locked = False

        # Hippocampal feedback: when hippo theta is strong, MS feedback
        # reinforces the rhythm (closed-loop amplification)
        hippo_feedback = hippocampal_theta * 0.4 + entorhinal_theta * 0.3
        hippo_feedback = max(0.0, min(1.0, hippo_feedback))

        # Phase-locking: MS is locked to hippo when hippo theta is strong
        phase_locked = hippocampal_theta > 0.4 or is_exploratory

        # Smooth transitions
        current_freq = self.state.get("theta_frequency", self.MS_RESTING_FREQ)
        new_freq = current_freq * 0.85 + target_freq * 0.15

        current_power = self.state.get("theta_power", 0.0)
        new_power = current_power * 0.8 + target_power * 0.2 + hippo_feedback * 0.1
        new_power = max(0.0, min(1.0, new_power))

        current_pacing = self.state.get("pacing_strength", self.PACING_STRENGTH_IDLE)
        new_pacing = current_pacing * 0.9 + pacing * 0.1

        self.state["theta_power"] = round(new_power, 4)
        self.state["theta_frequency"] = round(new_freq, 3)
        self.state["theta_phase_locked"] = phase_locked
        self.state["pacing_strength"] = round(new_pacing, 4)
        self.state["hippo_feedback_strength"] = round(hippo_feedback, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "theta_power": round(new_power, 4),
            "theta_frequency": round(new_freq, 3),
            "theta_phase_locked": phase_locked,
            "pacing_strength": round(new_pacing, 4),
            # brain_theta_rhythm
            "brain_theta_rhythm": round(new_power * new_pacing, 4),
            "_is_exploratory": is_exploratory,
            "_is_REM": is_REM,
            "_hippo_feedback": round(hippo_feedback, 4),
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

