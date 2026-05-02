"""
BotzingerExpiratory — BötC Expiratory Rhythm (Pair to preBötC Inspiratory)

NEURAL SUBSTRATE
================
The Bötzinger complex (BötC) is a ventrolateral medullary respiratory
group sitting just rostral to the pre-Bötzinger complex (preBötC,
covered separately). While preBötC generates the inspiratory rhythm,
BötC contains primarily **glycinergic and GABAergic inhibitory
neurons** that fire during expiration and suppress inspiratory
populations through inhibition. The reciprocal interaction between
BötC inhibition and preBötC excitation is fundamental to respiratory
phase switching — BötC's expiratory phase tonically inhibits preBötC,
which is released to fire during inspiration when BötC inhibition
fades.

The Smith/Feldman/Richter framework places BötC, preBötC, and the
caudal/rostral ventral respiratory groups (cVRG, rVRG) in a longitudinal
column along the ventrolateral medulla — the ventral respiratory column
(VRC) — that generates and shapes the three-phase respiratory cycle:
inspiration → post-inspiration → late expiration. BötC neurons fire
predominantly during late expiration (E2 phase), producing
post-inspiratory and stage-2 expiratory inhibition.

Two principal BötC neuron classes have been identified: post-inspiratory
(post-I) cells and augmenting-expiratory (aug-E) cells. Post-I cells
fire at the inspiration-to-expiration transition and are critical for
proper turnover. Aug-E cells fire with progressively increasing rate
during expiration and contribute to active expiration when ventilatory
demand rises.

BötC inhibition of preBötC and other VRC populations shapes the
respiratory pattern — without functional BötC inhibition, breathing
becomes irregular and gasping-like. BötC also receives modulation from
chemoreceptors (via RTN/pFRG and via NTS), enabling expiratory pattern
adaptation to metabolic demand.

In the agent's substrate this provides the expiratory-phase respiratory
inhibition channel — pairs with PreBotzingerInspiration to produce
proper inhalation-exhalation phase turnover, with augmenting expiratory
output during high ventilatory demand.

KEY FINDINGS
============
1. BötC contains primarily glycinergic/GABAergic inhibitory neurons
   that fire during expiration and inhibit inspiratory populations —
   reciprocal inhibition produces phase switching — [Smith Abdala
    Borgmann Rybak Paton 2013, Trends Neurosci 36:152, "Brainstem
    respiratory networks: building blocks and microcircuits"]
2. BötC contains post-inspiratory (post-I) and augmenting-expiratory
   (aug-E) neuron classes with distinct firing patterns across
   expiration — [reviewed Anderson et al. 2016, Nat Neurosci 19:1356,
    "A novel excitatory network for the control of breathing"]
3. BötC, preBötC, cVRG, rVRG together form the ventral respiratory
   column generating the three-phase respiratory cycle — [reviewed
    Feldman et al. 2003, Annu Rev Neurosci 26:239, "Breathing:
    rhythmicity, plasticity, chemosensitivity"]
4. Glycinergic inhibition from BötC is required for proper respiratory
   pattern; loss produces irregular gasping breathing — [Schreihofer
    Stornetta Guyenet 1999 J Physiol; reviewed Richter Smith 2014
    Annu Rev Physiol 76:347]
5. Active expiration recruited under high ventilatory demand depends
   on aug-E neurons of BötC and parafacial respiratory group — [Pagliardini
    et al. 2011 J Neurosci 31:2895; reviewed Del Negro Funk Feldman
    2018 Nat Rev Neurosci 19:351]

INPUTS (from prior_results)
============================
- PreBotzingerInspiration.inspiratory_rhythm
- PreBotzingerInspiration.inspiration_burst_active
- PreBotzingerInspiration.respiratory_rate_proxy
- VitalCoreRegulator.vital_drive
- CarotidBodyChemosensor.hypercapnia_response
- CarotidBodyChemosensor.hypoxia_response_active
- ArousalRegulator.tonic_level
- ValenceTagger.threat_signal

OUTPUTS (to brain_runner enrichment)
=====================================
- botc_drive (0.0-1.0): overall BötC inhibitory output
- post_i_drive (0.0-1.0): post-inspiratory cell drive
- aug_e_drive (0.0-1.0): augmenting expiratory cell drive
- expiratory_inhibition (0.0-1.0): inhibition of inspiratory populations
- active_expiration_engaged (bool): aug-E recruitment beyond baseline
- phase_marker (str): "post_inspiratory" | "stage_2_expiratory" | "expiratory_silent" | "inspiration"
- botc_state (str): "tonic_expiratory" | "active_expiration" | "irregular" | "quiet"

brain_runner enrichment:
    botc = all_results.get("BotzingerExpiratory", {})
    if botc:
        enrichments["brain_botc_drive"] = botc.get("botc_drive", 0.2)
        enrichments["brain_expiratory_inhibition"] = botc.get("expiratory_inhibition", 0.0)
        enrichments["brain_active_expiration"] = botc.get("active_expiration_engaged", False)
        enrichments["brain_botc_state"] = botc.get("botc_state", "tonic_expiratory")
"""

from brain.base_mechanism import BrainMechanism


