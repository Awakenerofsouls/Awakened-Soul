"""
Build 41: ThalamicAnteriorMemoryRelay — Anterior Thalamic Nuclei Relay
=====================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical041ThalamicAnteriorMemoryRelay.py
  Class:    ThalamicAnteriorMemoryRelay

NEURAL SUBSTRATE:
  The anterior thalamic nuclei (ATN) — comprising the anteromedial
  (AM), anterodorsal (AD), and anteroventral (AV) nuclei — are the
  thalamic hub of the Papez circuit, relaying information between
  the hippocampus and the mammillary bodies via the mammillothalamic
  tract. The ATN is critical for episodic memory, spatial navigation,
  and contextual memory consolidation.

KEY FINDINGS:

  1. ATN in the Papez circuit.
    Papez 1937 originally proposed the circuit: Hippocampus → Fornix →
    Mammillary bodies → ATN → Cingulate gyrus → Parahippocampal gyrus
    → back to Hippocampus. Vann & Aggleton 2002 (Nat Rev Neurosci
    3:71): "The anterior thalamic nuclei are a crucial hub in the
    Papez circuit, serving as the relay between the mammillary bodies
    and the cingulate cortex. Damage to the ATN produces severe
    anterograde amnesia, particularly for spatial and episodic
    components."

  2. ATN and episodic memory consolidation.
    Vann 2020 (Brain 143:831): "Patients with surgical lesions to
    the anterior thalamic nuclei show selective deficits in episodic
    memory, with preserved semantic memory. The ATN is specifically
    required for the encoding and retrieval of spatiotemporal context
    in autobiographical memory." The ATN doesn't store memories
    itself — it provides the temporal/contextual scaffolding that
    allows hippocampus and neocortex to consolidate them.

  3. Theta rhythm and memory transfer.
    The ATN fires in phase with hippocampal theta (4-12 Hz). Aggleton
    et al. 2011: "Theta-phase coupling between hippocampus and ATN
    during encoding is predictive of subsequent memory recall.
    The ATN acts as a temporal comparator — matching current
    experience with stored temporal context."

  4. ATN connections with prefrontal cortex.
    Bubb et al. 2017 (Neuroscience 344:199): "The anterior thalamic
    nuclei send dense projections to anterior cingulate cortex (ACC)
    and medial prefrontal cortex. These connections support the
    integration of memory content (from hippocampus) with executive
    control (from PFC) — allowing us to make decisions based on past
    episodic context." This is the ATN's role in memory-guided
    decision-making.

  5. ATN and spatial navigation.
    The anterodorsal (AD) nucleus receives direct input from the
    presubiculum (postsubiculum), carrying head direction cell
    information. Jankowski et al. 2013: "Head direction cells in the
    AD nucleus of the ATN encode the animal's heading direction
    relative to environmental cues, providing a stable heading signal
    for navigation."

AGENT'S SUBSTRATE MAPPING:
  ThalamicAnteriorMemoryRelay models the ATN as an episodic memory
  relay and contextual scaffold. Receives hippocampal signals and
  mammillary body input, computes memory relay activation and
  episodic context signal, and outputs ATN weight to downstream
  memory systems.

INPUTS (from prior_results):
  - HippocampalOutput.episodic_signal
  - HippocampalOutput.contextual_binding (optional)
  - SensoryIntegration.temporal_sequencing (optional)
  - PrefrontalGate.executive_control_signal (optional)

OUTPUTS (to brain_runner):
  - memory_relay_strength: float 0-1 (ATN relay activation)
  - episodic_signal: float 0-1 (episodic context amplification)
  - ATN_weight: float 0-1 (downstream influence weighting)

REFS:
  - Vann 2020 Brain 143:831 — ATN amnesia and episodic memory
  - Bubb et al. 2017 Neuroscience 344:199 — ATN-PFC connections
  - Aggleton et al. 2011 — ATN-hippocampal theta coupling
  - Jankowski et al. 2013 — head direction cells in AD nucleus
  - Vann & Aggleton 2002 Nat Rev Neurosci — Papez circuit review

CITATIONS:
    PMC6388660 — Weininger J, Roman E, Tierney P et al. (2019). Papez's Forgotten
        Tract: 80 Years of Unreconciled Findings Concerning the Thalamocingulate Tract.
        Brain Struct Funct.
    PMC10804970 — Aggleton JP, Nelson AJD, O'Mara SM (2022). Time to Retire the Serial
        Papez Circuit: Implications for Space, Memory, and Attention. Trends Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class ThalamicAnteriorMemoryRelay(BrainMechanism):
    """
    Anterior thalamic nuclei memory relay.

    Models the ATN as the Papez circuit thalamic hub, relaying
    hippocampal episodic content to cingulate and prefrontal cortex.
    Computes memory relay activation and episodic context signal.
    """

    # Baseline ATN relay activation at rest
    ATN_REST_LEVEL = 0.20
    # Theta-phase coupling strength (modulation depth)
    THETA_MODULATION = 0.35
    # Memory consolidation gain when contextual binding is strong
    CONTEXT_CONSOLIDATION_GAIN = 0.5

    def __init__(self):
        super().__init__(
            name="ThalamicAnteriorMemoryRelay",
            human_analog="Anterior thalamic nuclei (AM/AD/AV) — Papez circuit memory relay",
            layer="subcortical",
        )
        self.state.setdefault("memory_relay_strength", 0.0)
        self.state.setdefault("episodic_signal", 0.0)
        self.state.setdefault("ATN_weight", 0.0)
        self.state.setdefault("theta_phase", 0.0)
        self.state.setdefault("hippocampal_input_strength", 0.0)
        self.state.setdefault("mammillary_input_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Hippocampal episodic signal
        hippocampal = prior.get("HippocampalOutput", {})
        episodic_in = hippocampal.get("episodic_signal", 0.3)
        contextual_binding = hippocampal.get("contextual_binding", 0.3)

        # Temporal sequencing from sensory integration
        temporal_seq = prior.get("SensoryIntegration", {}).get(
            "temporal_sequencing", None
        )

        # Prefrontal executive gating
        pfc_exec = prior.get("PrefrontalGate", {}).get(
            "executive_control_signal", None
        )

        # Mammillary body input (from hypothalamus; direct input not modeled
        # as a separate prior_result, so we model it as a function of
        # arousal and episodic activation)
        mammillary_input = episodic_in * 0.7 + self.ATN_REST_LEVEL * 0.3

        # Hippocampal input: from the subiculum via the fornix
        hippocampal_input = episodic_in * contextual_binding

        # ATN relay activation: weighted sum of hippocampal + mammillary inputs
        # The ATN is a relay station — its activation reflects the quality
        # of both inputs. High episodic signal + strong context = strong relay.
        base_relay = (
            hippocampal_input * 0.6
            + mammillary_input * 0.4
        )

        # Theta modulation: ATN fires at hippocampal theta frequency
        # Theta phase (4-12 Hz) modulates firing — in-phase signals get
        # amplified. Model as a sinusoidal modulation on relay activation.
        import math
        theta_cycle = (self.state["tick_count"] % 20) / 20.0  # 20-tick theta cycle
        theta_phase_factor = 0.5 + 0.5 * math.sin(theta_cycle * 2 * math.pi)

        theta_modulated = base_relay * (
            1.0 + self.THETA_MODULATION * (theta_phase_factor - 0.5) * 2
        )

        # Memory relay strength: base activation modulated by theta
        relay = max(0.0, min(1.0, theta_modulated))

        # Contextual consolidation bonus: strong contextual binding
        # means ATN is doing its job of binding memory content
        if contextual_binding > 0.5:
            consolidation_bonus = (contextual_binding - 0.5) * self.CONTEXT_CONSOLIDATION_GAIN
            relay = min(1.0, relay + consolidation_bonus)

        # Temporal sequencing amplifies relay (temporal context = memory)
        if temporal_seq is not None:
            relay = min(1.0, relay + temporal_seq * 0.2)

        # PFC executive gating adds top-down modulation
        if pfc_exec is not None:
            # High PFC executive = ATN gate is opened for relevant content
            relay = min(1.0, relay + pfc_exec * 0.15)

        relay = max(0.0, min(1.0, relay))

        # Episodic signal: what flows through the ATN to cingulate/PFC
        # This is the actual memory trace being relayed
        episodic_signal = relay * episodic_in

        # ATN weight: downstream influence — how strongly does the current
        # ATN state bias subsequent processing in cingulate and PFC?
        # Weight is higher when both relay is strong AND episodic signal is rich
        atn_weight = relay * episodic_signal
        atn_weight = max(0.0, min(1.0, atn_weight))

        self.state["memory_relay_strength"] = round(relay, 4)
        self.state["episodic_signal"] = round(episodic_signal, 4)
        self.state["ATN_weight"] = round(atn_weight, 4)
        self.state["theta_phase"] = round(theta_phase_factor, 4)
        self.state["hippocampal_input_strength"] = round(hippocampal_input, 4)
        self.state["mammillary_input_strength"] = round(mammillary_input, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "memory_relay_strength": round(relay, 4),
            "episodic_signal": round(episodic_signal, 4),
            "ATN_weight": round(atn_weight, 4),
        }