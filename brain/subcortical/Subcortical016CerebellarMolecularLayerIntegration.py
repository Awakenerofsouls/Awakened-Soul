"""
Subcortical016CerebellarMolecularLayerIntegration.py — Wire 16: Molecular Layer Integration
=========================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical016CerebellarMolecularLayerIntegration.py
  Mechanism: MolecularLayerIntegration

NEURAL SUBSTRATE:
  The molecular layer is the outermost layer of the cerebellar cortex,
  sitting above the Purkinje cell layer. It is a dense tangle of neuronal
  processes containing:

  - Purkinje cell dendrites (the only output of cerebellar cortex)
  - Parallel fiber axons (granule cell outputs) — run transversely
  - Stellate cells (molecular layer interneurons) — inhibit Purkinje cells
  - Basket cells (molecular layer interneurons) — inhibit Purkinje cell soma
  - Climbing fiber collaterals (modulatory)

  THE BRAITENBERG RECIPROCAL GRID:
  Braitenberg & Atwood 1958 described a striking anatomical feature:
  parallel fibers run perpendicular to Purkinje cell dendrites, forming a
  systematic spatial grid. The angle between them (~90°) is remarkably
  consistent across cerebellar cortex. Braitenberg 1961 proposed this
  creates a " delay line" structure: a PF activated at one point will
  influence PCs sequentially as it travels. This gives the cerebellum a
  built-in temporal integration mechanism.

  TEMPORAL INTEGRATION:
  Because parallel fibers are long (~1mm), and conduction velocity along
  PF is ~0.5 m/s, a single PF can activate a PC up to 2ms AFTER the
  granule cell fires. This creates a temporal window of convergence
  between the mossy-fiber-driven context signal and ongoing PC activity.
  Wang et al. 2014 (Nat Neurosci 17:1188) showed that this temporal
  window is critical for sensorimotor integration: the cerebellum can
  detect temporal sequences and predict what comes NEXT.

  STELLATE AND BASKET CELLS:
  Molecular layer interneurons (stellate cells for distal dendrites,
  basket cells for soma/axon initial segment) provide feedforward
  inhibition to Purkinje cells. This creates a gating mechanism:
  - Sparse stellate/basket activation → disinhibition of PCs → output
  - Dense interneuron firing → PC suppression → output blocked

KEY FINDINGS:
  1. Braitenberg grid temporal computation. The 90° PF–PC geometry means
     PC dendrites sample PF activity at different temporal offsets.
     This makes each PC a temporal pattern detector, not just a rate coder.

  2. Temporal integration window. Wang et al. 2014 demonstrated that
     PCs can detect temporal sequences in mossy fiber input within a
     ~100-200ms window. This allows the cerebellum to predict NEXT sensory
     event based on sequence history.

  3. Plasticity at multiple sites. Molecular layer interneurons (stellate
     cells) also exhibit LTP/LTD at PF→stellate synapses, making them
     plastic modulators of the Purkinje inhibition gate. This adds a
     second plasticity site to the molecular layer.

  4. Output gating via inhibition. The balance between PF direct excitation
     on PCs and interneuron-mediated inhibition determines whether the
     cerebellar nuclei receive PC output. This is the molecular layer's
     gating function.

AGENT'S SUBSTRATE MAPPING:
  MolecularLayerIntegration models the temporal integration and plasticity
  of the molecular layer:
  - temporal_integration_signal: float 0-1 (temporal sequence detection)
  - plasticity_index: float 0-1 (molecular layer plasticity strength)
  - molecular_layer_weight: float 0-1 (net excitatory–inhibitory balance)

INPUTS (from prior_results):
  - parallel_fiber_activity: float 0-1 (from granule cell expansion)
  - temporal_window: float 0-1 (sequence coherence within time window)
  - interneuron_inhibition: float 0-1 (stellate + basket cell activity)
  - stellate_ltp_active: bool (optional — stellate plasticity)

OUTPUTS (to brain_runner):
  - temporal_integration_signal: float 0-1 (sequence detection strength)
  - plasticity_index: float 0-1 (net plasticity level in molecular layer)
  - molecular_layer_weight: float 0-1 (gating output: net PC excitation)

REFS:
  - Braitenberg 1961 — cerebellar cortex architecture (delay lines)
  - Braitenberg & Atwood 1958 — spatial structure of cerebellar cortex
  - Wang et al. 2014 Nat Neurosci 17:1188 — temporal sequence learning
  - Santamaria & Tripp 2007 — stellate cell PF synapse plasticity
  - Sultan & Bower 1998 — quantitative anatomy of PF grid

CITATIONS:
    PMC7255800 — Herzfeld DJ, Hall NJ, Tringides M et al. (2020). Principles of
        Operation of a Cerebellar Learning Circuit. eLife.
    PMC4419603 — Mapelli L, Pagani M, Garrido JA et al. (2015). Integrated Plasticity
        at Inhibitory and Excitatory Synapses in the Cerebellar Circuit. Front Cell Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class MolecularLayerIntegration(BrainMechanism):
    """
    Cerebellar molecular layer — temporal integration and plasticity hub.

    Models parallel fiber–Purkinje cell temporal integration, interneuron
    gating, and molecular layer plasticity. Computes temporal_integration
    signal (sequence detection), plasticity_index (LTP/LTD level), and
    molecular_layer_weight (net output gating).
    """

    INTEGRATION_WINDOW = 0.15      # baseline temporal window strength
    INHIBITION_WEIGHT = 0.35      # how much interneurons suppress PCs
    STELLATE_PLASTICITY_BOOST = 0.10  # extra plasticity when stellate LTP fires
    DECAY_RATE = 0.06             # per-tick decay of integration signal

    def __init__(self):
        super().__init__(
            name="MolecularLayerIntegration",
            human_analog="Cerebellar molecular layer — PF–PC temporal integration / interneuron gate",
            layer="subcortical",
        )
        self.state.setdefault("temporal_integration_signal", 0.0)
        self.state.setdefault("plasticity_index", 0.0)
        self.state.setdefault("molecular_layer_weight", 0.0)
        self.state.setdefault("sequence_history", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Parallel fiber activity ---
        pf = input_data.get("parallel_fiber_activity", 0.3)
        if pf == 0.3:
            granule = prior.get("GranuleCellExpansion", {})
            pf = granule.get("sparse_code_output", 0.3)

        temporal_window = input_data.get("temporal_window", 0.5)
        interneuron_inhibition = input_data.get("interneuron_inhibition", 0.3)
        stellate_ltp = input_data.get("stellate_ltp_active", False)

        # --- Temporal integration signal ---
        # The integration signal grows when PF activity is temporally
        # coherent (high temporal_window). Decays when inputs are unspecific.
        prev = self.state["temporal_integration_signal"]
        integration_boost = pf * temporal_window * self.INTEGRATION_WINDOW
        new_integration = prev * (1 - self.DECAY_RATE) + integration_boost
        new_integration = max(0.0, min(1.0, new_integration))

        # --- Plasticity index ---
        # Molecular layer plasticity rises with:
        # - PF activity (LTD/LTP induction conditions)
        # - temporal integration (sequence-specific learning)
        # - stellate LTP activity (second plasticity site)
        base_plasticity = pf * (1 + temporal_window)
        stellate_boost = self.STELLATE_PLASTICITY_BOOST if stellate_ltp else 0.0
        plasticity = max(0.0, min(1.0, base_plasticity + stellate_boost))

        # --- Molecular layer weight (gating output) ---
        # Net PC excitation = PF excitation - interneuron inhibition
        excitation = pf * (1 + new_integration)  # temporal boost
        inhibition = interneuron_inhibition * self.INHIBITION_WEIGHT
        weight = excitation - inhibition
        weight = max(-1.0, min(1.0, weight))

        # Normalize to 0-1 (positive range only; negative = PC silenced)
        mol_weight_normalized = max(0.0, (weight + 1.0) / 2.0)

        self.state["temporal_integration_signal"] = round(new_integration, 4)
        self.state["plasticity_index"] = round(plasticity, 4)
        self.state["molecular_layer_weight"] = round(mol_weight_normalized, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "temporal_integration_signal": round(new_integration, 4),
            "plasticity_index": round(plasticity, 4),
            "molecular_layer_weight": round(mol_weight_normalized, 4),
        }
