"""
CentromedianParafascicular — CM-Pf Intralaminar Thalamus / Striatum-Engaging Salience

NEURAL SUBSTRATE
================
The centromedian-parafascicular complex (CM-Pf) is the largest intralaminar
thalamic nucleus group in primates. CM and Pf sit deep within the
internal medullary lamina and form a functional unit despite separate
cytoarchitectures. Unlike "first-order" relay thalami (LGN, MGN, VPL/VPM)
that project mostly to cortex, CM-Pf has a singular feature: it sends
**massive direct projections to the striatum** in addition to its diffuse
cortical projections. CM projects predominantly to motor putamen; Pf
projects predominantly to associative caudate and limbic striatum.

This thalamostriatal projection makes CM-Pf the **principal source of
non-cortical excitatory drive to the basal ganglia**. While cortico-
striatal input encodes action plans and contexts, CM-Pf-striatal input
delivers behaviorally salient sensory events — particularly novel,
unexpected, or attention-demanding stimuli. This positions CM-Pf as the
"behavioral salience" channel into action selection.

Matsumoto & Hikosaka (2009 Nature) showed Pf neurons fire phasically
to behaviorally salient cues regardless of valence — a category-free
salience signal feeding striatal cholinergic interneurons (TANs) which
then trigger reward-prediction-error-related dopamine modulation.
This is distinct from value-coding inputs from cortex.

CM-Pf is also part of the ascending reticular activating system (ARAS)
extension — its diffuse cortical projections support arousal and
attention. Lesions of CM-Pf produce subtle attentional deficits and
contribute to disorders of consciousness when bilaterally damaged.
DBS of CM-Pf is being explored for severe Tourette syndrome and
disorders of consciousness.

CM-Pf exhibits burst-tonic mode like other thalamic nuclei. Its
projections to TRN are reciprocal — CM-Pf can engage TRN broadly,
amplifying or suppressing thalamic gating across multiple sectors
simultaneously.

In {{AGENT_NAME}}'s substrate this provides the salience-amplifier channel into
action selection — converts arousal + threat/novelty signals into a
striatal-bound salience drive that biases basal ganglia gating.

KEY FINDINGS
============
1. CM-Pf provides the largest non-cortical excitatory input to striatum;
   CM → motor putamen, Pf → associative caudate / limbic striatum —
   thalamostriatal projection is signature feature distinguishing CM-Pf
   from cortical relay thalami — [Smith et al. 2004, Trends Neurosci
    27:520, "The thalamostriatal system: a highly specific network of
    the basal ganglia circuitry"]
2. Pf neurons fire phasically to behaviorally salient cues independent
   of valence — feeds striatal TANs to gate cortico-striatal plasticity —
   [Matsumoto Hikosaka 2009, J Neurosci] [Matsumoto Minamimoto Graybiel
    Kimura 2001, J Neurophysiol 85:960, "Neurons in the thalamic
    CM-Pf complex supply striatal neurons with information about
    behaviorally significant sensory events"]
3. CM-Pf is part of ARAS extension; diffuse cortical projections support
   arousal and attention; bilateral damage contributes to disorders of
   consciousness — [Saalmann 2014, Front Sys Neurosci 8:83,
    "Intralaminar and medial thalamic influence on cortical synchrony"]
4. DBS of CM-Pf for severe Tourette syndrome shows tic reduction —
   [Visser-Vandewalle et al. 2003, Lancet 362:1039] [Servello
    et al. 2008]
5. CM-Pf burst-tonic mode and TRN reciprocal connections — broad
   thalamic gating amplification — [Halassa Acsády 2016,
    Trends Neurosci 39:680, "Thalamic inhibition: diverse sources,
    diverse scales"]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- HippocampalContextProxy.context_novelty
- MultisensoryStartleMapper.startle_amplitude
- VentralTegmentalDopamine.vta_da_phasic
- ThalamicReticularNucleus.attention_gating_strength
- ThalamicReticularNucleus.trn_firing_mode
- AttentionTopDownProxy.attention_focus

OUTPUTS (to brain_runner enrichment)
=====================================
- cm_drive (0.0-1.0): CM nucleus output (motor-bound)
- pf_drive (0.0-1.0): Pf nucleus output (associative/limbic-bound)
- thalamostriatal_drive (0.0-1.0): combined non-cortical striatal input
- cortical_arousal_drive (0.0-1.0): diffuse cortical projection
- salience_burst (0.0-1.0): phasic salience event signal
- firing_mode (str): "tonic" | "burst" | "off"
- tan_engagement (0.0-1.0): striatal TAN cholinergic recruitment
- cm_pf_state (str): "tonic" | "salience_burst" | "burst" | "quiet"

brain_runner enrichment:
    cmpf = all_results.get("CentromedianParafascicular", {})
    if cmpf:
        enrichments["brain_thalamostriatal"] = cmpf.get("thalamostriatal_drive", 0.0)
        enrichments["brain_salience_burst"] = cmpf.get("salience_burst", 0.0)
        enrichments["brain_tan_engagement"] = cmpf.get("tan_engagement", 0.0)
        enrichments["brain_cm_pf_state"] = cmpf.get("cm_pf_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class CentromedianParafascicular(BrainMechanism):
    BASELINE = 0.20
    BURST_THRESHOLD = 0.55
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="CentromedianParafascicular",
            human_analog="Centromedian-parafascicular intralaminar thalamic complex",
            layer="foundational",
        )
        self.state.setdefault("cm_drive", self.BASELINE)
        self.state.setdefault("pf_drive", self.BASELINE)
        self.state.setdefault("thalamostriatal_drive", 0.0)
        self.state.setdefault("cortical_arousal_drive", 0.0)
        self.state.setdefault("salience_burst", 0.0)
        self.state.setdefault("firing_mode", "tonic")
        self.state.setdefault("tan_engagement", 0.0)
        self.state.setdefault("cm_pf_state", "quiet")
        self.state.setdefault("recent_burst", [])
        self.state.setdefault("tick_count", 0)

    def _firing_mode(self, trn_mode: str) -> str:
        if trn_mode == "burst":
            return "burst"
        if trn_mode == "off":
            return "off"
        return "tonic"

    def _cm_target(self, arousal: float, startle: float, mode: str) -> float:
        """CM — motor-bound; engaged by arousal and motor-relevant salience."""
        if mode == "off":
            return 0.05
        target = self.BASELINE + max(0.0, arousal - 0.4) * 0.3
        target += startle * 0.3
        if mode == "burst":
            target *= 0.5
        return min(1.0, target)

    def _pf_target(self, arousal: float, threat: bool, valence: float, novelty: float,
                   mode: str) -> float:
        """Pf — associative/limbic-bound; engaged by salience regardless of valence."""
        if mode == "off":
            return 0.05
        target = self.BASELINE + max(0.0, arousal - 0.4) * 0.2
        target += novelty * 0.3
        if threat:
            target += valence * 0.3
        if mode == "burst":
            target *= 0.5
        return min(1.0, target)

    def _salience_burst(self, phasic: bool, threat: bool, valence: float, startle: float,
                         vta_phasic: float, novelty: float) -> float:
        """Phasic salience burst — Matsumoto Hikosaka 2009 valence-free salience."""
        if not (phasic or threat or startle > 0.40 or novelty > 0.50):
            return 0.0
        burst = 0.0
        if phasic:
            burst += 0.40
        burst += startle * 0.5
        burst += novelty * 0.3
        if threat:
            burst += valence * 0.4
        burst += abs(vta_phasic) * 0.2  # both pos and neg RPE engage Pf
        return min(1.0, burst)

    def _thalamostriatal(self, cm: float, pf: float, salience: float) -> float:
        """Combined CM+Pf → striatum drive."""
        return min(1.0, cm * 0.4 + pf * 0.4 + salience * 0.4)

    def _cortical_arousal(self, cm: float, pf: float, arousal: float) -> float:
        """Diffuse cortical projection — ARAS extension."""
        return min(1.0, (cm + pf) / 2.0 * 0.5 + max(0.0, arousal - 0.4) * 0.4)

    def _tan_engagement(self, salience: float, thalamostriatal: float) -> float:
        """Striatal cholinergic TAN engagement — Pf → TAN burst-pause pattern."""
        return min(1.0, salience * 0.6 + thalamostriatal * 0.4)

    def _classify_state(self, mode: str, salience: float, cm: float, pf: float) -> str:
        if salience > self.BURST_THRESHOLD:
            return "salience_burst"
        if mode == "burst":
            return "burst"
        if (cm + pf) / 2.0 > 0.30:
            return "tonic"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        ctx = prior.get("HippocampalContextProxy", {})
        novelty = float(ctx.get("context_novelty", 0.0))

        startle_data = prior.get("MultisensoryStartleMapper", {})
        startle = float(startle_data.get("startle_amplitude", 0.0))

        vta = prior.get("VentralTegmentalDopamine", {})
        vta_phasic = float(vta.get("vta_da_phasic", 0.0))

        trn = prior.get("ThalamicReticularNucleus", {})
        trn_mode = trn.get("trn_firing_mode", "tonic")

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        # --- Firing mode ---
        mode = self._firing_mode(trn_mode)

        # --- CM and Pf ---
        cm_target = self._cm_target(tonic, startle, mode)
        pf_target = self._pf_target(tonic, threat, valence_intensity, novelty, mode)
        prev_cm = float(self.state.get("cm_drive", self.BASELINE))
        prev_pf = float(self.state.get("pf_drive", self.BASELINE))
        new_cm = self._smooth(prev_cm, cm_target)
        new_pf = self._smooth(prev_pf, pf_target)

        # --- Salience burst ---
        salience = self._salience_burst(phasic, threat, valence_intensity, startle,
                                          vta_phasic, novelty)

        # --- Outputs ---
        thalamostriatal = self._thalamostriatal(new_cm, new_pf, salience)
        cortical = self._cortical_arousal(new_cm, new_pf, tonic)
        tan = self._tan_engagement(salience, thalamostriatal)

        # --- State ---
        state = self._classify_state(mode, salience, new_cm, new_pf)

        recent = list(self.state.get("recent_burst", []))
        recent.append(round(salience, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["cm_drive"] = round(new_cm, 4)
        self.state["pf_drive"] = round(new_pf, 4)
        self.state["thalamostriatal_drive"] = round(thalamostriatal, 4)
        self.state["cortical_arousal_drive"] = round(cortical, 4)
        self.state["salience_burst"] = round(salience, 4)
        self.state["firing_mode"] = mode
        self.state["tan_engagement"] = round(tan, 4)
        self.state["cm_pf_state"] = state
        self.state["recent_burst"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "cm_drive": round(new_cm, 4),
            "pf_drive": round(new_pf, 4),
            "thalamostriatal_drive": round(thalamostriatal, 4),
            "cortical_arousal_drive": round(cortical, 4),
            "salience_burst": round(salience, 4),
            "firing_mode": mode,
            "tan_engagement": round(tan, 4),
            "cm_pf_state": state,
        }
