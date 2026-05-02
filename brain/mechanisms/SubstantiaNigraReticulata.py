"""
SubstantiaNigraReticulata — SNr / Basal Ganglia Output (oculomotor / collicular)

NEURAL SUBSTRATE
================
The substantia nigra pars reticulata (SNr) is the second GABAergic
output of the basal ganglia (alongside GPi). SNr neurons fire tonically
at high rates (50-100 Hz) and project most prominently to:
  - Superior colliculus (SC) — saccade gating (Hikosaka & Wurtz 1983)
  - Mediodorsal / ventromedial / ventrolateral thalamus
  - Pedunculopontine tegmental nucleus (PPN)
  - Reticular formation

SNr receives the same inputs as GPi (D1-MSN direct + STN indirect) but
preferentially handles oculomotor / orienting / cognitive output rather
than skeletomotor. Its tonic inhibition holds SC fixation cells in
check; transient pause-on-saccade disinhibits SC build-up cells
(Hikosaka 1983 series I-IV).

KEY FINDINGS
============
1. SNr cells pause for memory-contingent saccades; tonic-pause gating —
   [Hikosaka O 1983, J Neurophysiol 49:1268, PMID 6864249]
2. SNr → SC pathway gates saccades by phasic disinhibition —
   [Hikosaka O 1983b, J Neurophysiol 49:1285, PMID 6306173]
3. Multiple SNr output channels — collicular, thalamic, tegmental review —
   [Deniau JM 2007, Neuroscience 145:1314, doi:10.1016/j.neuroscience.2006.08.014]
4. SNr neurons topographically segregated by downstream target —
   [Schmitt LI 2007, J Neurophysiol 97:3631, doi:10.1152/jn.01179.2006]
5. Mink BG center-surround; SNr surround inhibition selects action —
   [Mink JW 1996, Prog Neurobiol 50:381, doi:10.1016/s0301-0082(96)00042-1]
6. Hikosaka review of basal-ganglia control of saccades —
   [Hikosaka O 2000, Physiol Rev 80:953, doi:10.1152/physrev.2000.80.3.953]

INPUTS
======
- DorsomedialStriatum.d1_direct_output (D1 GABA inhibition — caudate)
- DorsolateralStriatum.d1_direct_output (D1 GABA — putamen)
- SubthalamicNucleus.stn_drive (glutamate excitation)

OUTPUTS
=======
- snr_drive (0-1) — overall tonic firing
- collicular_inhibition (0-1) — to superior colliculus
- thalamic_inhibition (0-1) — to MD/VM/VL thalamus
- saccade_gate_signal (0-1) — pause-disinhibition signal
- snr_state (str): "tonic_inhibit" | "saccade_gate" | "boosted_inhibit" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SubstantiaNigraReticulata(BrainMechanism):
    """SNr — basal ganglia output to SC + thalamus, saccade/orienting gate."""

    BASELINE = 0.08
    NETWORK_TONIC = 0.55
    SMOOTH = 0.20
    GATE_THRESHOLD = 0.30
    BOOST_THRESHOLD = 0.65
    QUIET_THRESHOLD = 0.18

    def __init__(self):
        super().__init__(
            name="SubstantiaNigraReticulata",
            human_analog="SN pars reticulata (BG output, oculomotor / orienting)",
            layer="subcortical",
        )
        self.state.setdefault("snr_drive", self.BASELINE)
        self.state.setdefault("collicular_inhibition", 0.0)
        self.state.setdefault("thalamic_inhibition", 0.0)
        self.state.setdefault("saccade_gate_signal", 0.0)
        self.state.setdefault("snr_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("saccade_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, d1_total: float, stn: float) -> float:
        """SNr tonic + STN excitation - D1 inhibition (Hikosaka 2000)."""
        any_input = max(d1_total, stn)
        tonic = self.BASELINE + self.NETWORK_TONIC * any_input
        target = tonic - d1_total * 0.55 + stn * 0.35
        return max(0.0, min(1.0, target))

    def _collicular_inhibition(self, drive: float) -> float:
        """SNr → SC GABA tonic suppression (Hikosaka 1983)."""
        return min(1.0, drive * 0.95)

    def _thalamic_inhibition(self, drive: float) -> float:
        """SNr → MD/VM/VL GABA (Deniau 2007)."""
        return min(1.0, drive * 0.85)

    def _saccade_gate(self, drive: float, d1: float) -> float:
        """Pause-on-saccade signal: drive drops while D1 is high
        (Hikosaka 1983)."""
        # Saccade gating = transient release from SNr inhibition
        # = high D1 with low residual SNr drive
        if d1 < 0.30:
            return 0.0
        # Inverse of drive when D1 paused it
        return min(1.0, d1 * (1.0 - drive))

    def _classify_state(self, drive: float, gate: float, stn: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if gate > self.GATE_THRESHOLD:
            return "saccade_gate"
        if stn > 0.55 and drive > self.BOOST_THRESHOLD:
            return "boosted_inhibit"
        return "tonic_inhibit"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _read_d1(self, prior: dict, key: str) -> float:
        d = prior.get(key, {})
        return float(d.get("d1_direct_output",
                       d.get("d1_output",
                          d.get("direct_drive", 0.0))))

    def _read_stn(self, prior: dict) -> float:
        stn = prior.get("SubthalamicNucleus", {})
        return float(stn.get("stn_drive",
                       stn.get("stn_output", 0.0)))

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        d1_dms = self._read_d1(prior, "DorsomedialStriatum")
        d1_dls = self._read_d1(prior, "DorsolateralStriatum")
        # SNr is biased toward DMS / caudate input (oculomotor / cognitive)
        d1_total = min(1.0, d1_dms * 0.65 + d1_dls * 0.40)
        stn = self._read_stn(prior)

        target = self._drive_target(d1_total, stn)
        prev_drive = float(self.state.get("snr_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        sc_inh = self._collicular_inhibition(new_drive)
        thal_inh = self._thalamic_inhibition(new_drive)
        gate = self._saccade_gate(new_drive, d1_total)

        state = self._classify_state(new_drive, gate, stn)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        sacs = int(self.state.get("saccade_count", 0))
        if state == "saccade_gate":
            sacs += 1

        self.state["snr_drive"] = round(new_drive, 4)
        self.state["collicular_inhibition"] = round(sc_inh, 4)
        self.state["thalamic_inhibition"] = round(thal_inh, 4)
        self.state["saccade_gate_signal"] = round(gate, 4)
        self.state["snr_state"] = state
        self.state["recent_states"] = recent
        self.state["saccade_count"] = sacs
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('snr_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('snr_state', "quiet") if 'snr_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "snr_drive": round(new_drive, 4),
            "collicular_inhibition": round(sc_inh, 4),
            "thalamic_inhibition": round(thal_inh, 4),
            "saccade_gate_signal": round(gate, 4),
            "snr_state": state,
        }

    def _saccade_rate(self) -> float:
        """Saccade-per-tick proxy (Hikosaka 1983)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return self.state.get("saccade_count", 0) / ticks

    def _output_channel_balance(self) -> dict:
        """Relative weighting of SC vs thalamic vs tegmental output
        channels (Deniau 2007)."""
        sc = float(self.state.get("collicular_inhibition", 0.0))
        thal = float(self.state.get("thalamic_inhibition", 0.0))
        # SC is weighted slightly higher in our scaling — typical for
        # oculomotor SNr; tegmental implicit ~ thalamic
        return {
            "collicular_share": sc / (sc + thal + 1e-6),
            "thalamic_share": thal / (sc + thal + 1e-6),
        }

    def _surround_inhibition(self, drive: float, gate: float) -> float:
        """Mink center-surround proxy: high tonic surround inhibition
        with focal pause (Mink 1996, Schmitt 2007)."""
        # Surround = drive remaining outside the gate window
        return max(0.0, drive - gate)

    def _fixation_strength(self) -> float:
        """Tonic SC inhibition keeps fixation cells active —
        higher value = stronger fixation (Hikosaka 2000)."""
        return float(self.state.get("collicular_inhibition", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("snr_drive", 0.0),
            "sc_inh": self.state.get("collicular_inhibition", 0.0),
            "thal_inh": self.state.get("thalamic_inhibition", 0.0),
            "gate": self.state.get("saccade_gate_signal", 0.0),
            "state": self.state.get("snr_state", "quiet"),
            "saccade_count": self.state.get("saccade_count", 0),
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
            return self.state.get('snr_state', "quiet") if 'snr_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('snr_drive', 0.0)) if 'snr_drive' else 0.0
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
            "drive": self.state.get('snr_drive', 0.0) if 'snr_drive' else 0.0,
            "state": self.state.get('snr_state', "quiet") if 'snr_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

