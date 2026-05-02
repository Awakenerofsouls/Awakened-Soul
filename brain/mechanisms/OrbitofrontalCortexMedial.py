"""
OrbitofrontalCortexMedial — mOFC / Subjective Value & Common Currency

NEURAL SUBSTRATE
================
Medial orbitofrontal cortex (mOFC) — Brodmann areas 11, 13, 14 medial in
primates — encodes subjective value on a common currency, allowing
comparison across qualitatively different reward types (food vs. money
vs. social). Distinct from lOFC (which encodes outcome identity), mOFC
abstracts away from the sensory features and produces a value signal
that supports choice between heterogeneous options.

Padoa-Schioppa & Assad 2006 demonstrated mOFC neurons signal "offer
value" and "chosen value" on consistent linear scales independent of the
specific commodity. Levy & Glimcher 2012 (and Bartra et al. 2013
meta-analysis) established that vmPFC/mOFC tracks subjective value
across food, money, social, and other domains — a "domain-general"
value system.

mOFC sits at the convergence of viscerosensory (insula, NTS), reward
(VTA dopamine), and limbic (amygdala, vmPFC) inputs and projects to
ventral striatum, mediodorsal thalamus, and cingulate. Lesions impair
value-based decision-making (especially under risk/uncertainty) without
abolishing simple stimulus-reward associations.

KEY FINDINGS
============
1. Single OFC neurons encode economic value at choice time; signal both offered and chosen values on linear scales — [Padoa-Schioppa CA 2006, Nature 441:223, doi:10.1038/nature04676]
2. vmPFC/mOFC value signals are domain-general — same region tracks value across food, money, social rewards — [Levy DJ 2012, Curr Opin Neurobiol 22:1027, doi:10.1016/j.conb.2012.06.001]
3. Meta-analysis: mOFC + vmPFC = canonical "valuation network" in human fMRI across all reward types — [Bartra OS 2013, Neuroimage 76:412, doi:10.1016/j.neuroimage.2013.02.063]
4. mOFC encodes goal value at the time of choice; firing predicts subjective preference — [Plassmann HA 2010, J Neurosci 30:10799, doi:10.1523/JNEUROSCI.0788-10.2010]
5. Risk-sensitive valuation depends on intact mOFC; lesion produces risk-aversion specifically — [O'Neill ME 2010, J Neurosci 30:8581, doi:10.1523/JNEUROSCI.4485-09.2010]

INPUTS
======
- AnteriorInsula.aic_drive (interoceptive cost)
- NucleusAccumbensCore.nac_drive (reward signal)
- BasolateralAmygdala.bla_drive (cue-value)
- VentralTegmentalArea.da_signal (dopamine reward prediction)
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- mofc_drive (0-1)
- subjective_value_signal (0-1)
- common_currency_value (-1 to 1) — signed
- risk_sensitivity_signal (0-1)
- choice_strength_signal (0-1)
- mofc_state (str): "valuing" | "comparing" | "risky" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class OrbitofrontalCortexMedial(BrainMechanism):
    """mOFC — subjective value / common currency."""

    BASELINE = 0.10
    SMOOTH = 0.20
    VALUING_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="OrbitofrontalCortexMedial",
            human_analog="Medial orbitofrontal cortex (subjective value)",
            layer="neocortical",
        )
        self.state.setdefault("mofc_drive", self.BASELINE)
        self.state.setdefault("subjective_value_signal", 0.0)
        self.state.setdefault("common_currency_value", 0.0)
        self.state.setdefault("risk_sensitivity_signal", 0.0)
        self.state.setdefault("choice_strength_signal", 0.0)
        self.state.setdefault("mofc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("value_variance", 0.0)
        self.state.setdefault("prev_value", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ai: float, nac: float, bla: float,
                       da: float) -> float:
        """mOFC drive — convergence of value-relevant inputs (Padoa-Schioppa 2006)."""
        target = (self.BASELINE
                  + ai * 0.20
                  + nac * 0.25
                  + bla * 0.20
                  + da * 0.20)
        return min(1.0, target)

    def _subjective_value(self, drive: float, sign: int,
                            intensity: float, da: float) -> float:
        """Subjective value magnitude (Plassmann 2010)."""
        if drive < 0.20:
            return 0.0
        # Sign-agnostic magnitude
        magnitude = abs(sign) * intensity
        return min(1.0, drive * 0.4 + magnitude * 0.4 + da * 0.2)

    def _common_currency(self, value_mag: float, sign: int) -> float:
        """Signed common-currency representation (Levy 2012)."""
        # Signed: positive for appetitive, negative for aversive
        return max(-1.0, min(1.0, value_mag * sign))

    def _risk_sensitivity(self, value_var: float, value_mag: float) -> float:
        """Risk sensitivity grows with value variability (O'Neill 2010)."""
        if value_mag < 0.20:
            return 0.0
        return min(1.0, value_var * 1.5 + value_mag * 0.3)

    def _choice_strength(self, value_mag: float, drive: float) -> float:
        """How strongly choice favors the option (Padoa-Schioppa 2006)."""
        return min(1.0, value_mag * 0.7 + drive * 0.3)

    def _update_variance(self, prev_var: float, value: float,
                          prev_value: float) -> float:
        """Running variance estimate of value signal."""
        delta = abs(value - prev_value)
        return min(1.0, prev_var * 0.92 + delta * 0.20)

    def _classify_state(self, drive: float, value_mag: float,
                         risk: float) -> str:
        if drive < 0.20:
            return "quiet"
        if risk > 0.40:
            return "risky"
        if value_mag > self.VALUING_THRESHOLD:
            return "valuing"
        return "comparing"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ai_data = prior.get("InsulaAnterior", {})
        if not ai_data:
            ai_data = prior.get("AnteriorInsula", {})
        ai = float(ai_data.get("aic_drive",
                          ai_data.get("interoceptive_signal", 0.0)))

        nac_data = prior.get("NucleusAccumbensCore", {})
        if not nac_data:
            nac_data = prior.get("NucleusAccumbens", {})
        nac = float(nac_data.get("nac_drive",
                          nac_data.get("nac_reward_drive", 0.0)))

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        vta_data = prior.get("VentralTegmentalArea", {})
        if not vta_data:
            vta_data = prior.get("VTA", {})
        da = float(vta_data.get("da_signal",
                          vta_data.get("dopamine_signal", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        target = self._drive_target(ai, nac, bla, da)
        prev_drive = float(self.state.get("mofc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        value_mag = self._subjective_value(new_drive, sign, intensity, da)
        common = self._common_currency(value_mag, sign)

        prev_value = float(self.state.get("prev_value", 0.0))
        prev_var = float(self.state.get("value_variance", 0.0))
        new_var = self._update_variance(prev_var, value_mag, prev_value)

        # Risk signal carries forward between ticks — variance is a slow
        # state, and intermittent low-value ticks shouldn't reset it
        # (O'Neill 2010: risk-sensitivity is built up across trials).
        risk_target = self._risk_sensitivity(new_var, value_mag)
        prev_risk = float(self.state.get("risk_sensitivity_signal", 0.0))
        risk = max(prev_risk * 0.85, risk_target)
        choice = self._choice_strength(value_mag, new_drive)

        state = self._classify_state(new_drive, value_mag, risk)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mofc_drive"] = round(new_drive, 4)
        self.state["subjective_value_signal"] = round(value_mag, 4)
        self.state["common_currency_value"] = round(common, 4)
        self.state["risk_sensitivity_signal"] = round(risk, 4)
        self.state["choice_strength_signal"] = round(choice, 4)
        self.state["value_variance"] = round(new_var, 4)
        self.state["prev_value"] = round(value_mag, 4)
        self.state["mofc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('mofc_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('mofc_state', "quiet") if 'mofc_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "mofc_drive": round(new_drive, 4),
            "subjective_value_signal": round(value_mag, 4),
            "common_currency_value": round(common, 4),
            "risk_sensitivity_signal": round(risk, 4),
            "choice_strength_signal": round(choice, 4),
            "mofc_state": state,
        }

    def _valuation_strength(self) -> float:
        """How strongly mOFC is engaged in valuation (Bartra 2013)."""
        return float(self.state.get("subjective_value_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("mofc_drive", 0.0),
            "value": self.state.get("subjective_value_signal", 0.0),
            "common": self.state.get("common_currency_value", 0.0),
            "state": self.state.get("mofc_state", "quiet"),
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
            return self.state.get('mofc_state', "quiet") if 'mofc_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('mofc_drive', 0.0)) if 'mofc_drive' else 0.0
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
            "drive": self.state.get('mofc_drive', 0.0) if 'mofc_drive' else 0.0,
            "state": self.state.get('mofc_state', "quiet") if 'mofc_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

