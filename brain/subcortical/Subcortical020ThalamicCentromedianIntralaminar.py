"""
Subcortical020ThalamicCentromedianIntralaminar.py — Wire 20: CMIntralaminarArousal

Centromedian (CM) and parafascicular (Pf) intralaminar nuclei —
intralaminar thalamic arousal and pain relay.

Neural analog: CM and Pf constitute the intralaminar nuclear complex of the
thalamus. Together with the centre median (CM), they form the main arousal-
generating matrix thalamic system. They receive input from the brainstem
reticular formation (ascending reticular activating system), the spinal cord
(pain), and the basal ganglia, and project broadly to striatum and cortex.

ANATOMY (Jones 2007):
  - CM/Pf: midline-adjacent intralaminar nuclei (not in main sensory pathways)
  - Inputs: brainstem reticular activating system, spinothalamic pain fibers,
    cerebellar nuclei (indirect), basal ganglia (indirect)
  - Outputs: widespread to striatum (motor), prefrontal cortex (arousal),
    posterior parietal, anterior cingulate
  - Burst and tonic modes: CM neurons fire in low-threshold burst mode
    during non-REM sleep and in tonic mode during waking

HALASSA 2021 — AROUSAL AND MATRIX THALAMUS:
  The "matrix" system (intralaminar nuclei + medial thalamus) provides
  broad, low-specificity background excitation to cortex. This is distinct
  from "core" relay nuclei which send specific sensory signals. Matrix cells
  have wide axonal arbors → widespread cortical depolarization.
  This creates a "blanket of arousal" (Halassa's phrase) over which
  specific signals from first-order relays (like MGN → V1) ride.

PAIN RELAY:
  CM receives spinothalamic input for pain. Pf also relays pain and visceral
  input. CM-Pf stimulation can drive anterior cingulate cortex (ACC),
  the cortical seat of pain affect/unpleasantness.

AUTONOMIC INTEGRATION:
  CM/Pf project to insular cortex and hypothalamus — autonomic state
  monitoring. They carry interoceptive signals (body state) alongside
  arousal signals.

KEY FUNCTIONS:
  1. arousal_modulation: ascending arousal signal from brainstem reticular
     formation, gated by current vigilance state
  2. arousal_weight: how strongly CM is amplifying cortex-wide excitation
  3. autonomic_state_signal: interoceptive/body state info from CM/Pf

REFS:
- Halassa 2021 Nat Rev Neurosci 22:515-530 — matrix vs core thalamus, arousal
- Jones 2007 Thalamus Vol I (2nd ed.) — intralaminar anatomy
- McCormick & Bal 1994 Prog Brain Res — thalamic arousal mechanisms
- Van der Werf et al. 2002 Brain Research Reviews — intralaminar functions
- Sherman & Guillery 2013 — thalamocortical function text

CITATIONS:
    PMC3569130 — Schiff ND, Shah SA, Hudson AE et al. (2013). Gating of Attentional
        Effort Through the Central Thalamus. Front Syst Neurosci.
    PMC10366221 — Kumar VJ, Scheffler K, Grodd W (2023). The Structural Connectivity
        Mapping of the Intralaminar Thalamic Nuclei. Hum Brain Mapp.
"""

from brain.base_mechanism import BrainMechanism


class ThalamicCentromedianIntralaminar(BrainMechanism):
    """
    CM/Pf intralaminar nucleus — arousal, pain, and autonomic relay.

    Receives brainstem arousal signals (ARAS), spinothalamic pain input,
    and basal ganglia modulatory signals. Generates a broad arousal
    modulation signal for cortex plus an autonomic state indicator.

    Distinct from specific sensory relays (MGN, VPL) — CM/Pf provide the
    non-specific "arousal blanket" over cortex.
    """

    ARousal_BASELINE = 0.30       # Intrinsic CM firing in relaxed wakefulness
    BURST_GAIN = 1.20             # Gain during burst (arousal onset)
    PAIN_INFLATION = 0.40         # Pain amplifies arousal weight
    AUTONOMIC_INTEGRATION_GAIN = 0.35
    DECAY_RATE = 0.06             # Natural decay per tick

    def __init__(self):
        super().__init__(
            name="ThalamicCentromedianIntralaminar",
            human_analog="Centromedian/Parafascicular intralaminar nuclei — arousal matrix",
            layer="subcortical",
        )
        self.state.setdefault("arousal_modulation", 0.0)
        self.state.setdefault("arousal_weight", 0.0)
        self.state.setdefault("autonomic_state_signal", 0.0)
        self.state.setdefault("last_pain_input", 0.0)
        self.state.setdefault("brainstem_arousal_input", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source 1: Brainstem ascending reticular activating system (ARAS)
        arasal_signal = prior.get("BrainstemAscendingArousal", {})
        arasal_level = arasal_signal.get("arousal_signal_strength", 0.0)

        # Source 2: Spinothalamic pain input (via spinal cord relay)
        pain_signal = prior.get("SpinalCordPainRelay", {})
        pain_level = pain_signal.get("pain_signal_strength", 0.0)

        # Source 3: Basal ganglia modulation (indirect pathway)
        indirect_pathway = prior.get("IndirectPathwaySuppressor", {})
        bg_modulation = indirect_pathway.get("suppression_strength", 0.0)

        # Source 4: Interoceptive/autonomic state (from insular thalamic relay)
        autonomic_input = prior.get("InteroceptiveThalamicRelay", {})
        interoceptive_signal = autonomic_input.get("interoceptive_strength", 0.0)

        # Arousal modulation: combines ARAS + pain amplification + BG modulation
        base_arousal = self.ARousal_BASELINE + arasal_level * 0.50

        # Pain inflates arousal (acute pain → high arousal/fight-flight mode)
        pain_boost = pain_level * self.PAIN_INFLATION * 0.5

        # Basal ganglia modulates arousal (high indirect = suppressed arousal)
        bg_mod_effect = (0.5 - bg_modulation) * 0.25

        raw_arousal = base_arousal + pain_boost + bg_mod_effect
        arousal_modulation = max(0.0, min(1.0, raw_arousal))

        # Arousal weight: intensity of CM broadcast to cortex
        # High arousal_weight = strong matrix excitation over cortex
        arousal_weight = max(0.0, min(1.0, arousal_modulation * self.BURST_GAIN))

        # Autonomic state signal: combines interoceptive + pain
        autonomic_state = (
            interoceptive_signal * 0.60
            + pain_level * 0.40
        )
        autonomic_state_signal = max(0.0, min(1.0, autonomic_state))

        # Decay arousal if no input
        if arasal_level < 0.05 and pain_level < 0.05:
            arousal_modulation = max(
                self.ARousal_BASELINE,
                arousal_modulation - self.DECAY_RATE
            )
            arousal_weight = max(0.0, arousal_weight - self.DECAY_RATE)

        self.state["arousal_modulation"] = round(arousal_modulation, 4)
        self.state["arousal_weight"] = round(arousal_weight, 4)
        self.state["autonomic_state_signal"] = round(autonomic_state_signal, 4)
        self.state["last_pain_input"] = round(pain_level, 4)
        self.state["brainstem_arousal_input"] = round(arasal_level, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "arousal_modulation": round(arousal_modulation, 4),
            "arousal_weight": round(arousal_weight, 4),
            "autonomic_state_signal": round(autonomic_state_signal, 4),
        }
