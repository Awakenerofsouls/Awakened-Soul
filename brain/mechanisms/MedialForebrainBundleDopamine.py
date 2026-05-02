"""
MedialForebrainBundleDopamine — MFB / Reward Bundle / VTA→Forebrain DA Conduit

NEURAL SUBSTRATE
================
The medial forebrain bundle (MFB) is the principal axonal highway
linking ventral tegmental area (VTA) dopaminergic neurons with their
forebrain targets — nucleus accumbens, ventral pallidum, prefrontal
cortex, amygdala, and bed nucleus of stria terminalis. It also carries
hypothalamic outputs (orexin, MCH, NPY) and lateral-hypothalamic
self-stimulation fibers that Olds & Milner 1954 discovered as the
most potent reward substrate in the brain.

Key insight from Wise 2008 review: MFB-supported intracranial
self-stimulation does not directly fire DA neurons — it activates
descending myelinated non-DA axons that secondarily recruit DA
release. The dopamine reward signal is downstream of, not identical
to, the bundle's primary signaling axis.

Anatomically the MFB has three principal directions:
- Ascending: VTA DA → NAc/PFC/amygdala (mesolimbic + mesocortical)
- Descending: lateral hypothalamic glutamate + GABA → VTA, PAG
- Recurrent: NAc/VP → VTA via accumbo-pallido-tegmental loop

Coenen 2018 + Schlaepfer 2013 used MFB deep brain stimulation to
treat refractory depression — DBS at supero-lateral MFB produced
sustained mood elevation, demonstrating clinically that the bundle
is a rate-limiting substrate of motivated/hedonic state.

KEY FINDINGS
============
1. Olds & Milner discovery: intracranial self-stimulation at lateral hypothalamic MFB is the most potent reward substrate; rats lever-press until exhaustion — [Olds J 1954, J Comp Physiol Psychol 47:419, doi:10.1037/h0058775]
2. MFB stimulation activates descending non-DA axons; DA recruited secondarily, not directly fired by stimulation — [Wise RA 2008, Neurotox Res 14:169, doi:10.1007/BF03033808]
3. Forebrain reward substrates: MFB carries DA + non-DA fibers connecting hypothalamic reward sites to forebrain motivation circuits — [Kringelbach ML 2008, Front Behav Neurosci 2:6, doi:10.3389/neuro.08.006.2008]
4. Supero-lateral MFB DBS produces rapid + sustained antidepressant effect in treatment-resistant depression — [Schlaepfer TE 2013, Biol Psychiatry 73:1204, doi:10.1016/j.biopsych.2013.01.034]
5. Convergence model of reward circuitry: MFB-DBS efficacy reveals integrative role of bundle for motivation + hedonic state — [Coenen VA 2018, Front Behav Neurosci 12:206, doi:10.3389/fnbeh.2018.00206]

INPUTS (from prior_results)
============================
- VentralTegmentalDopamine.da_release (or SubstantiaNigraCompacta.snc_drive)
- HypothalamicLateral.lh_drive (or LateralHypothalamus)
- NucleusAccumbensCore.nacc_drive
- BasolateralAmygdala.bla_drive
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS (to brain_runner enrichment)
=====================================
- mfb_drive (0-1)
- ascending_da_signal (0-1) — VTA → forebrain
- descending_motivation_signal (0-1) — LH → midbrain
- mesocortical_drive (0-1) — VTA → PFC
- mesolimbic_drive (0-1) — VTA → NAc
- self_stimulation_proxy (0-1) — Olds-Milner reward strength index
- mfb_state (str): "ascending_dominant" | "descending_dominant" |
  "balanced_reward" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class MedialForebrainBundleDopamine(BrainMechanism):
    """MFB — VTA-forebrain dopamine + lateral hypothalamic reward bundle."""

    BASELINE = 0.10
    SMOOTH = 0.20
    REWARD_THRESHOLD = 0.45

    def __init__(self):
        super().__init__(
            name="MedialForebrainBundleDopamineVariant",
            human_analog="Medial forebrain bundle (reward conduit)",
            layer="integration",
        )
        self.state.setdefault("mfb_drive", self.BASELINE)
        self.state.setdefault("ascending_da_signal", 0.0)
        self.state.setdefault("descending_motivation_signal", 0.0)
        self.state.setdefault("mesocortical_drive", 0.0)
        self.state.setdefault("mesolimbic_drive", 0.0)
        self.state.setdefault("self_stimulation_proxy", 0.0)
        self.state.setdefault("mfb_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _ascending_da(self, vta: float, valence_appetitive: float) -> float:
        """Ascending VTA→forebrain DA fibers (Wise 2008). DA carried
        upward, modulated by current appetitive valence."""
        return min(1.0, vta * 0.6 + valence_appetitive * 0.3)

    def _descending(self, lh: float, nacc: float, valence: float) -> float:
        """Descending LH + NAc → VTA fibers (Wise 2008 — these are the
        non-DA fibers actually activated by self-stimulation)."""
        return min(1.0, lh * 0.5 + nacc * 0.3 + valence * 0.2)

    def _mesocortical(self, ascending: float, pfc_demand: float) -> float:
        """VTA → PFC mesocortical branch. Stronger when PFC requires
        cognitive engagement."""
        return min(1.0, ascending * 0.6 + pfc_demand * 0.3)

    def _mesolimbic(self, ascending: float, nacc: float) -> float:
        """VTA → NAc mesolimbic branch. Standard reward pathway."""
        return min(1.0, ascending * 0.6 + nacc * 0.4)

    def _self_stim_proxy(self, descending: float, ascending: float,
                          appetitive: float) -> float:
        """Olds-Milner reward strength — primarily descending non-DA
        bundle activation × current appetitive context (Wise 2008
        showed MFB self-stim works through descending fibers)."""
        if descending < 0.15:
            return 0.0
        return min(1.0, descending * 0.5 + ascending * 0.3 + appetitive * 0.2)

    def _drive_target(self, ascending: float, descending: float,
                       arousal: float) -> float:
        """Aggregate MFB drive."""
        return min(1.0, self.BASELINE + ascending * 0.4 + descending * 0.4
                      + arousal * 0.10)

    def _classify_state(self, drive: float, ascending: float,
                          descending: float, self_stim: float) -> str:
        if drive < 0.20:
            return "quiet"
        if self_stim > self.REWARD_THRESHOLD:
            return "balanced_reward"
        if ascending > descending + 0.20:
            return "ascending_dominant"
        if descending > ascending + 0.20:
            return "descending_dominant"
        return "balanced_reward"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vta_data = prior.get("VentralTegmentalDopamine", {})
        if not vta_data:
            vta_data = prior.get("SubstantiaNigraCompacta", {})
        vta = float(vta_data.get("da_release",
                          vta_data.get("snc_drive",
                            vta_data.get("da_signal", 0.0))))

        lh_data = prior.get("HypothalamicLateral", {})
        if not lh_data:
            lh_data = prior.get("LateralHypothalamus", {})
        lh = float(lh_data.get("lh_drive",
                          lh_data.get("hypothalamus_drive", 0.0)))

        nacc_data = prior.get("NucleusAccumbensCore", {})
        nacc = float(nacc_data.get("nacc_drive",
                            nacc_data.get("nac_drive", 0.0)))

        bla_data = prior.get("BasolateralAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))
        appetitive = max(0.0, sign * intensity)

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level", 0.30))

        pfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        pfc_demand = float(pfc_data.get("dlpfc_drive", 0.0))

        ascending = self._ascending_da(vta, appetitive)
        descending = self._descending(lh, nacc, intensity)
        target = self._drive_target(ascending, descending, arousal)
        prev_drive = float(self.state.get("mfb_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        mesocortical = self._mesocortical(ascending, pfc_demand)
        mesolimbic = self._mesolimbic(ascending, nacc)
        self_stim = self._self_stim_proxy(descending, ascending, appetitive)

        state = self._classify_state(new_drive, ascending, descending,
                                       self_stim)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mfb_drive"] = round(new_drive, 4)
        self.state["ascending_da_signal"] = round(ascending, 4)
        self.state["descending_motivation_signal"] = round(descending, 4)
        self.state["mesocortical_drive"] = round(mesocortical, 4)
        self.state["mesolimbic_drive"] = round(mesolimbic, 4)
        self.state["self_stimulation_proxy"] = round(self_stim, 4)
        self.state["mfb_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mfb_drive": round(new_drive, 4),
            "ascending_da_signal": round(ascending, 4),
            "descending_motivation_signal": round(descending, 4),
            "mesocortical_drive": round(mesocortical, 4),
            "mesolimbic_drive": round(mesolimbic, 4),
            "self_stimulation_proxy": round(self_stim, 4),
            "mfb_state": state,
        }

    def _antidepressant_signature(self) -> float:
        """Sustained balanced MFB drive = MFB-DBS antidepressant
        signature (Schlaepfer 2013, Coenen 2018)."""
        return float(self.state.get("self_stimulation_proxy", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("mfb_drive", 0.0),
            "ascending": self.state.get("ascending_da_signal", 0.0),
            "descending": self.state.get("descending_motivation_signal", 0.0),
            "self_stim": self.state.get("self_stimulation_proxy", 0.0),
            "state": self.state.get("mfb_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
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
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
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

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

