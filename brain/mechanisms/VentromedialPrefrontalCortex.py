"""
VentromedialPrefrontalCortex — vmPFC / Self-Reference & Default Mode

NEURAL SUBSTRATE
================
Ventromedial prefrontal cortex (vmPFC) — Brodmann areas 14m, 25 (rostral
subgenual), and 32v — sits at the medial wall just dorsal to mOFC. vmPFC
is the anterior cornerstone of the default mode network (Raichle 2001),
engaged during self-referential thought, autobiographical memory
retrieval, mental simulation of others' minds, and emotion regulation.

vmPFC has dense reciprocal connectivity with hippocampus (via fornix/
cingulum), amygdala (top-down inhibition for extinction), and posterior
cingulate/precuneus. Phineas Gage's famous lesion through ventromedial
PFC produced the classic personality-and-decision-making syndrome
characterized by Damasio's somatic marker hypothesis (Damasio 1994).
Patients with vmPFC damage show impaired emotion-guided decision-making
on the Iowa Gambling Task (Bechara 1997).

vmPFC is critical for fear extinction — IL-equivalent in rodents
projects to amygdala intercalated cells which inhibit CeA fear output
(Quirk 2008, Phelps 2004). The default-mode role: vmPFC is the
prefrontal hub of internally-directed cognition that activates during
rest and deactivates during external attention demands.

KEY FINDINGS
============
1. vmPFC is the anterior hub of the default mode network; activates
   during rest + internally-directed cognition —
   [Raichle ME 2001, PNAS 98:676, doi:10.1073/pnas.98.2.676]
2. vmPFC patients show impaired emotion-guided decision-making on Iowa
   Gambling Task; somatic-marker deficit —
   [Bechara AR 1997, Science 275:1293, doi:10.1126/science.275.5304.1293]
3. vmPFC encodes self-referential processing across cultures and
   modalities — [Northoff GS 2006, Neuroimage 31:440, doi:10.1016/j.neuroimage.2005.12.002]
4. Top-down vmPFC→amygdala inhibition is critical for fear extinction
   memory retention — [Phelps EA 2004, Neuron 43:897, doi:10.1016/j.neuron.2004.08.042]
5. vmPFC integrates value with emotion regulation; reappraisal engages
   vmPFC inhibition of amygdala —
   [Etkin AM 2011, Trends Cogn Sci 15:85, doi:10.1016/j.tics.2010.11.004]

INPUTS
======
- HippocampalCA1Ventral.vca1_drive (autobiographical memory)
- BasolateralAmygdala.bla_drive (current emotion)
- PosteriorCingulateCortex.pcc_drive (default mode)
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- vmpfc_drive (0-1)
- self_reference_signal (0-1)
- emotion_regulation_signal (0-1)
- amygdala_inhibition (0-1)
- default_mode_engagement (0-1)
- vmpfc_state (str): "self_focused" | "regulating" | "default_mode" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class VentromedialPrefrontalCortex(BrainMechanism):
    """vmPFC — self-reference, emotion regulation, default mode."""

    BASELINE = 0.10
    SMOOTH = 0.20
    REGULATION_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="VentromedialPrefrontalCortex",
            human_analog="Ventromedial prefrontal cortex (default mode hub)",
            layer="neocortical",
        )
        self.state.setdefault("vmpfc_drive", self.BASELINE)
        self.state.setdefault("self_reference_signal", 0.0)
        self.state.setdefault("emotion_regulation_signal", 0.0)
        self.state.setdefault("amygdala_inhibition", 0.0)
        self.state.setdefault("default_mode_engagement", 0.0)
        self.state.setdefault("vmpfc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, hpc: float, bla: float, pcc: float,
                       external_load: float) -> float:
        """vmPFC drive — boosted by HPC + PCC, suppressed by external load."""
        target = (self.BASELINE
                  + hpc * 0.30
                  + pcc * 0.30
                  + bla * 0.15
                  - external_load * 0.20)  # default-mode anti-correlation
        return max(0.0, min(1.0, target))

    def _self_reference(self, drive: float, hpc: float, pcc: float) -> float:
        """Self-referential processing (Northoff 2006)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + hpc * 0.3 + pcc * 0.3)

    def _emotion_regulation(self, drive: float, intensity: float,
                              sign: int) -> float:
        """Emotion regulation engages with high-intensity affect (Etkin 2011)."""
        if intensity < 0.20:
            return 0.0
        # Stronger regulation needed for stronger affect, especially negative
        regulation_demand = intensity * (1.0 + (sign < 0) * 0.5)
        return min(1.0, drive * 0.4 + regulation_demand * 0.5)

    def _amygdala_inhibition(self, regulation: float, drive: float) -> float:
        """vmPFC→amygdala top-down inhibition for extinction (Phelps 2004)."""
        return min(1.0, regulation * 0.6 + drive * 0.3)

    def _default_mode(self, drive: float, external_load: float,
                       pcc: float) -> float:
        """Default mode engagement — anti-correlated with external task (Raichle 2001)."""
        if external_load > 0.50:
            return drive * 0.20
        return min(1.0, drive * 0.5 + pcc * 0.5)

    def _classify_state(self, drive: float, regulation: float,
                         self_ref: float, default: float) -> str:
        if drive < 0.20:
            return "quiet"
        if regulation > self.REGULATION_THRESHOLD:
            return "regulating"
        if self_ref > 0.40:
            return "self_focused"
        if default > 0.40:
            return "default_mode"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        hpc_data = prior.get("HippocampalCA1Ventral", {})
        if not hpc_data:
            hpc_data = prior.get("HippocampalCA1", {})
        hpc = float(hpc_data.get("vca1_drive",
                          hpc_data.get("ca1_output", 0.0)))

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        pcc_data = prior.get("CingulatePosterior", {})
        if not pcc_data:
            pcc_data = prior.get("PosteriorCingulateCortex", {})
        pcc = float(pcc_data.get("pcc_drive",
                          pcc_data.get("cingulate_drive", 0.0)))

        # External task load — taken from DLPFC if active
        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        external_load = float(dlpfc_data.get("dlpfc_drive",
                                  dlpfc_data.get("working_memory_signal", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        target = self._drive_target(hpc, bla, pcc, external_load)
        prev_drive = float(self.state.get("vmpfc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        self_ref = self._self_reference(new_drive, hpc, pcc)
        regulation = self._emotion_regulation(new_drive, intensity, sign)
        amyg_inhib = self._amygdala_inhibition(regulation, new_drive)
        default = self._default_mode(new_drive, external_load, pcc)

        state = self._classify_state(new_drive, regulation, self_ref, default)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vmpfc_drive"] = round(new_drive, 4)
        self.state["self_reference_signal"] = round(self_ref, 4)
        self.state["emotion_regulation_signal"] = round(regulation, 4)
        self.state["amygdala_inhibition"] = round(amyg_inhib, 4)
        self.state["default_mode_engagement"] = round(default, 4)
        self.state["vmpfc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('vmpfc_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('vmpfc_state', "quiet") if 'vmpfc_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "vmpfc_drive": round(new_drive, 4),
            "self_reference_signal": round(self_ref, 4),
            "emotion_regulation_signal": round(regulation, 4),
            "amygdala_inhibition": round(amyg_inhib, 4),
            "default_mode_engagement": round(default, 4),
            "vmpfc_state": state,
        }

    def _extinction_capacity(self) -> float:
        """How strongly vmPFC can drive extinction (Phelps 2004)."""
        return float(self.state.get("amygdala_inhibition", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("vmpfc_drive", 0.0),
            "self": self.state.get("self_reference_signal", 0.0),
            "regulation": self.state.get("emotion_regulation_signal", 0.0),
            "default": self.state.get("default_mode_engagement", 0.0),
            "state": self.state.get("vmpfc_state", "quiet"),
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
            return self.state.get('vmpfc_state', "quiet") if 'vmpfc_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('vmpfc_drive', 0.0)) if 'vmpfc_drive' else 0.0
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
            "drive": self.state.get('vmpfc_drive', 0.0) if 'vmpfc_drive' else 0.0,
            "state": self.state.get('vmpfc_state', "quiet") if 'vmpfc_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

