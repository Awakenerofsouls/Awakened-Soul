"""
SupplementaryMotorArea — SMA / Pre-SMA / Medial Brodmann 6

NEURAL SUBSTRATE
================
The supplementary motor area (SMA-proper, F3 in macaques) sits on the
medial wall of Brodmann area 6, anterior to the leg representation of M1
and superior to the cingulate. Together with pre-SMA (F6), the more
rostral region anterior to the vertical commissural plane (VAC), it
forms the supplementary motor complex. SMA-proper is body-mapped and
projects directly to M1 and the spinal cord, while pre-SMA lacks direct
spinal projection and connects with prefrontal cortex, supporting
higher-order action control (Nachev et al. 2008).

SMA is preferentially engaged during *internally guided* movements
(actions selected from memory rather than triggered by external cues —
Mushiake, Inase & Tanji 1991), and SMA neurons code multi-step movement
*sequences*: many cells fire selectively for a particular movement only
when it occurs in a particular ordinal position within a learned
sequence (Tanji 2001; Shima & Tanji 1998 / 2000). Bilateral pharmacological
inactivation of SMA + pre-SMA disrupts the temporal organization of
multiple movements while preserving execution of individual movements.

KEY FINDINGS
============
1. SMA neurons fire preferentially for internally generated sequential
   movements; PM more for visually triggered ones —
   [Mushiake H 1991, J Neurophysiol 66:705, PMID 1753282]
2. SMA cells encode movement sequences and ordinal position within
   learned sequences — review of cortical motor sequencing —
   [Tanji J 2001, Annu Rev Neurosci 24:631, doi:10.1146/annurev.neuro.24.1.631]
3. Both SMA and pre-SMA are crucial for the temporal organization of
   multiple movements; muscimol inactivation disrupts sequence —
   [Shima K 1998, J Neurophysiol 80:3247, PMID 9862919]
4. Functional dissociation along a rostrocaudal SMA-proper / pre-SMA
   gradient — review of the supplementary motor complex —
   [Nachev P 2008, Nat Rev Neurosci 9:856, doi:10.1038/nrn2478]
5. SMA cells active for several movements ahead in a learned sequence,
   reflecting motor-plan look-ahead —
   [Tanji J 1994, Nature 371:413, doi:10.1038/371413a0]

INPUTS
======
- BasalGangliaPallidum.gpi_inhibition (BG → thalamus → SMA gating)
- VentralAnteriorThalamus.va_drive (BG-thalamic relay)
- PrelimbicCortex.prelimbic_drive (cognitive goal)
- PrimaryMotorCortex.m1_drive (recurrent)
- PreSupplementaryMotorArea.pre_sma_drive (rostral SMA partner)

OUTPUTS
=======
- sma_drive (0-1) — overall SMA activation
- pre_sma_drive (0-1) — rostral pre-SMA activity
- internal_movement_signal (0-1) — internally generated movement
- sequence_position (int) — ordinal position in tracked sequence
- sequence_signal (0-1) — sequence-encoding activity
- sma_state (str): "internally_generated" | "sequencing" |
                   "preparing" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SupplementaryMotorArea(BrainMechanism):
    """SMA — internally generated movements / sequence motor planning."""

    BASELINE = 0.07
    SMOOTH = 0.20
    ACTIVE_THRESHOLD = 0.20
    SEQUENCE_THRESHOLD = 0.35
    INTERNAL_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="SupplementaryMotorArea",
            human_analog="Supplementary motor area (SMA + pre-SMA, medial Brodmann 6)",
            layer="neocortical",
        )
        self.state.setdefault("sma_drive", self.BASELINE)
        self.state.setdefault("pre_sma_drive", 0.0)
        self.state.setdefault("internal_movement_signal", 0.0)
        self.state.setdefault("sequence_position", 0)
        self.state.setdefault("sequence_signal", 0.0)
        self.state.setdefault("sma_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    # ----- helpers ----------------------------------------------------------

    def _drive_target(self, va: float, prelimbic: float, m1: float,
                      pre_partner: float, gpi_inh: float) -> float:
        """Composite SMA drive with BG/pallidal inhibition (Nachev 2008)."""
        # GPi releases SMA from inhibition when low
        disinh = max(0.0, 1.0 - gpi_inh)
        target = (self.BASELINE
                  + va * 0.30 * disinh
                  + prelimbic * 0.25
                  + m1 * 0.10
                  + pre_partner * 0.15)
        return min(1.0, target)

    def _pre_sma(self, drive: float, prelimbic: float) -> float:
        """Pre-SMA rostral partner — cognitive control (Nachev 2008)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.5 + prelimbic * 0.5)

    def _internal_movement(self, drive: float, prelimbic: float,
                              external: float) -> float:
        """Internally generated movement signal (Mushiake 1991).
        Suppressed by strong external visual cue."""
        if drive < 0.15:
            return 0.0
        # external visual cue REDUCES the internal-movement preference
        return min(1.0, drive * 0.5 + prelimbic * 0.5 - external * 0.3)

    def _sequence_signal(self, drive: float, prelimbic: float,
                          pre_sma: float) -> float:
        """Sequence-encoding activity (Tanji 2001, Shima 1998)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + prelimbic * 0.3 + pre_sma * 0.3)

    def _next_position(self, prev: int, seq_signal: float) -> int:
        """Ordinal sequence position increments while sequence is active."""
        if seq_signal < self.SEQUENCE_THRESHOLD:
            return 0
        # advance position; reset to 0 when not actively sequencing
        return min(prev + 1, 32)

    def _classify_state(self, drive: float, internal: float,
                         seq: float) -> str:
        if drive < self.ACTIVE_THRESHOLD:
            return "quiet"
        if seq > self.SEQUENCE_THRESHOLD:
            return "sequencing"
        if internal > self.INTERNAL_THRESHOLD:
            return "internally_generated"
        return "preparing"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ----- main tick --------------------------------------------------------

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        va_data = prior.get("VentralAnteriorThalamus", {})
        if not va_data:
            va_data = prior.get("VentrolateralThalamus", {})
        va = float(va_data.get("va_drive",
                          va_data.get("vl_drive",
                            va_data.get("thalamic_drive", 0.0))))

        prelimbic_data = prior.get("PrelimbicCortex", {})
        prelimbic = float(prelimbic_data.get("prelimbic_drive",
                                          prelimbic_data.get("plc_drive", 0.0)))

        m1_data = prior.get("PrimaryMotorCortex", {})
        m1 = float(m1_data.get("m1_drive", 0.0))

        gpi_data = prior.get("BasalGangliaPallidum", {})
        if not gpi_data:
            gpi_data = prior.get("GlobusPallidusInternal", {})
        gpi_inh = float(gpi_data.get("gpi_inhibition",
                            gpi_data.get("gpi_drive", 0.0)))

        pre_partner = float(prior.get("PreSupplementaryMotorArea", {}).get(
            "pre_sma_drive", 0.0))

        # External visual cues suppress internally generated movement signal
        v1_data = prior.get("VisualCortexV1", {})
        if not v1_data:
            v1_data = prior.get("PrimaryVisualCortex", {})
        external = float(v1_data.get("v1_drive", 0.0))

        target = self._drive_target(va, prelimbic, m1, pre_partner, gpi_inh)
        prev_drive = float(self.state.get("sma_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        pre_sma = self._pre_sma(new_drive, prelimbic)
        internal = max(0.0, self._internal_movement(new_drive, prelimbic, external))
        seq = self._sequence_signal(new_drive, prelimbic, pre_sma)
        prev_pos = int(self.state.get("sequence_position", 0))
        new_pos = self._next_position(prev_pos, seq)
        state = self._classify_state(new_drive, internal, seq)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["sma_drive"] = round(new_drive, 4)
        self.state["pre_sma_drive"] = round(pre_sma, 4)
        self.state["internal_movement_signal"] = round(internal, 4)
        self.state["sequence_position"] = new_pos
        self.state["sequence_signal"] = round(seq, 4)
        self.state["sma_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('sma_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('sma_state', "quiet") if 'sma_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "sma_drive": round(new_drive, 4),
            "pre_sma_drive": round(pre_sma, 4),
            "internal_movement_signal": round(internal, 4),
            "sequence_position": new_pos,
            "sequence_signal": round(seq, 4),
            "sma_state": state,
        }

    # ----- summary helpers --------------------------------------------------

    def _is_in_sequence(self) -> bool:
        return float(self.state.get("sequence_signal", 0.0)) > self.SEQUENCE_THRESHOLD

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("sma_drive", 0.0),
            "internal": self.state.get("internal_movement_signal", 0.0),
            "sequence": self.state.get("sequence_signal", 0.0),
            "position": self.state.get("sequence_position", 0),
            "state": self.state.get("sma_state", "quiet"),
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
            return self.state.get('sma_state', "quiet") if 'sma_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('sma_drive', 0.0)) if 'sma_drive' else 0.0
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
            "drive": self.state.get('sma_drive', 0.0) if 'sma_drive' else 0.0,
            "state": self.state.get('sma_state', "quiet") if 'sma_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

