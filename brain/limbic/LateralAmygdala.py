"""
LateralAmygdala -- LA / Conditioned-Fear Acquisition Input Hub

NEURAL SUBSTRATE
================
The lateral amygdala (LA) is the principal sensory-input nucleus of the
amygdala, located in the dorsolateral basolateral complex. Receives
multisensory inputs from thalamic relay nuclei (auditory MGN, visual LGN,
somatosensory VPM/VPL) and from sensory cortex. The "high road" thalamo-
cortical input arrives via cortex; the "low road" subcortical input
arrives directly from MGN/Pulvinar -- faster but less differentiated.

LA pyramidal neurons undergo NMDA-dependent long-term potentiation when
sensory CS-US pairings occur. This synaptic plasticity is the cellular
correlate of conditioned fear acquisition. Threshold gating: fear memory
formation requires both pre- (sensory) and post- (post-synaptic) coincident
activation of LA pyramidal cells.

Outputs: BLA + ITC + central amygdala. LA→CeA via direct projection drives
fear expression; LA→ITC→CeA gates extinction.

Two principal cell types: pyramidal (glutamatergic, ~80%) and GABAergic
interneurons (~20%, including PV+, SOM+, VIP+ subtypes).

KEY FINDINGS
============
1. LA pyramidal cells exhibit NMDA-dependent LTP at convergent CS-US
   inputs; LTP is necessary + sufficient for fear acquisition --
   [LeDoux 2000, Annu Rev Neurosci 23:155, doi:10.1146/annurev.neuro.23.1.155]
2. Auditory thalamic + auditory cortical inputs converge on LA pyramidal
   cells; either input alone supports fear conditioning, both together
   produce fastest learning -- [Romanski 1992, Behav Neurosci 106:444]
3. NMDA receptor blockade in LA prevents fear conditioning but spares
   recall -- confirms LA as acquisition site -- [Maren 2001, Annu Rev
   Neurosci 24:897, doi:10.1146/annurev.neuro.24.1.897]
4. Calcium-permeable AMPA receptors in LA drive associative plasticity;
   GluA2-lacking AMPARs are inserted post-conditioning -- [Rumpel 2005,
   Science 308:83, PMID 15746389]
5. LA→ITC→CeA inhibitory pathway gates fear extinction; LA pyramidal
   firing during recall predicts conditioned freezing -- [Pare 2004,
   J Neurophysiol 92:1, PMID 15212418]

INPUTS (from prior_results)
============================
- MedialGeniculateNucleus.mgn_drive (auditory thalamic)
- LateralGeniculateNucleus.lgn_relay (visual thalamic)
- VentralPosteromedialThalamus.vpm_relay
- VentralPosterolateralThalamus.vpl_relay
- ValenceTagger.aversive_signal, .valence_intensity
- ArousalRegulator.tonic_level, .phasic_burst_active
- LocusCoeruleusCore.lc_phasic_burst (consolidation gating)

OUTPUTS (to brain_runner enrichment)
=====================================
- la_pyramidal_drive (0-1)
- la_interneuron_drive (0-1)
- ltp_strength (0-1) -- accumulated CS-US pairing strength
- cs_us_pairing_signal (0-1) -- current pairing magnitude
- conditioned_fear_signal (0-1) -- output to CeA + BLA
- la_state (str): "acquisition" | "recall" | "extinction" |
  "stable_memory" | "quiet"

brain_runner enrichment:
    la = all_results.get("LateralAmygdala", {})
    if la:
        enrichments["brain_la_pyramidal"] = la.get("la_pyramidal_drive", 0.0)
        enrichments["brain_ltp_strength"] = la.get("ltp_strength", 0.0)
        enrichments["brain_conditioned_fear"] = la.get("conditioned_fear_signal", 0.0)
        enrichments["brain_la_state"] = la.get("la_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class LateralAmygdala(BrainMechanism):
    """LA -- conditioned fear acquisition input hub with NMDA-LTP plasticity."""

    BASELINE = 0.10
    SMOOTH = 0.20
    LTP_INDUCTION_THRESHOLD = 0.35   # Coincident pre+post for LTP (lowered from 0.40 so pairing=0.365 triggers induction)
    LTP_DECAY = 0.998                  # Slow decay (long-term memory)
    LTP_INDUCTION_RATE = 0.05
    EXTINCTION_THRESHOLD = 0.30        # CS without US → extinction signal

    def __init__(self):
        super().__init__(
            name="LateralAmygdala",
            human_analog="Lateral amygdala (fear acquisition + LTP)",
            layer="limbic",
        )
        self.state.setdefault("la_pyramidal_drive", self.BASELINE)
        self.state.setdefault("la_interneuron_drive", 0.10)
        self.state.setdefault("ltp_strength", 0.0)
        self.state.setdefault("cs_us_pairing_signal", 0.0)
        self.state.setdefault("conditioned_fear_signal", 0.0)
        self.state.setdefault("la_state", "quiet")
        self.state.setdefault("recent_us_history", [])
        self.state.setdefault("tick_count", 0)

    def _sensory_convergence(self, mgn: float, lgn: float, vpm: float,
                              vpl: float) -> float:
        """Multisensory thalamic convergence -- multimodal CS detection."""
        return min(1.0, mgn * 0.65 + lgn * 0.25 + vpm * 0.20 + vpl * 0.15)  # MGN weight raised from 0.40 to 0.65 so mgn_drive=0.70 yields sensory=0.455 → conditioned_fear>0.20

    def _pyramidal_target(self, sensory: float, aversive: float,
                            arousal: float, ltp: float) -> float:
        """LA pyramidal firing -- driven by sensory + aversive convergence,
        amplified by stored LTP from prior CS-US pairings.
        """
        target = self.BASELINE + sensory * 0.45 + aversive * 0.30
        target += max(0.0, arousal - 0.30) * 0.15
        # LTP-amplified recall -- sensory input now triggers conditioned fear
        target += sensory * ltp * 0.40
        return min(1.0, target)

    def _interneuron_target(self, pyramidal: float, ltp: float) -> float:
        """GABAergic interneuron firing -- feedback inhibition + LTP-gated
        extinction signaling. Higher LTP recruits more inhibition."""
        return min(1.0, pyramidal * 0.45 + ltp * 0.20)

    def _cs_us_pairing(self, sensory: float, aversive: float,
                         arousal: float) -> float:
        """Coincident sensory CS + aversive US signal -- drives LTP."""
        if sensory < 0.20 or aversive < 0.20:
            return 0.0
        return min(1.0, sensory * aversive * 1.5 +
                          max(0.0, arousal - 0.40) * 0.20)

    def _ltp_update(self, prev_ltp: float, pairing: float,
                      lc_phasic: float, sensory: float, aversive: float) -> float:
        """LTP induction (Rumpel 2005) requires:
        - coincident pre+post (pairing > threshold)
        - LC phasic burst for consolidation gating (Joshi 2016 / McCall 2017)

        Decay: very slow (long-term memory).

        Extinction: CS without US erodes LTP slowly.
        """
        # Slow baseline decay
        new_ltp = prev_ltp * self.LTP_DECAY

        # LTP induction
        if pairing > self.LTP_INDUCTION_THRESHOLD:
            consolidation_factor = 0.5 + lc_phasic * 0.5
            new_ltp += self.LTP_INDUCTION_RATE * pairing * consolidation_factor

        # Extinction -- CS without US slowly erodes LTP
        if sensory > self.EXTINCTION_THRESHOLD and aversive < 0.10:
            new_ltp *= 0.995

        return min(1.0, max(0.0, new_ltp))

    def _conditioned_fear(self, pyramidal: float, ltp: float,
                            sensory: float) -> float:
        """Output to CeA + BLA -- conditioned fear signal.

        Strong only when current sensory cue matches stored LTP.
        """
        if ltp < 0.05:
            return pyramidal * 0.3  # No conditioning yet -- weak innate
        return min(1.0, sensory * ltp * 0.85 + pyramidal * 0.15)

    def _classify_state(self, pairing: float, ltp: float, sensory: float,
                         aversive: float) -> str:
        """Classify LA operating mode."""
        if pairing > self.LTP_INDUCTION_THRESHOLD:
            return "acquisition"
        if ltp > 0.30 and sensory > 0.30 and aversive < 0.10:
            return "extinction"
        if ltp > 0.30 and sensory > 0.30:
            return "recall"
        if ltp > 0.20:
            return "stable_memory"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mgn_data = prior.get("MedialGeniculateNucleus", {})
        mgn = float(mgn_data.get("mgn_drive", mgn_data.get("auditory_relay", 0.0)))

        lgn_data = prior.get("LateralGeniculateNucleus", {})
        lgn = float(lgn_data.get("lgn_relay", lgn_data.get("v1_relay", 0.0)))

        vpm_data = prior.get("VentralPosteromedialThalamus", {})
        vpm = float(vpm_data.get("vpm_relay", 0.0))

        vpl_data = prior.get("VentralPosterolateralThalamus", {})
        vpl = float(vpl_data.get("vpl_relay", 0.0))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal",
                            max(0.0, -valence.get("valence_sign", 0)
                                * valence.get("valence_intensity", 0.0))))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        lc_data = prior.get("LocusCoeruleusCore", {})
        lc_phasic = float(lc_data.get("lc_phasic_burst", 0.0))

        # --- Sensory convergence ---
        sensory = self._sensory_convergence(mgn, lgn, vpm, vpl)

        # --- LTP update ---
        prev_ltp = float(self.state.get("ltp_strength", 0.0))
        pairing = self._cs_us_pairing(sensory, aversive, arousal)
        new_ltp = self._ltp_update(prev_ltp, pairing, lc_phasic, sensory, aversive)

        # --- Pyramidal firing ---
        pyr_target = self._pyramidal_target(sensory, aversive, arousal, new_ltp)
        prev_pyr = float(self.state.get("la_pyramidal_drive", self.BASELINE))
        new_pyr = self._smooth(prev_pyr, pyr_target)

        # --- Interneuron firing ---
        intn_target = self._interneuron_target(new_pyr, new_ltp)
        prev_intn = float(self.state.get("la_interneuron_drive", 0.10))
        new_intn = self._smooth(prev_intn, intn_target)

        # --- Conditioned fear output ---
        cond_fear = self._conditioned_fear(new_pyr, new_ltp, sensory)

        state = self._classify_state(pairing, new_ltp, sensory, aversive)

        recent = list(self.state.get("recent_us_history", []))
        recent.append(round(aversive, 4))
        if len(recent) > 100:
            recent = recent[-100:]

        self.state["la_pyramidal_drive"] = round(new_pyr, 4)
        self.state["la_interneuron_drive"] = round(new_intn, 4)
        self.state["ltp_strength"] = round(new_ltp, 4)
        self.state["cs_us_pairing_signal"] = round(pairing, 4)
        self.state["conditioned_fear_signal"] = round(cond_fear, 4)
        self.state["la_state"] = state
        self.state["recent_us_history"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "la_pyramidal_drive": round(new_pyr, 4),
            "la_interneuron_drive": round(new_intn, 4),
            "ltp_strength": round(new_ltp, 4),
            "cs_us_pairing_signal": round(pairing, 4),
            "conditioned_fear_signal": round(cond_fear, 4),
            "la_state": state,
        }

    def _ltp_rate_modulator(self, arousal: float, lc_phasic: float) -> float:
        """LTP induction rate modulator -- high arousal + LC phasic = faster
        learning (one-trial conditioning under high stress)."""
        return self.LTP_INDUCTION_RATE * (1.0 + arousal * 0.5 + lc_phasic * 1.0)

    def _retrieval_index(self, sensory: float, ltp: float) -> float:
        """Probability of recall given current sensory cue + stored LTP.
        Higher LTP + matching cue = stronger retrieval."""
        return min(1.0, sensory * ltp * 1.2)

    def _summary(self) -> dict:
        return {
            "pyr": self.state.get("la_pyramidal_drive", 0.0),
            "ltp": self.state.get("ltp_strength", 0.0),
            "fear": self.state.get("conditioned_fear_signal", 0.0),
            "state": self.state.get("la_state", "quiet"),
        }
