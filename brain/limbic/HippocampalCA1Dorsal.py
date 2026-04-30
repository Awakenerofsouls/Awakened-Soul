"""
HippocampalCA1Dorsal — dCA1 / Spatial Hippocampus Output

NEURAL SUBSTRATE
================
Dorsal CA1 (dCA1) is the primary spatial-cognitive output of the dorsal
hippocampus. dCA1 pyramidal neurons are the canonical "place cells"
(O'Keefe 1971). dCA1 receives Schaffer collateral input from CA3 plus
direct temporoammonic input from EC-III, and projects to subiculum and
EC-V — the gateway to neocortex for spatial/episodic memory.

Functionally distinct from vCA1: dCA1 lesions impair spatial memory
without affecting anxiety; vCA1 lesions are anxiolytic without spatial
deficits (Fanselow & Dong 2010 — dorsal/ventral functional gradient).

KEY FINDINGS
============
1. dCA1 pyramidal cells are place cells encoding spatial location;
   discovered in freely behaving rats —
   [O'Keefe 1971, Brain Res 34:171, PMID 5124915]
2. dCA1 lesion abolishes spatial memory in Morris water maze; selective
   spatial deficit — [Morris 1982, Nature 297:681, doi:10.1038/297681a0]
3. Dorsal-ventral hippocampal gradient: dorsal spatial/cognitive,
   ventral emotional — [Fanselow 2010, Neuron 65:7, doi:10.1016/j.neuron.2009.11.031]
4. Sharp-wave ripples (SWRs) in dCA1 reactivate spatial sequences during
   rest; required for memory consolidation —
   [Wilson 1994, Science 265:676, PMID 8036517]
5. Selective dCA1 silencing during SWRs impairs memory consolidation
   without affecting acquisition —
   [Girardeau 2009, Nat Neurosci 12:1222, doi:10.1038/nn.2384]

INPUTS
======
- HippocampalCA3Dorsal.dca3_drive (Schaffer collateral)
- EntorhinalLayer3.temporoammonic_signal (TA pathway)
- MedialSeptum.theta_signal (theta rhythm)

OUTPUTS
=======
- ca1d_drive (0-1)
- subicular_output (0-1)
- ec5_input_signal (0-1)
- ripple_event_signal (0-1) — SWR replay
- place_cell_activation (0-1)
- ca1d_state (str): "place_active" | "ripple_replay" | "theta_active" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class HippocampalCA1Dorsal(BrainMechanism):
    """dCA1 — spatial place cells / hippocampal output."""

    BASELINE = 0.10
    SMOOTH = 0.20
    RIPPLE_THRESHOLD = 0.55
    PLACE_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="HippocampalCA1Dorsal",
            human_analog="Dorsal CA1 (spatial place cells)",
            layer="limbic",
        )
        self.state.setdefault("ca1d_drive", self.BASELINE)
        self.state.setdefault("subicular_output", 0.0)
        self.state.setdefault("ec5_input_signal", 0.0)
        self.state.setdefault("ripple_event_signal", 0.0)
        self.state.setdefault("place_cell_activation", 0.0)
        self.state.setdefault("ca1d_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("ripple_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ca3: float, ta: float, theta: float) -> float:
        """Composite dCA1 drive (O'Keefe 1971 — pyramidal pooled input)."""
        target = (self.BASELINE
                  + ca3 * 0.40
                  + ta * 0.35
                  + theta * 0.10)
        return min(1.0, target)

    def _place_cell(self, drive: float, ca3: float, ta: float) -> float:
        """Place-cell activation (O'Keefe 1971)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.5 + ca3 * 0.3 + ta * 0.2)

    def _ripple(self, drive: float, theta: float, ca3: float) -> float:
        """SWR replay events occur during low-theta + high CA3 (Wilson 1994)."""
        # Ripples emerge when theta is low (rest/quiet wake) AND CA3 has
        # accumulated drive. Anti-correlated with theta.
        if theta > 0.40:
            return 0.0
        if ca3 < 0.30:
            return 0.0
        return min(1.0, ca3 * (1.0 - theta) * 1.2)

    def _subicular_output(self, drive: float, place: float) -> float:
        """Output to subiculum (gateway to EC-V)."""
        return min(1.0, drive * 0.6 + place * 0.4)

    def _ec5_input(self, drive: float, place: float) -> float:
        """Direct CA1→EC-V projection."""
        return min(1.0, drive * 0.5 + place * 0.3)

    def _classify_state(self, drive: float, place: float,
                         ripple: float, theta: float) -> str:
        if drive < 0.20:
            return "quiet"
        if ripple > self.RIPPLE_THRESHOLD:
            return "ripple_replay"
        if theta > 0.40:
            return "theta_active"
        if place > self.PLACE_THRESHOLD:
            return "place_active"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ca3_data = prior.get("HippocampalCA3Dorsal", {})
        if not ca3_data:
            ca3_data = prior.get("HippocampalCA3", {})
        ca3 = float(ca3_data.get("dca3_drive",
                          ca3_data.get("ca3_output",
                            ca3_data.get("ca3_drive", 0.0))))

        ec3_data = prior.get("EntorhinalLayer3", {})
        ta = float(ec3_data.get("temporoammonic_signal",
                          ec3_data.get("ec3_drive", 0.0)))

        sept_data = prior.get("MedialSeptum", {})
        if not sept_data:
            sept_data = prior.get("DiagonalBandBroca", {})
        theta = float(sept_data.get("theta_signal",
                            sept_data.get("theta_drive", 0.0)))

        target = self._drive_target(ca3, ta, theta)
        prev_drive = float(self.state.get("ca1d_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        place = self._place_cell(new_drive, ca3, ta)
        ripple = self._ripple(new_drive, theta, ca3)
        sub_out = self._subicular_output(new_drive, place)
        ec5_in = self._ec5_input(new_drive, place)

        state = self._classify_state(new_drive, place, ripple, theta)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        ripple_count = int(self.state.get("ripple_count", 0))
        if state == "ripple_replay":
            ripple_count += 1

        self.state["ca1d_drive"] = round(new_drive, 4)
        self.state["subicular_output"] = round(sub_out, 4)
        self.state["ec5_input_signal"] = round(ec5_in, 4)
        self.state["ripple_event_signal"] = round(ripple, 4)
        self.state["place_cell_activation"] = round(place, 4)
        self.state["ca1d_state"] = state
        self.state["recent_states"] = recent
        self.state["ripple_count"] = ripple_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ca1d_drive": round(new_drive, 4),
            "subicular_output": round(sub_out, 4),
            "ec5_input_signal": round(ec5_in, 4),
            "ripple_event_signal": round(ripple, 4),
            "place_cell_activation": round(place, 4),
            "ca1d_state": state,
        }

    def _consolidation_pressure(self) -> float:
        """Cumulative ripple count proxies consolidation (Girardeau 2009)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("ripple_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ca1d_drive", 0.0),
            "place": self.state.get("place_cell_activation", 0.0),
            "ripple": self.state.get("ripple_event_signal", 0.0),
            "state": self.state.get("ca1d_state", "quiet"),
        }
