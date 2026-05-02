"""
CentralAmygdalaCapsular -- CeC / CeL / Fear-Input Subnucleus

NEURAL SUBSTRATE
================
The capsular subdivision of central amygdala (CeC, also "CeL" lateral
central) is the principal input subdivision of the central nucleus.
Receives BLA + LA + ITC + ascending visceral. Two genetically defined
populations:

- **CeL-on (PKCδ-) / CRH+** -- fire during threat, drive freezing via CeM
  output. Activation produces conditioned fear expression.
- **CeL-off (PKCδ+) / SOM+** -- silenced during threat. Inhibit CeL-on cells.
  Activation suppresses freezing.

This recurrent inhibitory CeL→CeL→CeM circuit gates fear expression.
Ciocchi 2010 demonstrated bidirectional optogenetic control: PKCδ-
activation produces freezing, PKCδ+ activation suppresses it.

KEY FINDINGS
============
1. CeL contains genetically defined CeL-on / CeL-off populations with
   reciprocal inhibition; gates fear expression bidirectionally --
   [Ciocchi 2010, Nature 468:277, doi:10.1038/nature09559]
2. PKCδ+ CeL neurons inhibit CeM output; their activation produces
   anxiolysis -- [Haubensak 2010, Nature 468:270, doi:10.1038/nature09553]
3. CRH+ CeL neurons drive sustained anxiety + chronic stress responses --
   [Pomrenze 2019, eLife 8:e44325, PMC6440745]
4. CeL→CeM inhibitory disinhibition is required for fear expression;
   CeM is the output, CeL the gate -- [Tovote 2015, Nat Rev Neurosci
   16:317, doi:10.1038/nrn3945]
5. SOM+ CeL neurons also encode appetitive valence; not exclusively
   fear-related -- [Yu 2017, Neuron 93:1464, PMID 28285822]

INPUTS
======
- BasolateralAmygdala.cea_drive_command (or BasalAmygdala)
- LateralAmygdala.conditioned_fear_signal
- IntercalatedCellMasses.itc_inhibition_command
- ValenceTagger.aversive_signal, .valence_intensity

OUTPUTS
=======
- cec_on_drive (0-1) -- PKCδ-/CRH+ fear-on population
- cec_off_drive (0-1) -- PKCδ+/SOM+ fear-off population
- cem_disinhibition_signal (0-1) -- net signal to CeM
- crh_release (0-1) -- CRH peptide co-release
- cec_state (str): "fear_active" | "anxiolysis" | "balanced" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class CentralAmygdalaCapsular(BrainMechanism):
    """CeC/CeL -- fear-input subnucleus with bidirectional CeL-on/CeL-off control."""

    BASELINE = 0.10
    SMOOTH = 0.20
    FEAR_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="CentralAmygdalaCapsular",
            human_analog="Central amygdala capsular/lateral (CeL fear gate)",
            layer="limbic",
        )
        self.state.setdefault("cec_on_drive", self.BASELINE)
        self.state.setdefault("cec_off_drive", self.BASELINE)
        self.state.setdefault("cem_disinhibition_signal", 0.0)
        self.state.setdefault("crh_release", 0.0)
        self.state.setdefault("cec_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _on_target(self, bla: float, la_fear: float, aversive: float,
                    off_pop: float) -> float:
        """CeL-on (PKCδ-) firing -- fear-on, mutually inhibited by CeL-off."""
        target = self.BASELINE + bla * 0.40 + la_fear * 0.25 + aversive * 0.25
        target -= off_pop * 0.30
        return min(1.0, max(0.0, target))

    def _off_target(self, itc: float, on_pop: float, appetitive: float) -> float:
        """CeL-off (PKCδ+) firing -- anxiolytic, ITC-driven, recurrent inhibits on."""
        target = self.BASELINE + itc * 0.45 + appetitive * 0.30
        target -= on_pop * 0.20
        return min(1.0, max(0.0, target))

    def _cem_disinhibition(self, on: float, off: float) -> float:
        """Net signal to CeM = on - off (Tovote 2015 disinhibition)."""
        return max(0.0, min(1.0, on - off * 0.7))

    def _crh_release(self, on: float, aversive: float) -> float:
        """CRH+ subset of CeL-on releases CRH (Pomrenze 2019)."""
        return min(1.0, on * 0.6 + aversive * 0.4)

    def _classify_state(self, on: float, off: float, disinhibition: float) -> str:
        if disinhibition > self.FEAR_THRESHOLD:
            return "fear_active"
        if off > on + 0.15 and off > 0.30:
            return "anxiolysis"
        if (on + off) > 0.30:
            return "balanced"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("cea_drive_command",
                        bla_data.get("ba_fear_neurons", 0.0)))

        la_data = prior.get("LateralAmygdala", {})
        la_fear = float(la_data.get("conditioned_fear_signal", 0.0))

        itc_data = prior.get("IntercalatedCellMasses", {})
        itc = float(itc_data.get("itc_inhibition_command", 0.0))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal",
                            max(0.0, -valence.get("valence_sign", 0)
                                * valence.get("valence_intensity", 0.0))))
        appetitive = max(0.0, valence.get("valence_sign", 0)
                          * valence.get("valence_intensity", 0.0))

        prev_on = float(self.state.get("cec_on_drive", self.BASELINE))
        prev_off = float(self.state.get("cec_off_drive", self.BASELINE))

        on_target = self._on_target(bla, la_fear, aversive, prev_off)
        off_target = self._off_target(itc, prev_on, appetitive)

        new_on = self._smooth(prev_on, on_target)
        new_off = self._smooth(prev_off, off_target)

        disinhibition = self._cem_disinhibition(new_on, new_off)
        crh = self._crh_release(new_on, aversive)

        state = self._classify_state(new_on, new_off, disinhibition)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["cec_on_drive"] = round(new_on, 4)
        self.state["cec_off_drive"] = round(new_off, 4)
        self.state["cem_disinhibition_signal"] = round(disinhibition, 4)
        self.state["crh_release"] = round(crh, 4)
        self.state["cec_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "cec_on_drive": round(new_on, 4),
            "cec_off_drive": round(new_off, 4),
            "cem_disinhibition_signal": round(disinhibition, 4),
            "crh_release": round(crh, 4),
            "cec_state": state,
        }

    def _balance_index(self, on: float, off: float) -> float:
        """Net balance -- positive = fear-on dominant, negative = fear-off dominant."""
        return max(-1.0, min(1.0, on - off))

    def _crh_chronic_streak(self, recent_states: list) -> int:
        """Count recent ticks of sustained fear_active (chronic anxiety marker)."""
        if not recent_states:
            return 0
        return sum(1 for s in recent_states[-50:] if s == "fear_active")

    def _crh_vasopressin_interaction(self, crh: float,
                                          aversive: float) -> float:
        """CRH-vasopressin interaction in CeC -- both neuropeptides
        are co-released in CeC under stress. Synergistic anxiogenic
        effect (Tovote 2015)."""
        if crh < 0.20 or aversive < 0.20:
            return 0.0
        return min(1.0, crh * aversive * 1.5)

    def _anxiety_escape_threshold(self, cec_on: float,
                                  itc: float) -> float:
        """Anxiety-escape threshold -- CeC output gating determines
        when anxiety transitions to active escape behavior. ITC
        inhibition raises threshold."""
        if cec_on < 0.20:
            return 1.0
        threshold = max(0.0, 1.0 - cec_on + itc * 0.5)
        return min(1.0, threshold)

    def _fear_potentiated_startle_proxy(self, crh: float,
                                        cec_on: float) -> float:
        """Fear-potentiated startle proxy -- CRH enhances acoustic
        startle response via CeC modulation. High CRH + CeC-on
        predicts potentiated startle."""
        if cec_on < 0.20:
            return 0.0
        return min(1.0, crh * cec_on * 1.2)

    def _extended_fear_duration(self, cec_on: float,
                                 recent_states: list) -> float:
        """Extended fear duration -- proportion of recent ticks in
        fear_active. High values suggest persistent fear state."""
        if not recent_states or cec_on < 0.20:
            return 0.0
        recent = recent_states[-30:]
        fear_ticks = sum(1 for s in recent if s == "fear_active")
        return fear_ticks / max(1, len(recent))


    def _fear_persistence_index(self, cec_on: float,
                                recent_states: list) -> float:
        """Fear persistence index -- proportion of ticks in
        fear_active state. High = persistent fear state."""
        if not recent_states or cec_on < 0.20:
            return 0.0
        recent = recent_states[-30:]
        fear_ticks = sum(1 for s in recent if s == "fear_active")
        return fear_ticks / max(1, len(recent))

    def _anxiolytic_response_predictor(self, cec_off: float,
                                        cec_on: float) -> float:
        """Anxiolytic response predictor -- CeC-off activity
        predicts positive response to benzodiazepines.
        High CeC-off / low CeC-on = anxiolytic-responsive state."""
        if cec_on > 0.30:
            return 0.0
        return min(1.0, cec_off * 0.8)

    def _sustained_anxiety_proxy(self, cec_on: float,
                                  crh: float) -> float:
        """Sustained anxiety proxy -- chronic CeC-on + CRH
        co-activation predicts sustained anxiety disorder
        vulnerability."""
        if cec_on < 0.20 or crh < 0.20:
            return 0.0
        return min(1.0, cec_on * crh * 1.2)

    def _summary(self) -> dict:
        return {
            "on": self.state.get("cec_on_drive", 0.0),
            "off": self.state.get("cec_off_drive", 0.0),
            "disinhib": self.state.get("cem_disinhibition_signal", 0.0),
            "state": self.state.get("cec_state", "quiet"),
        }
