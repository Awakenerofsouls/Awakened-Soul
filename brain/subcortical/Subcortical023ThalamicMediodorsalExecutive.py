"""
Subcortical023ThalamicMediodorsalExecutive.py — Wire 23: ThalamicMDExecutive

Mediodorsal (MD) thalamic nucleus — PFC executive function relay.

Neural analog: MD is the thalamic station of the prefrontal cortex. It is
a higher-order relay that receives from layer 5 of PFC and projects back to
layer 4 of PFC, forming the cortico-thalamo-cortical loop that supports
working memory, executive control, and decision-making. MD dysfunction
produces profound deficits in PFC-dependent cognition.

ANATOMY (Collins 2018; Parnaudeau 2013):
  - MD subdivisions: medial (limbic, connected to ACC), central (cognitive,
    connected to DLPFC), lateral (connected to lateral PFC)
  - Inputs: PFC layer 5 (all subdivisions), ventral tegmental area (VTA)
    dopaminergic afferents, basal forebrain, raphe nuclei
  - Outputs: widespread to prefrontal cortex (DLPFC, ACC, OFC, LPFC),
    entorhinal cortex
  - MD-PFC loop: the most prominent thalamo-cortical excitatory loop;
    damage to either MD or PFC disrupts this loop completely

COLLINS 2018 — MD IN COGNITIVE CONTROL:
  "Mediodorsal thalamus is essential for prefrontal cortical dynamics
  and cognitive flexibility." Collins et al. showed that:
  1. MD supports PFC persistent firing (maintenance of working memory)
  2. MD synchronizes PFC gamma oscillations during cognitive load
  3. MD disruption causes cognitive inflexibility (cannot update rules)
  4. MD-PFC coupling increases during working memory tasks

PARNAUDEAU 2013 — MD IN FLEXIBILITY:
  Parnaudeau et al. showed that MD inactivation specifically disrupts:
  - Rule learning and set-shifting (not skill learning)
  - Behavioral flexibility when reward contingencies change
  - This implicates MD in "updating" rather than "maintaining"
  - MD is the thalamic trigger for PFC rule-updating

DOPAMINERGIC MODULATION:
  VTA → MD dopaminergic afferents modulate MD-PFC communication.
  This is analogous to SNc → striatum (basal ganglia) but for the
  cognitive loop. MD dopamine enhances signal-to-noise in the MD-PFC loop.

KEY FUNCTIONS:
  1. executive_relay_strength: strength of MD → PFC relay signal
  2. PFC_coordination_signal: MD-mediated coordination across PFC regions
  3. MD_weight: thalamic influence on PFC cortical dynamics

REFS:
- Collins 2018 Nat Neurosci 21:1418-1428 — MD in cognitive control/flexibility
- Parnaudeau et al. 2013 J Neurosci 33:15734-15746 — MD inactivation studies
- Parnaudeau et al. 2015 Front Syst Neurosci — MD cognitive functions review
- Watanabe & Funahashi 2012 Neurosci Biobehav Rev — MD-PFC monkey studies
- Groenewegen 1988 J Comp Neurol — MD anatomy in rat
- Halassa & Sherman 2019 — higher-order relay classification of MD

CITATIONS:
    PMC11881366 — Mochizuki Y, Joji-Nishino A, Emoto K et al. (2025). Distinct Neural
        Responses of Ventromedial Prefrontal Cortex-Projecting Nucleus Reuniens Neurons
        During Aversive Memory Extinction. eNeuro.
    PMC1951790 — Hugues S, Garcia R (2007). Reorganization of Learning-Associated
        Prefrontal Synaptic Plasticity. Eur J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class ThalamicMediodorsalExecutive(BrainMechanism):
    """
    MD mediodorsal thalamus — prefrontal executive function relay.

    MD is the thalamic hub of PFC executive function. It maintains the
    cortico-thalamo-cortical loop that enables working memory persistence,
    rule representation, and behavioral flexibility. MD receives from PFC
    layer 5 and projects back to PFC layer 4 — the cognitive thalamo-
    cortical loop.

    Inputs: PFC layer 5 efference, VTA dopaminergic modulation,
    rule update signals from ACC, arousal from CM.
    """

    RELAY_GAIN = 0.85
    DOPAMINE_MODULATION = 0.30
    PFC_COORDINATION_GAIN = 0.70
    RULE_UPDATE_BOOST = 0.60
    DECAY_RATE = 0.06

    def __init__(self):
        super().__init__(
            name="ThalamicMediodorsalExecutive",
            human_analog="Mediodorsal (MD) thalamus — PFC executive relay",
            layer="subcortical",
        )
        self.state.setdefault("executive_relay_strength", 0.0)
        self.state.setdefault("PFC_coordination_signal", 0.0)
        self.state.setdefault("MD_weight", 0.0)
        self.state.setdefault("last_rule_update_strength", 0.0)
        self.state.setdefault("dopamine_level", 0.5)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source 1: PFC layer 5 efference copy (what PFC is processing)
        pfc_efference = prior.get("PrefrontalExecutive", {})
        pfc_signal = pfc_efference.get("executive_relay_strength", 0.0)

        # Source 2: VTA/SNc dopaminergic modulation
        dopamine_signal = prior.get("SubstantiaNigraCompactaCognitive", {})
        dopamine_level = max(0.0, dopamine_signal.get("prediction_error", 0.5))
        # PE > 0 means better than expected = dopaminergic boost
        if dopamine_level > 0.0:
            dopamine_level = min(1.0, dopamine_level + 0.3)

        # Source 3: Rule update signals from ACC (anterior cingulate)
        acc_signal = prior.get("AnteriorCingulateRegulator", {})
        rule_update_strength = acc_signal.get("conflict_signal_strength", 0.0)

        # Source 4: CM arousal (matrix thalamus provides background arousal)
        cm_arousal = prior.get("ThalamicCentromedianIntralaminar", {})
        cm_level = cm_arousal.get("arousal_modulation", 0.0)

        # Source 5: Cognitive prediction error (signals need for rule update)
        cognitive_pe = prior.get("PredictionErrorDrift", {})
        cognitive_surprise = cognitive_pe.get("surprise_magnitude", 0.0)

        # Executive relay: PFC signal amplified by MD
        raw_relay = (
            pfc_signal * self.RELAY_GAIN
            + cm_level * 0.15
            + dopamine_level * self.DOPAMINE_MODULATION * 0.20
        )

        # Rule update boost: when cognitive PE is high, MD amplifies rule update
        if cognitive_surprise > 0.3 or rule_update_strength > 0.3:
            raw_relay += self.RULE_UPDATE_BOOST * max(cognitive_surprise, rule_update_strength)

        executive_relay = max(0.0, min(1.0, raw_relay))

        # PFC coordination signal: MD synchronizes multiple PFC regions
        # High coordination = multiple PFC regions being driven by MD
        coordination = max(
            0.0,
            min(1.0, executive_relay * self.PFC_COORDINATION_GAIN + cm_level * 0.2)
        )

        # MD weight: thalamic influence on PFC cortical dynamics
        # MD fires proportional to its PFC coordination role
        md_weight = max(0.0, min(1.0, executive_relay * 0.8 + dopamine_level * 0.2))

        # Decay on low input
        if pfc_signal < 0.05:
            executive_relay = max(0.0, executive_relay - self.DECAY_RATE)
            coordination = max(0.0, coordination - self.DECAY_RATE)
            md_weight = max(0.0, md_weight - self.DECAY_RATE)

        self.state["executive_relay_strength"] = round(executive_relay, 4)
        self.state["PFC_coordination_signal"] = round(coordination, 4)
        self.state["MD_weight"] = round(md_weight, 4)
        self.state["last_rule_update_strength"] = round(rule_update_strength, 4)
        self.state["dopamine_level"] = round(dopamine_level, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "executive_relay_strength": round(executive_relay, 4),
            "PFC_coordination_signal": round(coordination, 4),
            "MD_weight": round(md_weight, 4),
        }
