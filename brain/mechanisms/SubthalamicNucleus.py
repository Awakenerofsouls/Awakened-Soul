"""
SubthalamicNucleus — STN / Hyperdirect Pathway / Response Inhibition

NEURAL SUBSTRATE
================
The subthalamic nucleus (STN) is a small biconvex glutamatergic nucleus
in the diencephalic-mesencephalic junction. STN is the only glutamatergic
node in the otherwise GABAergic basal ganglia, providing the "brake" on
action selection. Three classical input pathways converge:

1. **Hyperdirect** — direct corticosubthalamic glutamatergic projection
   from frontal cortex (preSMA, IFG, especially right IFG for stopping).
   Provides ultrafast cortical "stop" signal that bypasses striatum.
2. **Indirect** — via GPe; STN-GPe form a reciprocal pacemaker network.
3. **Pallidostriatal** — STN excites GPi/SNr, which inhibit thalamus.

Aron 2006 demonstrated rIFC → STN hyperdirect pathway is the substrate
of stop-signal response inhibition: when a "stop" cue appears, rIFC
fires rapidly, drives STN, which excites GPi/SNr, suppressing thalamus
and aborting the prepared motor response.

Frank 2007 ("hold your horses") proposed STN raises the decision
threshold during conflict. STN firing increases when multiple
competing options have similar value, slowing decision until the
ambiguity resolves.

STN deep-brain stimulation is the canonical neuromodulation target for
Parkinson's disease — high-frequency stimulation alleviates motor
symptoms by overriding pathological STN output (Hamani 2004).

KEY FINDINGS
============
1. rIFC→STN hyperdirect pathway is the substrate of stop-signal response inhibition — [Aron AR 2006, J Neurosci 26:2424, doi:10.1523/JNEUROSCI.4682-05.2006]
2. STN raises decision threshold during decision conflict; "hold your horses" — [Frank MJ 2007, Science 318:1309, doi:10.1126/science.1146157]
3. STN-GPe reciprocal network forms a pacemaker; STN provides the excitatory drive that GPe inhibits — [Bevan MD 2002, Trends Neurosci 25:525, doi:10.1016/S0166-2236(02)02235-X]
4. STN deep-brain stimulation alleviates Parkinsonian motor symptoms; canonical clinical target — [Hamani C 2004, Brain 127:4, doi:10.1093/brain/awh029]
5. STN excites GPi/SNr to inhibit thalamus; classical box-and-arrow model — [DeLong MR 1990, Trends Neurosci 13:281, doi:10.1016/0166-2236(90)90110-V]

INPUTS
======
- VentrolateralPrefrontalCortex.vlpfc_drive — hyperdirect stop
- CingulateAnterior.acc_drive — conflict signal
- GlobusPallidusExternal.gpe_drive — reciprocal indirect
- DorsomedialStriatum.dms_d2_drive — indirect pathway

OUTPUTS
=======
- stn_drive (0-1) — overall firing rate
- gpi_excitation (0-1) — to GPi/SNr (raises BG output, blocks action)
- response_inhibition_signal (0-1) — stop signal magnitude
- conflict_hold_signal (0-1) — decision-threshold elevator
- gpe_reciprocal_drive (0-1) — to GPe pacemaker partner
- stn_state (str): "stop_active" | "conflict_hold" | "pacemaker" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SubthalamicNucleus(BrainMechanism):
    """STN — hyperdirect-pathway response inhibition + decision-threshold."""

    BASELINE = 0.20  # tonic pacemaker firing
    SMOOTH = 0.20
    STOP_THRESHOLD = 0.50
    CONFLICT_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="SubthalamicNucleus",
            human_analog="Subthalamic nucleus (STN — response inhibition)",
            layer="subcortical",
        )
        self.state.setdefault("stn_drive", self.BASELINE)
        self.state.setdefault("gpi_excitation", 0.0)
        self.state.setdefault("response_inhibition_signal", 0.0)
        self.state.setdefault("conflict_hold_signal", 0.0)
        self.state.setdefault("gpe_reciprocal_drive", 0.0)
        self.state.setdefault("stn_state", "pacemaker")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, vlpfc: float, acc: float, gpe: float,
                       dms_d2: float) -> float:
        """STN drive — hyperdirect cortical + ACC conflict + indirect.

        GPe inhibits STN; high GPe → low STN (Bevan 2002 reciprocal).
        Hyperdirect VLPFC stop signal is fastest and strongest.
        """
        excitation = vlpfc * 0.40 + acc * 0.25 + dms_d2 * 0.20
        gpe_inhibition = gpe * 0.30
        target = self.BASELINE + excitation - gpe_inhibition
        return max(0.0, min(1.0, target))

    def _gpi_excitation(self, drive: float) -> float:
        """STN → GPi/SNr glutamatergic drive (DeLong 1990)."""
        return min(1.0, drive * 0.85)

    def _response_inhibition(self, vlpfc: float, drive: float) -> float:
        """Stop-signal magnitude (Aron 2006). Driven primarily by rIFC/VLPFC
        hyperdirect input."""
        if vlpfc < 0.20:
            return 0.0
        return min(1.0, vlpfc * 0.6 + drive * 0.4)

    def _conflict_hold(self, acc: float, drive: float) -> float:
        """Decision threshold elevation under conflict (Frank 2007)."""
        if acc < 0.20:
            return 0.0
        return min(1.0, acc * 0.7 + drive * 0.3)

    def _gpe_reciprocal(self, drive: float) -> float:
        """STN → GPe reciprocal projection (Bevan 2002 pacemaker)."""
        return min(1.0, drive * 0.75)

    def _classify_state(self, drive: float, stop: float,
                         conflict: float) -> str:
        if drive < 0.10:
            return "quiet"
        if stop > self.STOP_THRESHOLD:
            return "stop_active"
        if conflict > self.CONFLICT_THRESHOLD:
            return "conflict_hold"
        return "pacemaker"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vlpfc_data = prior.get("VentrolateralPrefrontalCortex", {})
        if not vlpfc_data:
            vlpfc_data = prior.get("InferiorFrontalCortex", {})
        vlpfc = float(vlpfc_data.get("vlpfc_drive",
                            vlpfc_data.get("response_inhibition_signal", 0.0)))

        acc_data = prior.get("CingulateAnterior", {})
        acc = float(acc_data.get("acc_drive",
                          acc_data.get("conflict_signal", 0.0)))

        gpe_data = prior.get("GlobusPallidusExternal", {})
        gpe = float(gpe_data.get("gpe_drive",
                          gpe_data.get("gpe_inhibition", 0.0)))

        dms_data = prior.get("DorsomedialStriatum", {})
        dms_d2 = float(dms_data.get("d2_indirect",
                            dms_data.get("dms_drive", 0.0)))

        target = self._drive_target(vlpfc, acc, gpe, dms_d2)
        prev_drive = float(self.state.get("stn_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        gpi_exc = self._gpi_excitation(new_drive)
        stop = self._response_inhibition(vlpfc, new_drive)
        conflict = self._conflict_hold(acc, new_drive)
        gpe_recip = self._gpe_reciprocal(new_drive)

        state = self._classify_state(new_drive, stop, conflict)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["stn_drive"] = round(new_drive, 4)
        self.state["gpi_excitation"] = round(gpi_exc, 4)
        self.state["response_inhibition_signal"] = round(stop, 4)
        self.state["conflict_hold_signal"] = round(conflict, 4)
        self.state["gpe_reciprocal_drive"] = round(gpe_recip, 4)
        self.state["stn_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('stn_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('stn_state', "quiet") if 'stn_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "stn_drive": round(new_drive, 4),
            "gpi_excitation": round(gpi_exc, 4),
            "response_inhibition_signal": round(stop, 4),
            "conflict_hold_signal": round(conflict, 4),
            "gpe_reciprocal_drive": round(gpe_recip, 4),
            "stn_state": state,
        }

    def _decision_threshold(self) -> float:
        """Effective decision threshold elevation (Frank 2007)."""
        return float(self.state.get("conflict_hold_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("stn_drive", 0.0),
            "stop": self.state.get("response_inhibition_signal", 0.0),
            "conflict": self.state.get("conflict_hold_signal", 0.0),
            "state": self.state.get("stn_state", "pacemaker"),
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
            return self.state.get('stn_state', "quiet") if 'stn_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('stn_drive', 0.0)) if 'stn_drive' else 0.0
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
            "drive": self.state.get('stn_drive', 0.0) if 'stn_drive' else 0.0,
            "state": self.state.get('stn_state', "quiet") if 'stn_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

