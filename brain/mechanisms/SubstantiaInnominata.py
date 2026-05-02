"""
SubstantiaInnominata — SI / Cholinergic Cortical Modulator

NEURAL SUBSTRATE
================
The substantia innominata (SI), including the nucleus basalis of Meynert
(NBM) in primates, is the principal source of cholinergic projections to
the entire cortical mantle. SI/NBM cholinergic neurons are large,
multipolar, and degenerate selectively in Alzheimer's disease — the
historical "cholinergic hypothesis" of dementia (Bartus 1982).

Functionally, SI cholinergic activity provides a tonic cortical ACh tone
that gates attention, perception, and learning. Phasic SI activation on
salient cues drives transient ACh release, opening cortical plasticity
windows (Kilgard 1998 — pairing SI stimulation with tone reorganizes A1).

KEY FINDINGS
============
1. Substantia innominata / NBM is the primary source of cortical ACh;
   diffuse projection to entire cortical mantle —
   [Mesulam 1983, Neuroscience 10:1185, PMID 6320048]
2. NBM cholinergic neurons degenerate in Alzheimer's; cholinergic
   hypothesis of dementia —
   [Bartus 1982, Science 217:408, doi:10.1126/science.7046051]
3. Pairing NBM stimulation with auditory tone reorganizes primary
   auditory cortex; ACh enables cortical plasticity —
   [Kilgard 1998, Science 279:1714, doi:10.1126/science.279.5357.1714]
4. SI cholinergic activation drives cortical attention; phasic ACh
   release on salient cues —
   [Sarter 2009, Neuropsychopharmacology 34:36, doi:10.1038/npp.2008.92]
5. NBM optogenetic stimulation enhances perceptual learning + cortical
   gain in V1 —
   [Pinto 2013, Nat Neurosci 16:1857, doi:10.1038/nn.3552]

INPUTS
======
- LateralAmygdala.la_drive (or BasolateralAmygdala.bla_drive)
- BrainstemReticular.arousal_drive (or ArousalRegulator.tonic_level)
- ValenceTagger.valence_intensity

OUTPUTS
=======
- si_drive (0-1)
- cortical_ach_tone (0-1) — tonic
- cortical_ach_phasic (0-1) — salience-driven
- attention_gain_signal (0-1)
- plasticity_window_signal (0-1)
- si_state (str): "phasic_release" | "tonic_high" | "rest" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SubstantiaInnominata(BrainMechanism):
    """SI/NBM — cortical cholinergic modulator."""

    BASELINE = 0.10
    SMOOTH = 0.20
    PHASIC_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="SubstantiaInnominata",
            human_analog="Substantia innominata (NBM cholinergic)",
            layer="limbic",
        )
        self.state.setdefault("si_drive", self.BASELINE)
        self.state.setdefault("cortical_ach_tone", 0.0)
        self.state.setdefault("cortical_ach_phasic", 0.0)
        self.state.setdefault("attention_gain_signal", 0.0)
        self.state.setdefault("plasticity_window_signal", 0.0)
        self.state.setdefault("si_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("prev_intensity", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, la: float, arousal: float, intensity: float) -> float:
        """SI drive (Mesulam 1983)."""
        target = (self.BASELINE
                  + arousal * 0.40
                  + la * 0.25
                  + intensity * 0.20)
        return min(1.0, target)

    def _ach_tone(self, drive: float, arousal: float) -> float:
        """Tonic ACh release (Sarter 2009)."""
        return min(1.0, drive * 0.55 + arousal * 0.30)

    def _ach_phasic(self, intensity: float, prev_intensity: float,
                      la: float) -> float:
        """Phasic ACh on salience change (Sarter 2009; Pinto 2013)."""
        delta = max(0.0, intensity - prev_intensity)
        return min(1.0, delta * 1.2 + la * 0.3)

    def _attention_gain(self, tone: float, phasic: float) -> float:
        """Cortical attention gain (Sarter 2009)."""
        return min(1.0, tone * 0.5 + phasic * 0.5)

    def _plasticity_window(self, phasic: float, attention: float) -> float:
        """Plasticity-enabling ACh release (Kilgard 1998; Bartus 1982)."""
        return min(1.0, phasic * 0.6 + attention * 0.4)

    def _classify_state(self, drive: float, tone: float, phasic: float) -> str:
        if drive < 0.20:
            return "quiet"
        if phasic > self.PHASIC_THRESHOLD:
            return "phasic_release"
        if tone > 0.40:
            return "tonic_high"
        return "rest"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        la_data = prior.get("LateralAmygdala", {})
        if not la_data:
            la_data = prior.get("BasolateralAmygdala", {})
        if not la_data:
            la_data = prior.get("BasalAmygdala", {})
        la = float(la_data.get("la_drive",
                          la_data.get("bla_drive", 0.0)))

        ar_data = prior.get("ArousalRegulator", {})
        if not ar_data:
            ar_data = prior.get("BrainstemReticular", {})
        arousal = float(ar_data.get("tonic_level",
                            ar_data.get("arousal_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))

        target = self._drive_target(la, arousal, intensity)
        prev_drive = float(self.state.get("si_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        prev_intensity = float(self.state.get("prev_intensity", 0.0))
        tone = self._ach_tone(new_drive, arousal)
        phasic = self._ach_phasic(intensity, prev_intensity, la)
        attention = self._attention_gain(tone, phasic)
        plasticity = self._plasticity_window(phasic, attention)

        state = self._classify_state(new_drive, tone, phasic)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["si_drive"] = round(new_drive, 4)
        self.state["cortical_ach_tone"] = round(tone, 4)
        self.state["cortical_ach_phasic"] = round(phasic, 4)
        self.state["attention_gain_signal"] = round(attention, 4)
        self.state["plasticity_window_signal"] = round(plasticity, 4)
        self.state["prev_intensity"] = round(intensity, 4)
        self.state["si_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('si_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('si_state', "quiet") if 'si_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "si_drive": round(new_drive, 4),
            "cortical_ach_tone": round(tone, 4),
            "cortical_ach_phasic": round(phasic, 4),
            "attention_gain_signal": round(attention, 4),
            "plasticity_window_signal": round(plasticity, 4),
            "si_state": state,
        }

    def _cholinergic_health_index(self) -> float:
        """Tonic ACh integrity (degraded in dementia, Bartus 1982)."""
        return float(self.state.get("cortical_ach_tone", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("si_drive", 0.0),
            "tone": self.state.get("cortical_ach_tone", 0.0),
            "phasic": self.state.get("cortical_ach_phasic", 0.0),
            "state": self.state.get("si_state", "quiet"),
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
            return self.state.get('si_state', "quiet") if 'si_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('si_drive', 0.0)) if 'si_drive' else 0.0
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
            "drive": self.state.get('si_drive', 0.0) if 'si_drive' else 0.0,
            "state": self.state.get('si_state', "quiet") if 'si_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

