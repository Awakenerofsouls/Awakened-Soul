"""
SeptofimbrialNucleus — Sfi / Hippocampal-Habenular Interface

NEURAL SUBSTRATE
================
The septofimbrial nucleus (Sfi) is a small midline septal structure
sitting at the junction of the fimbria-fornix and the medial septum.
Receives massive hippocampal input (subicular + CA1 fibers via fimbria)
and projects rostrally to triangular septal nucleus (TS) and caudally
to lateral habenula (LHb) via stria medullaris. Sfi serves as the
hippocampal gateway into the dorsal diencephalic conduction system —
how stored episodic context biases habenular reward/aversion gating.

KEY FINDINGS
============
1. Septofimbrial nucleus receives hippocampal subicular afferents and
   projects to medial habenula —
   [Risold 1997, Brain Res Rev 24:115, PMID 9385452]
2. Septohabenular pathway (Sfi + TS → habenula) modulates fear-like
   behavior; lesion increases anxiety —
   [Yamaguchi 2013, J Neurosci 33:14365, doi:10.1523/JNEUROSCI.4385-12.2013]
3. Sfi neurons co-express glutamate + GABA; mixed excitatory-inhibitory
   habenular drive —
   [Aizawa 2011, J Comp Neurol 519:4051, doi:10.1002/cne.22685]
4. Fimbria-fornix bundle including septofimbrial fibers carries
   hippocampal output to limbic forebrain —
   [Swanson 1977, Brain Res 119:443, PMID 65067]
5. Septofimbrial → habenula pathway critical for
   hippocampal-modulation of midbrain monoamine systems —
   [Hsu 2014, Neuron 84:1213, doi:10.1016/j.neuron.2014.11.008]

INPUTS
======
- HippocampalCA1Ventral.vca1_drive (or HippocampalCA1.ca1_output)
- SubiculumVentral.vsub_drive (or SubiculumDorsal)
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- sfi_drive (0-1)
- mhb_drive_signal (0-1)
- lhb_drive_signal (0-1)
- hippocampal_habenular_relay (0-1)
- sfi_state (str): "relay_active" | "rest" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SeptofimbrialNucleus(BrainMechanism):
    """Sfi — hippocampo-habenular gateway."""

    BASELINE = 0.10
    SMOOTH = 0.20
    RELAY_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="SeptofimbrialNucleus",
            human_analog="Septofimbrial nucleus",
            layer="limbic",
        )
        self.state.setdefault("sfi_drive", self.BASELINE)
        self.state.setdefault("mhb_drive_signal", 0.0)
        self.state.setdefault("lhb_drive_signal", 0.0)
        self.state.setdefault("hippocampal_habenular_relay", 0.0)
        self.state.setdefault("sfi_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, vca1: float, sub: float, intensity: float) -> float:
        """Sfi drive (Risold 1997)."""
        target = (self.BASELINE
                  + vca1 * 0.40
                  + sub * 0.30
                  + intensity * 0.15)
        return min(1.0, target)

    def _mhb_drive(self, drive: float, intensity: float) -> float:
        """Sfi→MHb (Hsu 2014)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.5 + intensity * 0.3)

    def _lhb_drive(self, drive: float, sign: int, intensity: float) -> float:
        """Sfi→LHb — biased toward aversive contexts (Yamaguchi 2013)."""
        aversive = max(0.0, -sign * intensity)
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + aversive * 0.6)

    def _relay_signal(self, mhb: float, lhb: float) -> float:
        """Combined hippocampal→habenular relay (Swanson 1977)."""
        return min(1.0, max(mhb, lhb) * 0.7 + (mhb + lhb) * 0.20)

    def _classify_state(self, drive: float, relay: float) -> str:
        if drive < 0.20:
            return "quiet"
        if relay > self.RELAY_THRESHOLD:
            return "relay_active"
        return "rest"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vca1_data = prior.get("HippocampalCA1Ventral", {})
        if not vca1_data:
            vca1_data = prior.get("HippocampalCA1", {})
        vca1 = float(vca1_data.get("vca1_drive",
                            vca1_data.get("ca1_output", 0.0)))

        sub_data = prior.get("SubiculumVentral", {})
        if not sub_data:
            sub_data = prior.get("SubiculumDorsal", {})
        if not sub_data:
            sub_data = prior.get("Subiculum", {})
        sub = float(sub_data.get("vsub_drive",
                          sub_data.get("dsub_drive",
                            sub_data.get("sub_drive", 0.0))))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        target = self._drive_target(vca1, sub, intensity)
        prev_drive = float(self.state.get("sfi_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        mhb = self._mhb_drive(new_drive, intensity)
        lhb = self._lhb_drive(new_drive, sign, intensity)
        relay = self._relay_signal(mhb, lhb)

        state = self._classify_state(new_drive, relay)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["sfi_drive"] = round(new_drive, 4)
        self.state["mhb_drive_signal"] = round(mhb, 4)
        self.state["lhb_drive_signal"] = round(lhb, 4)
        self.state["hippocampal_habenular_relay"] = round(relay, 4)
        self.state["sfi_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('sfi_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('sfi_state', "quiet") if 'sfi_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "sfi_drive": round(new_drive, 4),
            "mhb_drive_signal": round(mhb, 4),
            "lhb_drive_signal": round(lhb, 4),
            "hippocampal_habenular_relay": round(relay, 4),
            "sfi_state": state,
        }

    def _hippocampal_bias_strength(self) -> float:
        """How much Sfi is biasing habenula on this trial (Aizawa 2011)."""
        return float(self.state.get("hippocampal_habenular_relay", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("sfi_drive", 0.0),
            "mhb": self.state.get("mhb_drive_signal", 0.0),
            "lhb": self.state.get("lhb_drive_signal", 0.0),
            "state": self.state.get("sfi_state", "quiet"),
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
            return self.state.get('sfi_state', "quiet") if 'sfi_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('sfi_drive', 0.0)) if 'sfi_drive' else 0.0
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
            "drive": self.state.get('sfi_drive', 0.0) if 'sfi_drive' else 0.0,
            "state": self.state.get('sfi_state', "quiet") if 'sfi_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

