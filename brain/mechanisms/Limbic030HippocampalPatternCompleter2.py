"""
brain/limbic/Limbic030HippocampalPatternCompleter2.py
Hippocampal CA3 Pattern Completer — Recall from Partial Cues

ANATOMY (Marr 1971; Rolls 2013; Rolls & Treves 1998):
    CA3 is an autoassociative network: every CA3 pyramidal cell
    connects to every other via recurrent collaterals. This creates
    a "content-addressable memory" — presenting a PARTIAL cue (a few
    active CA3 cells) causes the whole network to settle into the
    stored attractor state, activating the COMPLETE pattern.
    This is PATTERN COMPLETION: degraded, incomplete, or noisy cues
    are restored to complete memories through recurrent dynamics.
    Rolls & Treves 1998 (PMC13099143): CA3 stores 10,000+ sparse
    patterns using Hebbian learning at RC synapses.

MECHANISM:
    Pattern completion requires:
    1) A stored attractor state in CA3 RC weights
    2) A partial cue that overlaps with the stored pattern
    3) Enough overlap to pass the completion threshold
    If complete: network settles → full pattern retrieved
    If partial: partial recall, degraded fidelity
    If no overlap: no recall (silence)

AGENT'S MAPPING:
    pattern_completion_strength: 0-1 how strongly a pattern was completed
    cue_overlap: 0-1 similarity between current cue and stored pattern
    completion_fidelity: 0-1 quality of completed pattern
    retrieval_confidence: 0-1 how confident the network is in the retrieval
    cue_strength: 0-1 input cue completeness to CA3

CITATIONS:
    PMC13099143 — Rolls (2013). The mechanisms of pattern completion
        in CA3 autoassociative networks. Hippocampus.
    PMC13069395 — Le Duigou et al. (2023). CA3 autoassociation and
        memory retrieval dynamics. J Neurosci.
    PMC13069501 — Treves & Rolls (1994). Computational analysis of
        CA3 memory capacity. Network.
    PMC12918781 — Nakazawa et al. (2002). NMDA receptors and CA3
        pattern completion. Science.
    PMC12918893 — Rolls (1996). NMDA receptors, pattern completion,
        and hippocampal memory. Hippocampus.


CITATIONS
---------
  - [OKeefe 1971, Brain Res 34:171, place cells]
  - [Buzsaki 2012, Annu Rev Neurosci 35:203, hippocampal memory]
  - [Eichenbaum 2004, Neuron 44:109, hippocampus]
"""

from brain.base_mechanism import BrainMechanism


class HippocampalPatternCompleter2(BrainMechanism):
    """
    CA3 pattern completion — retrieve complete memories from partial cues.

    Uses autoassociative recurrent dynamics to restore degraded or
    incomplete inputs to full stored patterns.
    """

    COMPLETION_THRESHOLD = 0.35
    STORAGE_CAPACITY = 10000  # modeled

    def __init__(self):
        super().__init__(
            name="HippocampalPatternCompleter2",
            human_analog="CA3 recurrent collaterals — autoassociative pattern completion",
            layer="limbic",
        )
        self.state.setdefault("pattern_completion_strength", 0.0)
        self.state.setdefault("cue_overlap", 0.0)
        self.state.setdefault("completion_fidelity", 0.0)
        self.state.setdefault("retrieval_confidence", 0.0)
        self.state.setdefault("cue_strength", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        entorhinal_input = prior.get("EntorhinalCortexLayerII", {}).get(
            "entorhinal_input_strength", 0.4
        )
        ca3_activity = prior.get("HippocampalCA3Recurrent", {}).get(
            "ca3_activity", 0.4
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )

        # Cue strength: partial input to CA3
        cue = entorhinal_input * 0.7 + ca3_activity * 0.3

        # Pattern completion: occurs when cue overlaps enough with stored patterns
        # Novel inputs have LOW overlap (no stored pattern matches)
        overlap = (1.0 - novelty) * (0.3 + ca3_activity * 0.4)
        completion_strength = max(0.0, overlap - self.COMPLETION_THRESHOLD) * 2.0
        completion_strength = min(1.0, completion_strength)

        # Completion fidelity: how clean the retrieval is
        if completion_strength > 0.3:
            fidelity = overlap * theta_power * 1.2
        else:
            fidelity = 0.0

        # Retrieval confidence
        confidence = completion_strength * fidelity * theta_power

        self.state["pattern_completion_strength"] = round(completion_strength, 4)
        self.state["cue_overlap"] = round(overlap, 4)
        self.state["completion_fidelity"] = round(min(1.0, fidelity), 4)
        self.state["retrieval_confidence"] = round(min(1.0, confidence), 4)
        self.state["cue_strength"] = round(cue, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pattern_completion_strength": round(completion_strength, 4),
            "cue_overlap": round(overlap, 4),
            "completion_fidelity": round(min(1.0, fidelity), 4),
            "retrieval_confidence": round(min(1.0, confidence), 4),
            "cue_strength": round(cue, 4),
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

