"""
OrbitofrontalCortexLateral — lOFC / Outcome Identity & Sensory-Specific Value

NEURAL SUBSTRATE
================
Lateral orbitofrontal cortex (lOFC) — Brodmann area 12/47 in primates,
medial agranular orbital cortex (LO/VO) in rodents — encodes outcome
identity rather than abstract value: which specific reward (food type,
sensory features) and its current expected utility, not the
common-currency value (handled by mOFC/vmPFC).

lOFC pyramidal neurons receive multimodal sensory input from temporal
cortex (gustatory from anterior insula; olfactory from piriform; visual
from inferotemporal) and project to BLA, ventral striatum, mediodorsal
thalamus, and back to sensory cortex. lOFC is necessary for
sensory-specific reward devaluation (eating to satiety on one food
selectively reduces motivation to work for that food but not others) —
classic Rudebeck/Murray demonstrations on rhesus.

Stalnaker 2015 reframed long-standing OFC findings: lOFC encodes the
"cognitive map" of outcome states — what specific outcome is expected
given the current cue/context, supporting model-based reinforcement
learning. Damage produces specific deficits in outcome-specific learning
without abolishing simple value-based choice.

KEY FINDINGS
============
1. Selective lOFC lesion in rhesus monkeys impairs sensory-specific
   reward devaluation; outcome-identity encoding —
   [Rudebeck PH 2013, Neuron 80:1175, doi:10.1016/j.neuron.2013.10.057]
2. OFC encodes outcome-state cognitive map; supports model-based
   inference about specific outcomes —
   [Stalnaker NM 2015, Nat Neurosci 18:620, doi:10.1038/nn.3982]
3. lOFC neurons show outcome-specific cue responses; identity not just
   value — [Walton ME 2010, Neuron 65:927, doi:10.1016/j.neuron.2010.02.027]
4. OFC encodes economic value at choice time; cells signal chosen and
   offered values — [Padoa-Schioppa CA 2006, Nature 441:223, doi:10.1038/nature04676]
5. lOFC-BLA reciprocal pathway is necessary for cue-specific reward
   expectancy updating —
   [Lichtenberg NT 2017, J Neurosci 37:8374, doi:10.1523/JNEUROSCI.0486-17.2017]

INPUTS
======
- AnteriorInsula.aic_drive (gustatory)
- PiriformLayer3.ofc_drive_signal (olfactory)
- InferotemporalCortex.it_drive (visual object)
- BasolateralAmygdala.bla_drive (cue-outcome association)
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- lofc_drive (0-1)
- outcome_identity_signal (0-1) — current outcome state estimate
- sensory_specific_value (0-1)
- bla_value_update_signal (0-1)
- devaluation_sensitivity (0-1)
- lofc_state (str): "outcome_active" | "devalued" | "expectancy" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class OrbitofrontalCortexLateral(BrainMechanism):
    """lOFC — outcome-identity / sensory-specific value cortex."""

    BASELINE = 0.10
    SMOOTH = 0.20
    OUTCOME_THRESHOLD = 0.40
    DEVALUATION_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="OrbitofrontalCortexLateral",
            human_analog="Lateral orbitofrontal cortex (outcome identity)",
            layer="neocortical",
        )
        self.state.setdefault("lofc_drive", self.BASELINE)
        self.state.setdefault("outcome_identity_signal", 0.0)
        self.state.setdefault("sensory_specific_value", 0.0)
        self.state.setdefault("bla_value_update_signal", 0.0)
        self.state.setdefault("devaluation_sensitivity", 0.0)
        self.state.setdefault("lofc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("satiety_trace", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, gust: float, olf: float, vis: float,
                      bla: float) -> float:
        """lOFC drive — multimodal sensory pooling (Rudebeck 2013)."""
        target = (self.BASELINE
                  + gust * 0.25
                  + olf * 0.20
                  + vis * 0.15
                  + bla * 0.25)
        return min(1.0, target)

    def _outcome_identity(self, drive: float, gust: float, olf: float,
                           vis: float) -> float:
        """Outcome-state cognitive map (Stalnaker 2015)."""
        # Identity signal grows with how distinct the modality-specific
        # input is — concentrated input → clearer outcome estimate.
        modality_max = max(gust, olf, vis)
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + modality_max * 0.6)

    def _sensory_specific_value(self, identity: float, sign: int,
                                  intensity: float, satiety: float) -> float:
        """Sensory-specific value — devalued by satiety (Rudebeck 2013)."""
        if identity < 0.20:
            return 0.0
        # Devaluation reduces value for the specific outcome
        base_value = identity * (0.5 + sign * intensity * 0.5)
        devalued = base_value * max(0.0, 1.0 - satiety)
        return min(1.0, max(0.0, devalued))

    def _bla_update(self, drive: float, identity: float, bla: float) -> float:
        """lOFC→BLA value-update signal (Lichtenberg 2017)."""
        return min(1.0, drive * 0.3 + identity * 0.4 + bla * 0.3)

    def _satiety_accumulator(self, prev: float, intensity: float,
                              sign: int) -> float:
        """Satiety builds with sustained appetitive consumption.

        This proxies the slow build-up that drives sensory-specific
        devaluation (Rudebeck 2013).
        """
        if sign > 0 and intensity > 0.40:
            return min(1.0, prev * 0.97 + 0.03)
        return prev * 0.92  # decay during non-consumption

    def _devaluation_sensitivity(self, satiety: float, identity: float) -> float:
        """How much current outcome is devalued."""
        if identity < 0.20:
            return 0.0
        return min(1.0, satiety * identity * 1.4)

    def _classify_state(self, drive: float, identity: float,
                         devaluation: float) -> str:
        if drive < 0.20:
            return "quiet"
        if devaluation > self.DEVALUATION_THRESHOLD:
            return "devalued"
        if identity > self.OUTCOME_THRESHOLD:
            return "outcome_active"
        return "expectancy"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        gust_data = prior.get("InsulaAnterior", {})
        if not gust_data:
            gust_data = prior.get("AnteriorInsula", {})
        gust = float(gust_data.get("aic_drive",
                          gust_data.get("gustatory_signal", 0.0)))

        olf_data = prior.get("PiriformLayer3", {})
        olf = float(olf_data.get("ofc_drive_signal",
                          olf_data.get("hedonic_signal", 0.0)))

        vis_data = prior.get("InferotemporalCortex", {})
        vis = float(vis_data.get("it_drive",
                          vis_data.get("object_signal", 0.0)))

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        target = self._drive_target(gust, olf, vis, bla)
        prev_drive = float(self.state.get("lofc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        prev_satiety = float(self.state.get("satiety_trace", 0.0))
        satiety = self._satiety_accumulator(prev_satiety, intensity, sign)

        identity = self._outcome_identity(new_drive, gust, olf, vis)
        ssv = self._sensory_specific_value(identity, sign, intensity, satiety)
        bla_upd = self._bla_update(new_drive, identity, bla)
        devaluation = self._devaluation_sensitivity(satiety, identity)

        state = self._classify_state(new_drive, identity, devaluation)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["lofc_drive"] = round(new_drive, 4)
        self.state["outcome_identity_signal"] = round(identity, 4)
        self.state["sensory_specific_value"] = round(ssv, 4)
        self.state["bla_value_update_signal"] = round(bla_upd, 4)
        self.state["devaluation_sensitivity"] = round(devaluation, 4)
        self.state["satiety_trace"] = round(satiety, 4)
        self.state["lofc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('lofc_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('lofc_state', "quiet") if 'lofc_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "lofc_drive": round(new_drive, 4),
            "ofc_drive": round(new_drive, 4),  # alias
            "outcome_identity_signal": round(identity, 4),
            "sensory_specific_value": round(ssv, 4),
            "bla_value_update_signal": round(bla_upd, 4),
            "devaluation_sensitivity": round(devaluation, 4),
            "lofc_state": state,
        }

    def _model_based_inference(self) -> float:
        """How strongly lOFC supports model-based RL (Stalnaker 2015)."""
        return float(self.state.get("outcome_identity_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("lofc_drive", 0.0),
            "identity": self.state.get("outcome_identity_signal", 0.0),
            "devaluation": self.state.get("devaluation_sensitivity", 0.0),
            "state": self.state.get("lofc_state", "quiet"),
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
            return self.state.get('lofc_state', "quiet") if 'lofc_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('lofc_drive', 0.0)) if 'lofc_drive' else 0.0
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
            "drive": self.state.get('lofc_drive', 0.0) if 'lofc_drive' else 0.0,
            "state": self.state.get('lofc_state', "quiet") if 'lofc_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

