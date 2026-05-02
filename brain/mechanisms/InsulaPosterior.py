"""
InsulaPosterior -- PIC / Primary Interoceptive Cortex / Pain Awareness

NEURAL SUBSTRATE
================
Posterior insular cortex (PIC) is the primary interoceptive cortex --
the cortical destination of lamina I spinothalamic + vagal/glossopharyngeal
visceral afferents via VPL/VMpo thalamic relay. PIC encodes raw
interoceptive signals: heartbeat, breathing, GI sensation, temperature,
itch, sensual touch, pain.

Three-tier interoceptive hierarchy (Craig 2009):
- PIC = primary representation (raw)
- Mid-insula = re-representation
- AIC = meta-representation (conscious awareness)

PIC is also primary cortical pain center (sensory-discriminative pain
component, distinct from ACC pain affect). Mazzola 2009 demonstrated
direct PIC stimulation evokes pain sensations.

KEY FINDINGS
============
1. Posterior insula is primary interoceptive cortex; receives lamina I
   thalamocortical projections -- first-order body-state representation --
   [Craig 2002, Nat Rev Neurosci 3:655, doi:10.1038/nrn894]
2. Three-tier interoceptive hierarchy: PIC (primary) → mid-insula
   (re-representation) → AIC (meta-representation/awareness) --
   [Craig 2009, Nat Rev Neurosci 10:59, doi:10.1038/nrn2555]
3. Direct intracranial PIC stimulation evokes pain sensations in
   contralateral body -- primary pain cortex --
   [Mazzola 2009, Pain 146:99, doi:10.1016/j.pain.2009.07.014]
4. PIC encodes heartbeat detection accuracy at primary level; AIC
   re-represents for conscious awareness -- [Critchley 2004,
   Nat Neurosci 7:189, doi:10.1038/nn1176]
5. PIC-AIC connectivity scales interoceptive accuracy across
   individuals; trait-like -- [Khalsa 2018, Biol Psychiatry Cogn
   Neurosci Neuroimaging 3:501, doi:10.1016/j.bpsc.2017.12.004]

INPUTS
======
- VentralPosterolateralThalamus.vpl_relay (somatosensory + lamina I)
- VentralPosteromedialThalamus.vpm_relay (visceral + face)
- ParabrachialTasteVisceral.parabrachial_signal
- SpinalDorsalHornGate.ascending_nociceptive_signal (pain)
- ValenceTagger.pain_signal

OUTPUTS
=======
- pic_drive (0-1)
- raw_interoceptive_signal (0-1)
- pain_sensory_signal (0-1)
- temperature_signal (0-1)
- visceral_signal (0-1)
- pic_state (str): "pain_active" | "interoceptive_active" |
  "visceral_active" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class InsulaPosterior(BrainMechanism):
    """PIC -- primary interoceptive cortex + sensory pain."""

    BASELINE = 0.10
    SMOOTH = 0.20
    PAIN_THRESHOLD = 0.40
    INTEROCEPTIVE_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="InsulaPosterior",
            human_analog="Posterior insula (primary interoception + pain)",
            layer="limbic",
        )
        self.state.setdefault("pic_drive", self.BASELINE)
        self.state.setdefault("raw_interoceptive_signal", 0.0)
        self.state.setdefault("pain_sensory_signal", 0.0)
        self.state.setdefault("temperature_signal", 0.0)
        self.state.setdefault("visceral_signal", 0.0)
        self.state.setdefault("pic_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, vpl: float, vpm: float, parabrachial: float,
                       noci: float, pain: float) -> float:
        """PIC firing -- primary interoception + somatosensory + pain."""
        target = self.BASELINE + vpl * 0.25 + vpm * 0.20 + parabrachial * 0.20
        target += noci * 0.20 + pain * 0.15
        return min(1.0, target)

    def _raw_interoceptive(self, vpl: float, parabrachial: float,
                             vpm: float) -> float:
        """Raw interoceptive signal -- first-order body-state representation
        (Craig 2002 lamina I cortical projection).
        """
        return min(1.0, vpl * 0.4 + parabrachial * 0.4 + vpm * 0.2)

    def _pain_sensory(self, noci: float, pain: float) -> float:
        """Sensory-discriminative pain (Mazzola 2009 direct stim evokes pain)."""
        return min(1.0, noci * 0.6 + pain * 0.4)

    def _temperature_signal(self, vpl: float, parabrachial: float) -> float:
        """Temperature interoception via lamina I → VPL → PIC."""
        return min(1.0, vpl * 0.5 + parabrachial * 0.3)

    def _visceral_signal(self, parabrachial: float, vpm: float) -> float:
        """Visceral interoception (NTS → parabrachial → VPM → PIC)."""
        return min(1.0, parabrachial * 0.6 + vpm * 0.4)

    def _classify_state(self, pain: float, intero: float,
                          visceral: float) -> str:
        if pain > self.PAIN_THRESHOLD:
            return "pain_active"
        if visceral > 0.40:
            return "visceral_active"
        if intero > self.INTEROCEPTIVE_THRESHOLD:
            return "interoceptive_active"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vpl_data = prior.get("VentralPosterolateralThalamus", {})
        vpl = float(vpl_data.get("vpl_relay", 0.0))

        vpm_data = prior.get("VentralPosteromedialThalamus", {})
        vpm = float(vpm_data.get("vpm_relay", 0.0))

        pb_data = prior.get("ParabrachialTasteVisceral", {})
        parabrachial = float(pb_data.get("parabrachial_signal",
                                pb_data.get("pb_drive", 0.0)))

        sdh_data = prior.get("SpinalDorsalHornGate", {})
        noci = float(sdh_data.get("ascending_nociceptive_signal", 0.0))

        valence = prior.get("ValenceTagger", {})
        pain = float(valence.get("pain_signal",
                          valence.get("aversive_signal", 0.0)))

        target = self._drive_target(vpl, vpm, parabrachial, noci, pain)
        prev_drive = float(self.state.get("pic_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        intero = self._raw_interoceptive(vpl, parabrachial, vpm)
        pain_sens = self._pain_sensory(noci, pain)
        temp = self._temperature_signal(vpl, parabrachial)
        visceral = self._visceral_signal(parabrachial, vpm)

        state = self._classify_state(pain_sens, intero, visceral)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pic_drive"] = round(new_drive, 4)
        self.state["raw_interoceptive_signal"] = round(intero, 4)
        self.state["pain_sensory_signal"] = round(pain_sens, 4)
        self.state["temperature_signal"] = round(temp, 4)
        self.state["visceral_signal"] = round(visceral, 4)
        self.state["pic_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pic_drive": round(new_drive, 4),
            "raw_interoceptive_signal": round(intero, 4),
            "pain_sensory_signal": round(pain_sens, 4),
            "temperature_signal": round(temp, 4),
            "visceral_signal": round(visceral, 4),
            "pic_state": state,
        }

    def _heartbeat_accuracy_proxy(self, intero: float) -> float:
        """Heartbeat detection accuracy primary substrate (Critchley 2004)."""
        return intero * 0.85

    def _interoceptive_aic_relay(self, intero: float, pain: float,
                                    visceral: float) -> float:
        """Relay to AIC for conscious awareness (Craig 2009 hierarchy)."""
        return min(1.0, intero * 0.4 + pain * 0.3 + visceral * 0.3)

    def _gastric_motility_signal(self, visceral: float,
                                      intero: float) -> float:
        """Gastric motility signal -- stomach activity proxy.
        PIC receives gastric vagal afferents; high gastric motility
        suppresses appetite and drives nausea signals."""
        if visceral < 0.20 and intero < 0.20:
            return 0.0
        return min(1.0, (visceral * 0.6 + intero * 0.4))

    def _cardiac_baroreceptor_signal(self, intero: float,
                                      pain: float) -> float:
        """Cardiac baroreceptor signal -- heart rate / blood pressure
        interoceptive signal. PIC is primary cortical target for
        baroreceptor afferents (Craig 2002)."""
        if intero < 0.20:
            return 0.0
        return min(1.0, intero * 0.7 + pain * 0.2)

    def _respiratory_depth_estimate(self, intero: float) -> float:
        """Respiratory depth estimate -- slow deep breaths vs rapid shallow.
        Drives respiratory gating of cortical processing."""
        if intero < 0.15:
            return 0.0
        return min(1.0, intero * 0.8)

    def _homeostatic_deviation_index(self, pain: float,
                                      intero: float,
                                      visceral: float) -> float:
        """Homeostatic deviation -- overall deviation from baseline
        autonomic state. High values indicate allostatic load."""
        deviation = (pain + intero + visceral) / 3.0
        if deviation < 0.20:
            return 0.0
        return min(1.0, deviation * 1.5)


    def _immune_activation_signal(self, pain: float,
                                  visceral: float) -> float:
        """Immune activation signal -- PIC receives signals from
        immune system via vagal afferents (cytokine levels).
        Fever/illness activates insula."""
        if pain < 0.20 and visceral < 0.20:
            return 0.0
        return min(1.0, (pain * 0.6 + visceral * 0.4))

    def _thermal_homeostasis_signal(self, intero: float) -> float:
        """Thermal homeostasis signal -- PIC processes
        temperature afferents. High values indicate deviation
        from thermal neutrality."""
        if intero < 0.15:
            return 0.0
        return min(1.0, intero * 0.75)

    def _bladder_distension_signal(self, visceral: float) -> float:
        """Bladder distension signal -- pelvic visceral afferents
        reach PIC. Full bladder = high signal, drives attention."""
        if visceral < 0.20:
            return 0.0
        return min(1.0, visceral * 0.65)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pic_drive", 0.0),
            "intero": self.state.get("raw_interoceptive_signal", 0.0),
            "pain": self.state.get("pain_sensory_signal", 0.0),
            "state": self.state.get("pic_state", "quiet"),
        }
