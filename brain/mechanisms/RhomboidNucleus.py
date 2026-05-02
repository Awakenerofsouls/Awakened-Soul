"""
RhomboidNucleus — Rh / Midline Thalamic Hippocampal-Cortical Bridge

NEURAL SUBSTRATE
================
The rhomboid nucleus (Rh) is a midline thalamic nucleus closely allied
with the nucleus reuniens (Re). Together, Rh-Re form a tight midline
thalamic complex projecting reciprocally to hippocampus (CA1, subiculum)
and medial prefrontal cortex (mPFC). Rh-Re is the primary anatomical
substrate by which mPFC and hippocampus communicate (no direct
hippocampus-mPFC connection exists in either direction).

Rh-Re activity is required for behaviors that demand prefrontal-
hippocampal coordination — working memory tasks, contextual fear
discrimination, and behavioral flexibility (Vertes 2007). Rh-Re also
relays information about goal-directed planning back to hippocampus to
update memory traces.

KEY FINDINGS
============
1. Nucleus reuniens + rhomboid project bidirectionally between mPFC
   and hippocampus; principal route for PFC-HPC communication —
   [Vertes 2007, J Comp Neurol 499:768, doi:10.1002/cne.21135]
2. Re-Rh inactivation impairs working memory tasks requiring
   PFC-hippocampal coordination —
   [Hembrook 2012, Hippocampus 22:1769, doi:10.1002/hipo.22013]
3. Re-Rh lesion impairs contextual fear discrimination + generalization
   reduction —
   [Xu 2012, Curr Biol 22:1857, doi:10.1016/j.cub.2012.07.038]
4. Re-Rh activity synchronizes prefrontal-hippocampal theta during
   spatial working memory —
   [Roy 2017, eLife 6:e30772, doi:10.7554/eLife.30772]
5. Re-Rh integrates prefrontal goal signals with hippocampal context;
   bidirectional coordinator —
   [Cassel 2013, Prog Neurobiol 111:34, doi:10.1016/j.pneurobio.2013.08.006]
"""

from brain.base_mechanism import BrainMechanism


class RhomboidNucleus(BrainMechanism):
    """Rh — midline thalamic hippocampal-cortical bridge."""

    BASELINE = 0.10
    SMOOTH = 0.20
    COORDINATION_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="RhomboidNucleus",
            human_analog="Rhomboid thalamic nucleus",
            layer="limbic",
        )
        self.state.setdefault("rh_drive", self.BASELINE)
        self.state.setdefault("hippocampal_drive_signal", 0.0)
        self.state.setdefault("mpfc_drive_signal", 0.0)
        self.state.setdefault("pfc_hpc_coordination_signal", 0.0)
        self.state.setdefault("working_memory_signal", 0.0)
        self.state.setdefault("rh_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, pfc: float, hpc: float, theta: float) -> float:
        """Rh drive (Vertes 2007)."""
        target = (self.BASELINE
                  + pfc * 0.35
                  + hpc * 0.30
                  + theta * 0.15)
        return min(1.0, target)

    def _hpc_drive(self, drive: float, pfc: float) -> float:
        """Rh→HPC (Cassel 2013)."""
        return min(1.0, drive * 0.5 + pfc * 0.4)

    def _mpfc_drive(self, drive: float, hpc: float) -> float:
        """Rh→mPFC (Vertes 2007)."""
        return min(1.0, drive * 0.5 + hpc * 0.4)

    def _coordination(self, hpc_out: float, pfc_out: float,
                       theta: float) -> float:
        """PFC-HPC coordination signal (Roy 2017)."""
        return min(1.0, hpc_out * pfc_out * 1.5 + theta * 0.2)

    def _working_memory(self, coord: float, drive: float) -> float:
        """Working memory support (Hembrook 2012)."""
        return min(1.0, coord * 0.7 + drive * 0.3)

    def _classify_state(self, drive: float, coord: float, theta: float) -> str:
        if drive < 0.20:
            return "quiet"
        if coord > self.COORDINATION_THRESHOLD:
            return "coordinating"
        if theta > 0.30:
            return "theta_synced"
        return "rest"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        pfc_data = prior.get("MedialPrefrontalCortex", {})
        if not pfc_data:
            pfc_data = prior.get("PrelimbicCortex", {})
        pfc = float(pfc_data.get("pfc_drive",
                          pfc_data.get("pl_drive", 0.0)))

        hpc_data = prior.get("HippocampalCA1Dorsal", {})
        if not hpc_data:
            hpc_data = prior.get("HippocampalCA1", {})
        if not hpc_data:
            hpc_data = prior.get("HippocampalCA1Ventral", {})
        hpc = float(hpc_data.get("ca1d_drive",
                          hpc_data.get("ca1_output",
                            hpc_data.get("vca1_drive", 0.0))))

        sept_data = prior.get("MedialSeptum", {})
        if not sept_data:
            sept_data = prior.get("DiagonalBandBroca", {})
        theta = float(sept_data.get("theta_signal",
                            sept_data.get("theta_drive", 0.0)))

        target = self._drive_target(pfc, hpc, theta)
        prev_drive = float(self.state.get("rh_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        hpc_out = self._hpc_drive(new_drive, pfc)
        pfc_out = self._mpfc_drive(new_drive, hpc)
        coord = self._coordination(hpc_out, pfc_out, theta)
        wm = self._working_memory(coord, new_drive)

        state = self._classify_state(new_drive, coord, theta)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["rh_drive"] = round(new_drive, 4)
        self.state["hippocampal_drive_signal"] = round(hpc_out, 4)
        self.state["mpfc_drive_signal"] = round(pfc_out, 4)
        self.state["pfc_hpc_coordination_signal"] = round(coord, 4)
        self.state["working_memory_signal"] = round(wm, 4)
        self.state["rh_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('rh_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('rh_state', "quiet") if 'rh_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "rh_drive": round(new_drive, 4),
            "hippocampal_drive_signal": round(hpc_out, 4),
            "mpfc_drive_signal": round(pfc_out, 4),
            "pfc_hpc_coordination_signal": round(coord, 4),
            "working_memory_signal": round(wm, 4),
            "rh_state": state,
        }

    def _flexibility_index(self) -> float:
        """Behavioral flexibility from PFC-HPC coordination (Xu 2012)."""
        return float(self.state.get("pfc_hpc_coordination_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("rh_drive", 0.0),
            "coord": self.state.get("pfc_hpc_coordination_signal", 0.0),
            "wm": self.state.get("working_memory_signal", 0.0),
            "state": self.state.get("rh_state", "quiet"),
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
        if not recent:
            return self.state.get('rh_state', "quiet") if 'rh_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('rh_drive', 0.0)) if 'rh_drive' else 0.0
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
            "drive": self.state.get('rh_drive', 0.0) if 'rh_drive' else 0.0,
            "state": self.state.get('rh_state', "quiet") if 'rh_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

