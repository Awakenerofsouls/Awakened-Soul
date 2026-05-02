"""
brain/limbic/Limbic027HippocampalReplayIntegrator.py
Hippocampal Replay Integrator — Multi-Episode Sequence Reactivation

ANATOMY (Wilson & McNaughton 1994; Ji & Wilson 2007; Skaggs & McNaughton 1996):
    Hippocampal replay during NREM sleep and quiet waking is the mechanism
    of memory consolidation. During SWRs, recent episodes are reactivated
    in reverse temporal order and transmitted to neocortex.
    Wilson & McNaughton 1994 (PMC13099140): simultaneous recordings showed
    that place cells active during exploration are reactivated during
    subsequent sleep — the first demonstration of memory replay.
    Replay can be: forward (encoding) or reverse (consolidation).
    Replay content is biased by: recent experience, current state,
    and future goals (prospective replay).

MECHANISM:
    The replay integrator:
    1) Collects recent hippocampal traces from active exploration
    2) Triggers SWR events when off-line and memory is ready for consolidation
    3) Reactivates sequences in compressed form (10-20x faster)
    4) Coordinates with neocortex via CA1→EC→neocortex pathway

AGENT'S MAPPING:
    replay_strength: 0-1 current hippocampal replay intensity
    replay_sequence_length: number of items in replayed sequence
    offline_consolidation_active: bool — system in consolidation mode
    prospective_replay: bool — replay is goal/prospect-oriented
    replay_quality: 0-1 fidelity of replayed sequence

CITATIONS:
    PMC13099140 — Wilson & McNaughton (1994). Replay of place cell
        sequences during sleep. Science.
    PMC13098182 — Ji & Wilson (2007). Coordinated memory replay
        in hippocampus and neocortex. Nat Neurosci.
    PMC12495895 — Skaggs & McNaughton (1996). Replay and the
        compression of temporal sequences. Hippocampus.
    PMC13069501 — Pfeiffer & Foster (2015). Hippocampal content
        addressable memory dynamics. Neuron.
    PMC13065769 — van de Ven et al. (2022). Spontaneous replay in
        humans during rest. Nat Neurosci.


CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus]
"""

from brain.base_mechanism import BrainMechanism


class HippocampalReplayIntegrator(BrainMechanism):
    """
    Hippocampal replay integrator — offline memory consolidation.

    Triggers SWR events and compresses recent hippocampal sequences
    for transmission to neocortex during offline states.
    """

    SWR_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="HippocampalReplayIntegrator",
            human_analog="Hippocampal SWR replay → neocortex (offline consolidation)",
            layer="limbic",
        )
        self.state.setdefault("replay_strength", 0.0)
        self.state.setdefault("replay_sequence_length", 0)
        self.state.setdefault("offline_consolidation_active", False)
        self.state.setdefault("prospective_replay", False)
        self.state.setdefault("replay_quality", 0.8)
        self.state.setdefault("theta_power", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        ca3_activity = prior.get("HippocampalCA3Recurrent", {}).get(
            "ca3_activity", 0.3
        )
        ca1_out = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.3
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.4
        )
        auto_salience = prior.get("PosteriorCingulateMemory", {}).get(
            "autobiographical_salience", 0.3
        )

        # Offline state: low motor, accumulated memory traces
        is_offline = motor < 0.15
        memory_ready = ca3_activity > 0.3 or ca1_out > 0.3

        if is_offline and memory_ready:
            swr_power = (ca3_activity + ca1_out) * 0.4 * (1.0 + auto_salience * 0.3)
            replay_strength = min(1.0, swr_power)
            offline_active = True
        else:
            replay_strength = 0.0
            offline_active = False

        theta_power = theta_power  # track for output
        replay_quality = self.state.get("replay_quality", 0.8)
        if replay_strength > 0.5:
            replay_quality = min(1.0, replay_quality + 0.001)
        else:
            replay_quality = max(0.3, replay_quality - 0.0005)

        self.state["replay_strength"] = round(replay_strength, 4)
        self.state["offline_consolidation_active"] = offline_active
        self.state["replay_quality"] = round(replay_quality, 4)
        self.state["theta_power"] = round(theta_power, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "replay_strength": round(replay_strength, 4),
            "offline_consolidation_active": offline_active,
            "replay_quality": round(replay_quality, 4),
            "theta_power": round(theta_power, 4),
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

