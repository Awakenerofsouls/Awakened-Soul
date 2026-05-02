"""
ParaventricularNucleusThalamusAnterior — aPVT / Anterior Salience Hub

NEURAL SUBSTRATE
================
Anterior paraventricular nucleus of the thalamus (aPVT) is a midline
thalamic nucleus that serves as a critical hub for arousal-driven
salience processing. Distinct from posterior PVT (pPVT) which is
more aversion-biased, aPVT preferentially encodes appetitive cues and
reward expectancy. aPVT projects densely to NAc, mPFC, and BLA.

Recent work shows aPVT activity tracks reward predictions and bridges
hypothalamic homeostatic state with cortical decision-making. aPVT
neurons fire in response to reward-predictive cues (Beas 2018), gate
appetitive learning, and route hunger-state information to motivational
circuits.

KEY FINDINGS
============
1. Anterior PVT projects preferentially to NAc shell + mPFC; appetitive
   bias relative to posterior PVT —
   [Li 2008, Front Neuroanat 2:6, doi:10.3389/neuro.05.006.2008]
2. aPVT neurons encode reward-predictive cues; Bayesian prediction
   signal — [Beas 2018, Nat Neurosci 21:963, doi:10.1038/s41593-018-0167-4]
3. aPVT is a hub for hypothalamic homeostatic-state-to-cortex
   information; integrates hunger / arousal / reward —
   [Kirouac 2015, Neurosci Biobehav Rev 56:315, doi:10.1016/j.neubiorev.2015.08.005]
4. aPVT-NAc projection drives goal-directed approach; selective optical
   activation increases reward-seeking —
   [Otis 2017, Nature 543:103, doi:10.1038/nature21376]
5. aPVT activity tracks subjective value of reward; encodes incentive
   salience — [Choi 2019, Cell Rep 27:2902, doi:10.1016/j.celrep.2019.05.029]
"""

from brain.base_mechanism import BrainMechanism


class ParaventricularNucleusThalamusAnterior(BrainMechanism):
    """aPVT — anterior salience / appetitive thalamic hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    APPETITIVE_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="ParaventricularNucleusThalamusAnterior",
            human_analog="Anterior paraventricular thalamus (aPVT)",
            layer="limbic",
        )
        self.state.setdefault("apvt_drive", self.BASELINE)
        self.state.setdefault("nac_appetitive_drive", 0.0)
        self.state.setdefault("mpfc_drive", 0.0)
        self.state.setdefault("reward_prediction_signal", 0.0)
        self.state.setdefault("homeostatic_relay", 0.0)
        self.state.setdefault("apvt_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, hyp: float, ca: float, arousal: float,
                       reward_pred: float) -> float:
        """aPVT drive (Kirouac 2015)."""
        target = (self.BASELINE
                  + hyp * 0.30
                  + ca * 0.15
                  + arousal * 0.20
                  + reward_pred * 0.25)
        return min(1.0, target)

    def _nac_drive(self, drive: float, reward_pred: float) -> float:
        """aPVT→NAc shell (Otis 2017)."""
        return min(1.0, drive * 0.5 + reward_pred * 0.4)

    def _mpfc(self, drive: float, arousal: float) -> float:
        """aPVT→mPFC (Li 2008)."""
        return min(1.0, drive * 0.5 + arousal * 0.3)

    def _reward_prediction(self, drive: float, sign: int,
                            intensity: float) -> float:
        """Reward-predictive signal (Beas 2018; Choi 2019)."""
        appetitive = max(0.0, sign * intensity)
        if appetitive < 0.10:
            return 0.0
        return min(1.0, drive * 0.5 + appetitive * 0.5)

    def _homeostatic_relay(self, drive: float, hyp: float) -> float:
        """Hypothalamic-homeostatic state relay (Kirouac 2015)."""
        return min(1.0, drive * 0.4 + hyp * 0.6)

    def _classify_state(self, drive: float, reward_pred: float,
                         appetitive: float) -> str:
        if drive < 0.20:
            return "quiet"
        if reward_pred > self.APPETITIVE_THRESHOLD:
            return "reward_predictive"
        if appetitive > 0.30:
            return "appetitive"
        return "rest"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        hyp_data = prior.get("HypothalamicLateral", {})
        if not hyp_data:
            hyp_data = prior.get("LateralHypothalamus", {})
        hyp = float(hyp_data.get("lh_drive",
                          hyp_data.get("hypothalamus_drive", 0.0)))

        ca_data = prior.get("CentralAmygdala", {})
        if not ca_data:
            ca_data = prior.get("CentralAmygdalaMedial", {})
        ca = float(ca_data.get("ca_drive",
                          ca_data.get("cea_drive", 0.0)))

        ar_data = prior.get("ArousalRegulator", {})
        if not ar_data:
            ar_data = prior.get("BrainstemReticular", {})
        arousal = float(ar_data.get("tonic_level",
                            ar_data.get("arousal_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))
        appetitive = max(0.0, sign * intensity)

        prev_pred = float(self.state.get("reward_prediction_signal", 0.0))
        target = self._drive_target(hyp, ca, arousal, prev_pred)
        prev_drive = float(self.state.get("apvt_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        nac = self._nac_drive(new_drive, prev_pred)
        mpfc = self._mpfc(new_drive, arousal)
        reward_pred = self._reward_prediction(new_drive, sign, intensity)
        homeostatic = self._homeostatic_relay(new_drive, hyp)

        state = self._classify_state(new_drive, reward_pred, appetitive)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["apvt_drive"] = round(new_drive, 4)
        self.state["nac_appetitive_drive"] = round(nac, 4)
        self.state["mpfc_drive"] = round(mpfc, 4)
        self.state["reward_prediction_signal"] = round(reward_pred, 4)
        self.state["homeostatic_relay"] = round(homeostatic, 4)
        self.state["apvt_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('apvt_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('apvt_state', "quiet") if 'apvt_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "apvt_drive": round(new_drive, 4),
            "nac_appetitive_drive": round(nac, 4),
            "mpfc_drive": round(mpfc, 4),
            "reward_prediction_signal": round(reward_pred, 4),
            "homeostatic_relay": round(homeostatic, 4),
            "apvt_state": state,
        }

    def _value_tracking_strength(self) -> float:
        """Subjective value tracking (Choi 2019)."""
        return float(self.state.get("reward_prediction_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("apvt_drive", 0.0),
            "reward_pred": self.state.get("reward_prediction_signal", 0.0),
            "homeostatic": self.state.get("homeostatic_relay", 0.0),
            "state": self.state.get("apvt_state", "quiet"),
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
            return self.state.get('apvt_state', "quiet") if 'apvt_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('apvt_drive', 0.0)) if 'apvt_drive' else 0.0
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
            "drive": self.state.get('apvt_drive', 0.0) if 'apvt_drive' else 0.0,
            "state": self.state.get('apvt_state', "quiet") if 'apvt_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

