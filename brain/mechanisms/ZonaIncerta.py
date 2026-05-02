"""
ZonaIncerta — ZI / Incerto-Thalamic GABAergic Gating, Defensive Behavior

NEURAL SUBSTRATE
================
The zona incerta (ZI) is a heterogeneous, predominantly GABAergic
subthalamic nucleus situated between the thalamic reticular nucleus
dorsally and the subthalamic nucleus ventrally. It is functionally
divided into rostral, dorsal, ventral, and caudal sectors, each with
distinct neurochemistry (GABA, glutamate, somatostatin, parvalbumin)
and connectivity (Mitrofanis 2005).

ZI is described as an "integrative node for global behavioral
modulation" — it receives multimodal sensory and motor inputs and
projects broadly to higher-order thalamus (POm, MD, LP), brainstem
(PAG, SC, PPN), and cortex.

Key roles:
  - INCERTO-THALAMIC GATING: ZI GABAergic neurons inhibit higher-order
    thalamic relay nuclei, gating cortico-cortical communication
    (Trageser 2006).
  - DEFENSIVE BEHAVIOR: Rostral ZI GABAergic neurons projecting to PAG
    bidirectionally gate flight/freezing (Hormigo 2020); inhibitory
    gain modulation of defense (Zhao 2019, Nat Commun, ZI →
    central amygdala / PAG).
  - Parkinson DBS target (Ossowska 2020).

KEY FINDINGS
============
1. Review of ZI organization, connectivity, and integrative function —
   [Mitrofanis J 2005, Neuroscience 130:1, doi:10.1016/j.neuroscience.2004.08.017]
2. ZI inhibitory gain modulation of defensive behaviors via PAG/CeA —
   [Zhao ZD 2019, Nat Commun 10:951, doi:10.1038/s41467-019-08808-8]
3. ZI GABA output controls signaled locomotor avoidance via SC —
   [Hormigo S 2020, eNeuro 7:0390-19.2020, doi:10.1523/ENEURO.0390-19.2020]
4. State-dependent ZI gating of higher-order thalamic POm sensory gain —
   [Trageser JC 2006, J Neurosci 26:8911, doi:10.1523/JNEUROSCI.2419-06.2006]
5. ZI as deep-brain stimulation target in Parkinson disease and tremor —
   [Ossowska K 2020, Pharmacol Rep 72:1, doi:10.1007/s43440-019-00046-5]
6. ZI integrative node — global behavioral modulation review —
   [Wang X 2020, Trends Neurosci 43:82, doi:10.1016/j.tins.2019.11.007]

INPUTS
======
- CentralAmygdalaMedial.cea_drive (defensive context)
- PrimarySomatosensoryCortex.s1_output (multimodal sensory)
- BasalGangliaOutput.bg_signal (SNr / GPi)
- DorsalRapheNucleus.serotonin_signal (state modulation)

OUTPUTS
=======
- zi_drive (0-1) — overall ZI activity
- thalamic_gating (0-1) — incerto-thalamic POm/MD inhibition
- pag_drive (0-1) — defensive PAG control (rostral ZI)
- defensive_gain (0-1) — ZI defensive modulation index
- zi_state (str): "defensive_gate" | "thalamic_gate" | "tonic_active" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class ZonaIncerta(BrainMechanism):
    """ZI — incerto-thalamic GABA gating + defensive behavior gate."""

    BASELINE = 0.07
    NETWORK_TONIC = 0.40
    SMOOTH = 0.20
    DEFENSIVE_THRESHOLD = 0.45
    THALAMIC_THRESHOLD = 0.35
    QUIET_THRESHOLD = 0.15

    def __init__(self):
        super().__init__(
            name="ZonaIncertaBroadOutput",
            human_analog="Zona incerta (incerto-thalamic GABA, defensive gate)",
            layer="subcortical",
        )
        self.state.setdefault("zi_drive", self.BASELINE)
        self.state.setdefault("thalamic_gating", 0.0)
        self.state.setdefault("pag_drive", 0.0)
        self.state.setdefault("defensive_gain", 0.0)
        self.state.setdefault("zi_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("defensive_episodes", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, cea: float, sensory: float,
                       bg: float, ser: float) -> float:
        """ZI drive: multimodal sensory + amygdalar + BG + 5-HT
        (Mitrofanis 2005)."""
        any_input = max(cea, sensory, bg, ser)
        tonic = self.BASELINE + self.NETWORK_TONIC * any_input
        target = (tonic
                  + cea * 0.35      # CeA defensive context engages ZI
                  + sensory * 0.25  # multimodal sensory
                  + bg * 0.15       # BG output (SNr)
                  + ser * 0.10)     # 5-HT modulation
        return max(0.0, min(1.0, target))

    def _thalamic_gating(self, drive: float) -> float:
        """ZI GABA inhibits POm / MD higher-order thalamus
        (Trageser 2006)."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.85)

    def _pag_drive(self, drive: float, cea: float) -> float:
        """Rostral ZI → PAG defensive control (Hormigo 2020, Zhao 2019)."""
        # Defensive PAG drive scales with CeA-driven ZI engagement
        if cea < 0.15:
            return 0.0
        return min(1.0, drive * 0.6 + cea * 0.4)

    def _defensive_gain(self, drive: float, cea: float, pag: float) -> float:
        """ZI inhibitory gain modulation of defense (Zhao 2019)."""
        # ZI bidirectionally modulates defense — high ZI suppresses
        # excessive defense, low ZI permits flight/freeze
        return min(1.0, drive * cea * 0.8 + pag * 0.3)

    def _classify_state(self, drive: float, pag: float,
                         thal: float, cea: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if pag >= self.DEFENSIVE_THRESHOLD and cea > 0.30:
            return "defensive_gate"
        if thal >= self.THALAMIC_THRESHOLD:
            return "thalamic_gate"
        return "tonic_active"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _read_cea(self, prior: dict) -> float:
        c = prior.get("CentralAmygdalaMedial", {})
        if not c:
            c = prior.get("CentralAmygdala", {})
        if not c:
            c = prior.get("CentralAmygdalaCapsular", {})
        return float(c.get("cea_drive",
                       c.get("defensive_signal",
                          c.get("cem_drive", 0.0))))

    def _read_sensory(self, prior: dict) -> float:
        s1 = prior.get("PrimarySomatosensoryCortex", {})
        if not s1:
            s1 = prior.get("SomatosensoryS1", {})
        return float(s1.get("s1_output",
                       s1.get("somato_drive", 0.0)))

    def _read_bg(self, prior: dict) -> float:
        snr = prior.get("SubstantiaNigraReticulata", {})
        if not snr:
            snr = prior.get("GlobusPallidusInternal", {})
        return float(snr.get("snr_drive",
                       snr.get("gpi_drive",
                          snr.get("bg_signal", 0.0))))

    def _read_serotonin(self, prior: dict) -> float:
        dr = prior.get("DorsalRapheNucleus", {})
        if not dr:
            dr = prior.get("DorsalRaphe", {})
        return float(dr.get("serotonin_signal",
                       dr.get("dr_drive", 0.0)))

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cea = self._read_cea(prior)
        sensory = self._read_sensory(prior)
        bg = self._read_bg(prior)
        ser = self._read_serotonin(prior)

        target = self._drive_target(cea, sensory, bg, ser)
        prev_drive = float(self.state.get("zi_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        thal_gate = self._thalamic_gating(new_drive)
        pag = self._pag_drive(new_drive, cea)
        gain = self._defensive_gain(new_drive, cea, pag)

        state = self._classify_state(new_drive, pag, thal_gate, cea)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        episodes = int(self.state.get("defensive_episodes", 0))
        if state == "defensive_gate":
            episodes += 1

        self.state["zi_drive"] = round(new_drive, 4)
        self.state["thalamic_gating"] = round(thal_gate, 4)
        self.state["pag_drive"] = round(pag, 4)
        self.state["defensive_gain"] = round(gain, 4)
        self.state["zi_state"] = state
        self.state["recent_states"] = recent
        self.state["defensive_episodes"] = episodes
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('zi_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('zi_state', "quiet") if 'zi_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "zi_drive": round(new_drive, 4),
            "thalamic_gating": round(thal_gate, 4),
            "pag_drive": round(pag, 4),
            "defensive_gain": round(gain, 4),
            "zi_state": state,
        }

    def _defensive_rate(self) -> float:
        """Defensive engagement proxy (Zhao 2019)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return self.state.get("defensive_episodes", 0) / ticks

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("zi_drive", 0.0),
            "thal": self.state.get("thalamic_gating", 0.0),
            "pag": self.state.get("pag_drive", 0.0),
            "gain": self.state.get("defensive_gain", 0.0),
            "state": self.state.get("zi_state", "quiet"),
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
            return self.state.get('zi_state', "quiet") if 'zi_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('zi_drive', 0.0)) if 'zi_drive' else 0.0
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
            "drive": self.state.get('zi_drive', 0.0) if 'zi_drive' else 0.0,
            "state": self.state.get('zi_state', "quiet") if 'zi_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

