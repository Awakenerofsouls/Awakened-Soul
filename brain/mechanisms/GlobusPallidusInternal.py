"""
GlobusPallidusInternal — GPi / Basal Ganglia Output (Entopeduncular nucleus)

NEURAL SUBSTRATE
================
The internal globus pallidus (GPi) is one of two GABAergic output nuclei
of the basal ganglia (the other being SNr). In rodents, it is referred
to as the entopeduncular nucleus (EPN). GPi neurons fire tonically at
~80 Hz and project to ventral anterior / ventral lateral thalamus and to
the centromedian/parafascicular intralaminar nuclei, plus the lateral
habenula via the border cells.

GPi is the convergence point of the direct (D1-MSN → GPi) and indirect
(D2-MSN → GPe → STN → GPi) pathways. Tonic GPi activity inhibits
thalamocortical motor circuits; transient D1-direct pause permits action,
indirect-pathway boost suppresses competing actions
(Albin 1989, DeLong 1990).

KEY FINDINGS
============
1. Functional anatomy of BG disorders; D1 direct/D2 indirect with GPi output —
   [Albin RL 1989, Trends Neurosci 12:366, doi:10.1016/0166-2236(89)90074-x]
2. Primate basal ganglia model — DeLong's box-and-arrow circuit —
   [DeLong MR 1990, Trends Neurosci 13:281, doi:10.1016/0166-2236(90)90110-v]
3. Microcircuitry of direct and indirect pathways; GPi convergence —
   [Smith Y 1998, Neuroscience 86:353, doi:10.1016/s0306-4522(98)00004-9]
4. Hikosaka model — GPi/SNr disinhibition gates motor output —
   [Hikosaka O 2000, Physiol Rev 80:953, doi:10.1152/physrev.2000.80.3.953]
5. Mink basal ganglia center-surround focal action selection —
   [Mink JW 1996, Prog Neurobiol 50:381, doi:10.1016/s0301-0082(96)00042-1]
6. GPi DBS effective in PD because it overrides pathological output —
   [Hamani C 2004, Neurosurgery 56:1313, doi:10.1227/01.neu.0000159714.28232.c4]

INPUTS
======
- DorsolateralStriatum.d1_direct_output (direct path GABA inhibition)
- DorsomedialStriatum.d1_direct_output
- SubthalamicNucleus.stn_drive (indirect path glutamate excitation)
- GlobusPallidusExternal.prototypic_output (modulatory)

OUTPUTS
=======
- gpi_drive (0-1) — net tonic inhibitory output
- thalamic_inhibition (0-1) — to VA/VL thalamus
- gpi_state (str): "tonic_inhibit" | "action_gate" | "boosted_inhibit" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class GlobusPallidusInternal(BrainMechanism):
    """GPi / EPN — basal ganglia tonic inhibitory output to thalamus."""

    BASELINE = 0.08
    NETWORK_TONIC = 0.55
    SMOOTH = 0.20
    GATE_THRESHOLD = 0.30
    BOOST_THRESHOLD = 0.65
    QUIET_THRESHOLD = 0.18

    def __init__(self):
        super().__init__(
            name="GlobusPallidusInternal",
            human_analog="Internal globus pallidus / entopeduncular (BG output)",
            layer="subcortical",
        )
        self.state.setdefault("gpi_drive", self.BASELINE)
        self.state.setdefault("thalamic_inhibition", 0.0)
        self.state.setdefault("gpi_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("gate_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, d1_total: float, stn: float, gpe: float) -> float:
        """GPi tonic + STN excitation - D1 direct inhibition - GPe modulation
        (DeLong 1990, Smith 1998)."""
        # Some network input required to engage tonic firing
        any_input = max(d1_total, stn, gpe)
        tonic = self.BASELINE + self.NETWORK_TONIC * any_input
        # D1 direct path INHIBITS GPi (pause-on-action)
        # STN EXCITES GPi (indirect boost / hyperdirect)
        # GPe prototypic INHIBITS GPi (downstream proto projection)
        target = tonic - d1_total * 0.55 + stn * 0.35 - gpe * 0.20
        return max(0.0, min(1.0, target))

    def _thalamic_inhibition(self, drive: float) -> float:
        """GPi → thalamus is GABAergic; output magnitude tracks drive
        (Hikosaka 2000)."""
        return min(1.0, drive * 0.95)

    def _classify_state(self, drive: float, d1: float, stn: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        # Strong D1 with low STN → action gate (disinhibition of thalamus)
        if d1 > 0.35 and drive < 0.30:
            return "action_gate"
        # High STN drive raises tonic → boosted inhibition (stop)
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

    def _read_gpe(self, prior: dict) -> float:
        gpe = prior.get("GlobusPallidusExternal", {})
        return float(gpe.get("prototypic_output",
                       gpe.get("gpe_drive", 0.0)))

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        d1_dls = self._read_d1(prior, "DorsolateralStriatum")
        d1_dms = self._read_d1(prior, "DorsomedialStriatum")
        d1_total = min(1.0, d1_dls * 0.55 + d1_dms * 0.55)
        stn = self._read_stn(prior)
        gpe = self._read_gpe(prior)

        target = self._drive_target(d1_total, stn, gpe)
        prev_drive = float(self.state.get("gpi_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        thal_inh = self._thalamic_inhibition(new_drive)
        state = self._classify_state(new_drive, d1_total, stn)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        gate = int(self.state.get("gate_count", 0))
        if state == "action_gate":
            gate += 1

        self.state["gpi_drive"] = round(new_drive, 4)
        self.state["thalamic_inhibition"] = round(thal_inh, 4)
        self.state["gpi_state"] = state
        self.state["recent_states"] = recent
        self.state["gate_count"] = gate
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('gpi_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('gpi_state', "quiet") if 'gpi_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "gpi_drive": round(new_drive, 4),
            "thalamic_inhibition": round(thal_inh, 4),
            "gpi_state": state,
        }

    def _action_gate_index(self) -> float:
        """Mink center-surround / focal selection proxy (Mink 1996)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return self.state.get("gate_count", 0) / ticks

    def _direct_indirect_balance(self, d1: float, stn: float) -> float:
        """Net direct-vs-indirect drive balance.
        Positive: direct dominant (action permitted via GPi pause).
        Negative: indirect dominant (action suppressed).
        Reflects Albin 1989 / DeLong 1990 dichotomy."""
        return d1 - stn

    def _pd_proxy(self) -> float:
        """Parkinsonian-state proxy: chronic high tonic drive without
        gating events (Hamani 2004)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        gates = self.state.get("gate_count", 0)
        avg_drive = float(self.state.get("gpi_drive", 0.0))
        # PD-like: low gating frequency + high tonic drive
        return min(1.0, max(0.0, avg_drive - (gates / ticks)))

    def _saccade_thalamic_balance(self) -> float:
        """Indicator of motor-thalamic disinhibition strength.
        High value means thalamus released from GPi (action permitted)."""
        thal_inh = float(self.state.get("thalamic_inhibition", 0.0))
        return 1.0 - thal_inh

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("gpi_drive", 0.0),
            "thal_inh": self.state.get("thalamic_inhibition", 0.0),
            "state": self.state.get("gpi_state", "quiet"),
            "gates": self.state.get("gate_count", 0),
            "ticks": self.state.get("tick_count", 0),
        }

    def _state_distribution(self) -> dict:
        """Recent-window distribution over GPi states.
        Useful for diagnostic introspection (DeLong 1990 — output rate
        signatures of hyper/hypokinetic regimes)."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return {"tonic": 0.0, "gate": 0.0, "boost": 0.0}
        n = len(recent)
        return {
            "tonic": sum(1 for s in recent if s == "tonic_inhibit") / n,
            "gate": sum(1 for s in recent if s == "action_gate") / n,
            "boost": sum(1 for s in recent if s == "boosted_inhibit") / n,
        }

    def _output_to_thalamus(self) -> float:
        """Net thalamic disinhibition pressure — how strongly motor
        thalamus is being released for action (Hikosaka 2000)."""
        thal_inh = float(self.state.get("thalamic_inhibition", 0.0))
        return 1.0 - thal_inh

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
            return self.state.get('gpi_state', "quiet") if 'gpi_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('gpi_drive', 0.0)) if 'gpi_drive' else 0.0
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
            "drive": self.state.get('gpi_drive', 0.0) if 'gpi_drive' else 0.0,
            "state": self.state.get('gpi_state', "quiet") if 'gpi_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