class BotzingerExpiratory(BrainMechanism):
    BASELINE = 0.30
    ACTIVE_EXP_THRESHOLD = 0.55
    SMOOTH = 0.30

    def __init__(self):
        super().__init__(
            name="BotzingerExpiratory",
            human_analog="Bötzinger complex expiratory rhythm (post-I + aug-E)",
            layer="foundational",
        )
        self.state.setdefault("botc_drive", self.BASELINE)
        self.state.setdefault("post_i_drive", 0.20)
        self.state.setdefault("aug_e_drive", 0.20)
        self.state.setdefault("expiratory_inhibition", 0.0)
        self.state.setdefault("active_expiration_engaged", False)
        self.state.setdefault("phase_marker", "expiratory_silent")
        self.state.setdefault("botc_state", "tonic_expiratory")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _botc_drive_target(self, inspiration: bool, rate: float, hypercapnia: float,
                            arousal: float, threat: bool) -> float:
        """BötC overall drive — high during expiration, modulated by demand."""
        if inspiration:
            # Inspiration phase — BötC is inhibited (reciprocal)
            return self.BASELINE * 0.4
        # Expiration phase — base + demand modulation
        target = self.BASELINE + 0.20  # base expiratory drive
        target += hypercapnia * 0.3
        target += max(0.0, arousal - 0.5) * 0.1
        if threat:
            target += 0.10
        if rate > 0.65:
            target += 0.10
        return min(1.0, target)

    def _post_i_target(self, inspiration: bool, rhythm: float) -> float:
        """Post-inspiratory cells fire at I→E transition.
        Engaged at end of inspiration / start of expiration.
        """
        # rhythm > 0.4 means we're past inspiration peak, in transition
        if not inspiration and rhythm > 0.20:
            return 0.0  # still in mid expiration, post-I has fallen
        if inspiration and rhythm > 0.50:
            # End of inspiration approaches — post-I rising
            return 0.60
        if not inspiration and rhythm < 0.15:
            # Just transitioned — post-I peak
            return 0.85
        return 0.20

    def _aug_e_target(self, inspiration: bool, rhythm: float, demand: float) -> float:
        """Augmenting expiratory — rising rate during expiration."""
        if inspiration:
            return 0.10  # silent during inspiration
        # During expiration, ramps with demand
        if demand > 0.60:
            return min(1.0, 0.40 + demand * 0.5)
        return 0.20 + demand * 0.3

    def _expiratory_inhibition(self, botc: float, post_i: float, aug_e: float) -> float:
        """Net inhibition of inspiratory populations from BötC."""
        return min(1.0, botc * 0.5 + post_i * 0.3 + aug_e * 0.2)

    def _phase_marker(self, inspiration: bool, post_i: float, aug_e: float) -> str:
        if inspiration:
            return "inspiration"
        if post_i > 0.55:
            return "post_inspiratory"
        if aug_e > 0.50:
            return "stage_2_expiratory"
        return "expiratory_silent"

    def _classify_state(self, active_exp: bool, irregular_proxy: bool, botc: float) -> str:
        if irregular_proxy:
            return "irregular"
        if active_exp:
            return "active_expiration"
        if botc > 0.40:
            return "tonic_expiratory"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        prebotc = prior.get("PreBotzingerInspiration", {})
        rhythm = float(prebotc.get("inspiratory_rhythm", 0.0))
        inspiration = bool(prebotc.get("inspiration_burst_active", False))
        rate = float(prebotc.get("respiratory_rate_proxy", 0.50))

        vcr = prior.get("VitalCoreRegulator", {})
        vital = float(vcr.get("vital_drive", 0.50))

        cb = prior.get("CarotidBodyChemosensor", {})
        hypercapnia = float(cb.get("hypercapnia_response", 0.0))
        hypoxia = bool(cb.get("hypoxia_response_active", False))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))

        # Demand proxy — combines metabolic demand
        demand = max(hypercapnia, vital - 0.5)
        if hypoxia:
            demand = max(demand, 0.5)

        # --- BötC drive ---
        botc_target = self._botc_drive_target(inspiration, rate, hypercapnia, tonic, threat)
        prev_botc = float(self.state.get("botc_drive", self.BASELINE))
        new_botc = self._smooth(prev_botc, botc_target)

        # --- Post-I ---
        post_i_target = self._post_i_target(inspiration, rhythm)
        prev_post_i = float(self.state.get("post_i_drive", 0.20))
        new_post_i = self._smooth(prev_post_i, post_i_target)

        # --- Aug-E ---
        aug_e_target = self._aug_e_target(inspiration, rhythm, demand)
        prev_aug_e = float(self.state.get("aug_e_drive", 0.20))
        new_aug_e = self._smooth(prev_aug_e, aug_e_target)

        # --- Expiratory inhibition ---
        exp_inh = self._expiratory_inhibition(new_botc, new_post_i, new_aug_e)

        # --- Active expiration ---
        active_exp = new_aug_e > self.ACTIVE_EXP_THRESHOLD

        # --- Phase marker ---
        phase = self._phase_marker(inspiration, new_post_i, new_aug_e)

        # --- Irregularity proxy: very low BötC drive can produce irregular pattern ---
        irregular = new_botc < 0.15 and rate > 0.30

        # --- State ---
        state = self._classify_state(active_exp, irregular, new_botc)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["botc_drive"] = round(new_botc, 4)
        self.state["post_i_drive"] = round(new_post_i, 4)
        self.state["aug_e_drive"] = round(new_aug_e, 4)
        self.state["expiratory_inhibition"] = round(exp_inh, 4)
        self.state["active_expiration_engaged"] = active_exp
        self.state["phase_marker"] = phase
        self.state["botc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "botc_drive": round(new_botc, 4),
            "post_i_drive": round(new_post_i, 4),
            "aug_e_drive": round(new_aug_e, 4),
            "expiratory_inhibition": round(exp_inh, 4),
            "active_expiration_engaged": active_exp,
            "phase_marker": phase,
            "botc_state": state,
        }
