"""
EntorhinalLayer5 — EC-V / Hippocampal Output Layer

NEURAL SUBSTRATE
================
Layer V of entorhinal cortex (EC-V) is the principal output layer,
receiving CA1 and subiculum projections and broadcasting hippocampal
output to widespread cortical targets (medial/orbitofrontal cortex,
cingulate, retrosplenial). EC-V pyramidal cells are large multipolar
neurons with long-range axons and serve as the gateway for
hippocampally-stored information back into the cortical mantle.

EC-V also provides feedback to EC-II/III via local circuit, completing
the entorhinal-hippocampal loop. Sürmeli 2015 demonstrated EC-V activity
is necessary for systems consolidation — selective EC-V silencing
abolishes hippocampal-dependent memory transfer to neocortex.

KEY FINDINGS
============
1. EC-V receives dense CA1 + subicular projections and broadcasts
   hippocampal output to widespread neocortex —
   [Insausti 1997, J Comp Neurol 386:495, PMID 9303432]
2. EC-V pyramidal silencing abolishes systems consolidation; necessary
   for memory transfer hippocampus→neocortex —
   [Surmeli 2015, Neuron 88:1040, doi:10.1016/j.neuron.2015.10.041]
3. EC-V supplies feedback to EC-II/III completing entorhinal loop;
   intra-entorhinal recurrent circuitry —
   [Kloosterman 2003, Eur J Neurosci 18:3037, PMID 14656298]
4. Deep EC-V neurons project preferentially to retrosplenial and
   prefrontal cortex; superficial EC-V to subiculum and CA1 —
   [Burwell 2000, Hippocampus 10:284, PMID 10902898]
5. EC-V-CA1 reciprocal loop encodes goal-directed prospective coding
   for navigation planning —
   [Ohara 2018, Cell Reports 24:107, doi:10.1016/j.celrep.2018.06.014]

INPUTS
======
- HippocampalCA1Dorsal.ca1d_drive (or HippocampalCA1.ca1_output)
- SubiculumDorsal.dsub_drive (or SubiculumVentral.vsub_drive)
- EntorhinalCortexGridCells.ec_output (recurrent intra-EC)
- MedialPrefrontalCortex.pfc_drive (top-down)

OUTPUTS
=======
- ec5_drive (0-1)
- cortical_output_signal (0-1) — to neocortex
- ec_loop_feedback (0-1) — back to EC-II/III
- consolidation_signal (0-1) — systems consolidation gate
- ec5_state (str): "broadcasting" | "looping" | "consolidating" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class EntorhinalLayer5(BrainMechanism):
    """EC-V — hippocampal output / cortical broadcast layer."""

    BASELINE = 0.10
    SMOOTH = 0.20
    BROADCAST_THRESHOLD = 0.45
    CONSOLIDATION_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="EntorhinalLayer5",
            human_analog="Entorhinal cortex layer V (output)",
            layer="limbic",
        )
        self.state.setdefault("ec5_drive", self.BASELINE)
        self.state.setdefault("cortical_output_signal", 0.0)
        self.state.setdefault("ec_loop_feedback", 0.0)
        self.state.setdefault("consolidation_signal", 0.0)
        self.state.setdefault("ec5_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("consolidation_accumulator", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ca1: float, sub: float,
                      ec_grid: float, pfc: float) -> float:
        """Composite EC-V drive (Insausti 1997)."""
        target = (self.BASELINE
                  + ca1 * 0.40
                  + sub * 0.25
                  + ec_grid * 0.10
                  + pfc * 0.15)
        return min(1.0, target)

    def _cortical_output(self, drive: float, ca1: float, sub: float) -> float:
        """Broadcast to neocortex (Burwell 2000)."""
        return min(1.0, drive * 0.5 + ca1 * 0.3 + sub * 0.2)

    def _ec_loop_feedback(self, drive: float) -> float:
        """Recurrent feedback to EC-II/III (Kloosterman 2003)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.85)

    def _consolidation(self, drive: float, ca1: float, accum: float) -> float:
        """Systems consolidation signal (Sürmeli 2015)."""
        # Consolidation requires sustained EC-V + CA1 activity over time
        if drive < 0.30 or ca1 < 0.30:
            return accum * 0.92
        boost = drive * ca1 * 0.40
        return min(1.0, accum * 0.95 + boost)

    def _classify_state(self, drive: float, output: float,
                         consolidation: float) -> str:
        if drive < 0.20:
            return "quiet"
        if consolidation > self.CONSOLIDATION_THRESHOLD:
            return "consolidating"
        if output > self.BROADCAST_THRESHOLD:
            return "broadcasting"
        return "looping"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ca1_data = prior.get("HippocampalCA1Dorsal", {})
        if not ca1_data:
            ca1_data = prior.get("HippocampalCA1", {})
        ca1 = float(ca1_data.get("ca1d_drive",
                          ca1_data.get("ca1_output",
                            ca1_data.get("ca1_drive", 0.0))))

        sub_data = prior.get("SubiculumDorsal", {})
        if not sub_data:
            sub_data = prior.get("SubiculumVentral", {})
        if not sub_data:
            sub_data = prior.get("Subiculum", {})
        sub = float(sub_data.get("dsub_drive",
                          sub_data.get("vsub_drive",
                            sub_data.get("sub_drive", 0.0))))

        ec_data = prior.get("EntorhinalCortexGridCells", {})
        ec_grid = float(ec_data.get("ec_output", 0.0))

        pfc_data = prior.get("MedialPrefrontalCortex", {})
        if not pfc_data:
            pfc_data = prior.get("PrelimbicCortex", {})
        pfc = float(pfc_data.get("pfc_drive",
                          pfc_data.get("pl_drive", 0.0)))

        target = self._drive_target(ca1, sub, ec_grid, pfc)
        prev_drive = float(self.state.get("ec5_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        cortical_out = self._cortical_output(new_drive, ca1, sub)
        loop_fb = self._ec_loop_feedback(new_drive)
        accum = float(self.state.get("consolidation_accumulator", 0.0))
        consolidation = self._consolidation(new_drive, ca1, accum)

        state = self._classify_state(new_drive, cortical_out, consolidation)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ec5_drive"] = round(new_drive, 4)
        self.state["cortical_output_signal"] = round(cortical_out, 4)
        self.state["ec_loop_feedback"] = round(loop_fb, 4)
        self.state["consolidation_signal"] = round(consolidation, 4)
        self.state["consolidation_accumulator"] = round(consolidation, 4)
        self.state["ec5_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ec5_drive": round(new_drive, 4),
            "cortical_output_signal": round(cortical_out, 4),
            "ec_loop_feedback": round(loop_fb, 4),
            "consolidation_signal": round(consolidation, 4),
            "ec5_state": state,
        }

    def _consolidation_progress(self) -> float:
        """Cumulative consolidation strength (Sürmeli 2015)."""
        return float(self.state.get("consolidation_accumulator", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ec5_drive", 0.0),
            "output": self.state.get("cortical_output_signal", 0.0),
            "consolidation": self.state.get("consolidation_signal", 0.0),
            "state": self.state.get("ec5_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

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
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
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

