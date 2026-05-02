"""
HippocampalCA3Dorsal — dCA3 / Pattern Completion + Auto-Association

NEURAL SUBSTRATE
================
Dorsal CA3 (dCA3) is the canonical auto-associative network of the
hippocampus. dCA3 pyramidal neurons receive (1) dentate gyrus mossy fiber
"detonator" input — sparse, powerful, conveys pattern-separated codes
from DG; (2) recurrent collaterals — the only major recurrent excitatory
network in cortex, supporting attractor dynamics; (3) direct EC-II
perforant path. Output via Schaffer collaterals to CA1.

Marr 1971 originally proposed CA3 as a Hebbian auto-associator; Treves &
Rolls 1994 formalized this as pattern-completion: a partial cue
reactivates a complete stored memory via attractor convergence. dCA3
specifically is critical for spatial pattern completion (Nakazawa 2002).

KEY FINDINGS
============
1. CA3 recurrent collateral network is the principal cortical
   auto-associator; theoretically supports pattern completion —
   [Marr 1971, Phil Trans R Soc 262:23, doi:10.1098/rstb.1971.0078]
2. CA3 NMDA receptor knockout impairs spatial pattern completion in
   degraded-cue tasks; selective CA3 deficit —
   [Nakazawa 2002, Science 297:211, doi:10.1126/science.1071795]
3. Mossy fiber inputs from dentate are sparse, powerful "detonator"
   synapses driving CA3 pyramidal cells — single-fiber EPSPs sufficient —
   [Henze 2002, Nat Neurosci 5:790, doi:10.1038/nn887]
4. CA3 attractor dynamics quantitatively support pattern completion;
   computational model fits behavioral data —
   [Treves 1994, Hippocampus 4:374, doi:10.1002/hipo.450040319]
5. CA3 generates sharp-wave ripple events that drive CA1 replay;
   originates from CA3 recurrent network —
   [Csicsvari 2000, J Neurosci 20:RC20, PMID 10678901]

INPUTS
======
- DentateGyrusPatternSep.dg_drive (mossy fiber input)
- EntorhinalCortexGridCells.ec_output (perforant path)
- MedialSeptum.theta_signal

OUTPUTS
=======
- dca3_drive (0-1)
- schaffer_collateral_output (0-1) — to CA1
- pattern_completion_signal (0-1)
- recurrent_attractor_signal (0-1)
- swr_origin_signal (0-1)
- dca3_state (str): "completing" | "encoding" | "ripple_origin" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class HippocampalCA3Dorsal(BrainMechanism):
    """dCA3 — auto-associative pattern completion."""

    BASELINE = 0.10
    SMOOTH = 0.20
    COMPLETION_THRESHOLD = 0.45
    RIPPLE_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="HippocampalCA3Dorsal",
            human_analog="Dorsal CA3 (auto-associative)",
            layer="limbic",
        )
        self.state.setdefault("dca3_drive", self.BASELINE)
        self.state.setdefault("schaffer_collateral_output", 0.0)
        self.state.setdefault("pattern_completion_signal", 0.0)
        self.state.setdefault("recurrent_attractor_signal", 0.0)
        self.state.setdefault("swr_origin_signal", 0.0)
        self.state.setdefault("dca3_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("recurrent_trace", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, dg: float, ec: float, theta: float,
                      recurrent: float) -> float:
        """Composite dCA3 drive with mossy fiber dominance (Henze 2002)."""
        target = (self.BASELINE
                  + dg * 0.45        # mossy fibers strong
                  + ec * 0.20        # perforant path
                  + theta * 0.10
                  + recurrent * 0.20)  # recurrent excitation
        return min(1.0, target)

    def _pattern_completion(self, drive: float, dg: float,
                             recurrent: float) -> float:
        """Attractor convergence (Treves 1994; Nakazawa 2002)."""
        # Pattern completion happens when a partial cue (low DG) plus
        # strong recurrent dynamics drives the attractor to convergence.
        if drive < 0.20:
            return 0.0
        # Higher recurrent and lower-DG ratio = more completion
        cue_strength = max(0.0, drive - dg * 0.5)
        return min(1.0, cue_strength * 0.6 + recurrent * 0.4)

    def _recurrent_excitation(self, drive: float, prev_trace: float) -> float:
        """Recurrent collateral self-sustaining (Marr 1971)."""
        if drive < 0.20:
            return prev_trace * 0.80
        return min(1.0, prev_trace * 0.65 + drive * 0.35)

    def _schaffer_output(self, drive: float, completion: float) -> float:
        """Schaffer collateral output to CA1."""
        return min(1.0, drive * 0.55 + completion * 0.45)

    def _swr_origin(self, drive: float, theta: float, recurrent: float) -> float:
        """SWR origination (Csicsvari 2000)."""
        if theta > 0.40:
            return 0.0
        if drive < 0.30:
            return 0.0
        return min(1.0, drive * recurrent * (1.0 - theta) * 1.5)

    def _classify_state(self, drive: float, completion: float,
                         swr: float, theta: float) -> str:
        if drive < 0.20:
            return "quiet"
        if swr > self.RIPPLE_THRESHOLD:
            return "ripple_origin"
        if completion > self.COMPLETION_THRESHOLD:
            return "completing"
        return "encoding"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dg_data = prior.get("DentateGyrusPatternSep", {})
        if not dg_data:
            dg_data = prior.get("DentateGyrus", {})
        dg = float(dg_data.get("dg_drive",
                          dg_data.get("dg_output", 0.0)))

        ec_data = prior.get("EntorhinalCortexGridCells", {})
        ec = float(ec_data.get("ec_output",
                          ec_data.get("grid_cell_signal", 0.0)))

        sept_data = prior.get("MedialSeptum", {})
        if not sept_data:
            sept_data = prior.get("DiagonalBandBroca", {})
        theta = float(sept_data.get("theta_signal",
                            sept_data.get("theta_drive", 0.0)))

        prev_recurrent = float(self.state.get("recurrent_trace", 0.0))
        prev_drive = float(self.state.get("dca3_drive", self.BASELINE))

        target = self._drive_target(dg, ec, theta, prev_recurrent)
        new_drive = self._smooth(prev_drive, target)

        recurrent = self._recurrent_excitation(new_drive, prev_recurrent)
        completion = self._pattern_completion(new_drive, dg, recurrent)
        schaffer = self._schaffer_output(new_drive, completion)
        swr = self._swr_origin(new_drive, theta, recurrent)

        state = self._classify_state(new_drive, completion, swr, theta)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["dca3_drive"] = round(new_drive, 4)
        self.state["schaffer_collateral_output"] = round(schaffer, 4)
        self.state["pattern_completion_signal"] = round(completion, 4)
        self.state["recurrent_attractor_signal"] = round(recurrent, 4)
        self.state["recurrent_trace"] = round(recurrent, 4)
        self.state["swr_origin_signal"] = round(swr, 4)
        self.state["dca3_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('dca3_drive', 0.0)))
        if len(rd) > 60:
            rd = rd[-60:]
        self.state["recent_drives"] = rd

        # extension: track state history if state field exists
        rs = list(self.state.get("recent_states", []))
        cur_state = self.state.get('dca3_state', "quiet") if 'dca3_state' else "quiet"
        rs.append(cur_state)
        if len(rs) > 60:
            rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "dca3_drive": round(new_drive, 4),
            "ca3_output": round(new_drive, 4),  # alias for downstream
            "schaffer_collateral_output": round(schaffer, 4),
            "pattern_completion_signal": round(completion, 4),
            "recurrent_attractor_signal": round(recurrent, 4),
            "swr_origin_signal": round(swr, 4),
            "dca3_state": state,
        }

    def _attractor_stability(self) -> float:
        """Recurrent trace persistence (Treves 1994)."""
        return float(self.state.get("recurrent_trace", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("dca3_drive", 0.0),
            "completion": self.state.get("pattern_completion_signal", 0.0),
            "swr": self.state.get("swr_origin_signal", 0.0),
            "state": self.state.get("dca3_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        """Fraction of recent ticks where the system was non-quiet."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet", "rest", "neutral", ""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        """Fraction of consecutive ticks holding the same state."""
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i - 1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        """Most-frequent recent state."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return self.state.get('dca3_state', "quiet") if 'dca3_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        """Running mean of primary drive over recent window."""
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('dca3_drive', 0.0)) if 'dca3_drive' else 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        """Std-dev proxy of primary drive — tonic-vs-phasic balance."""
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4:
            return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        """Sustained ceiling — runaway feedback flag."""
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        """Sustained collapse — afferent failure flag."""
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v < 0.05 for v in hist[-10:])

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "drive": self.state.get('dca3_drive', 0.0) if 'dca3_drive' else 0.0,
            "state": self.state.get('dca3_state', "quiet") if 'dca3_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

