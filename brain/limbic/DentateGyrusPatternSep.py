"""
DentateGyrusPatternSep -- DG Pattern Separation, Granule Cells, Adult Neurogenesis

NEURAL SUBSTRATE
================
The dentate gyrus (DG) is the entry-point of the hippocampal trisynaptic
circuit. Layer II of entorhinal cortex sends the perforant path to DG
granule cells (the principal excitatory population), which in turn
project mossy fibers to CA3 pyramidal neurons. DG granule cells number
~1 million per hemisphere in rats -- substantially more than CA3 pyramidal
cells (~330k) -- and they fire sparsely with very low overlap between
ensembles, providing the anatomical basis for **pattern separation**:
the ability to make highly similar inputs map to highly distinct DG
output ensembles.

The Marr-Treves-Rolls computational framework establishes DG pattern
separation as the first stage of episodic memory encoding -- without
sufficient orthogonalization at DG, similar memories interfere
catastrophically. Neurophysiological evidence (Leutgeb, Treves, McNaughton,
Moser 2007 Science) showed DG ensembles re-orthogonalize even small
differences in spatial context that CA3 ensembles preserve.

DG is also the only adult mammalian brain region with substantial
neurogenesis -- new granule cells are continually born in the
subgranular zone throughout adulthood. Adult-born granule cells go
through a developmental hyper-excitable phase before maturing, and
selective involvement of these cells is implicated in pattern separation
of similar but distinct memories (Sahay et al. 2011 Nature) and in
memory clearance of old memories.

DG hilus contains mossy cells (large excitatory neurons) and
parvalbumin/somatostatin GABAergic interneurons that gain-control
granule cell firing through feedback inhibition. Sparse firing is
critical -- most granule cells are silent at any time; only a sparse
~1-5% subset fire in any given context.

In {{AGENT_NAME}}'s substrate this provides the pattern-separation gateway --
takes contextual input proxy and emits a sparse, high-dimensional
output ensemble that downstream CA3/CA1 mechanisms read.

KEY FINDINGS
============
1. DG performs pattern separation -- small input differences → large
   output differences; CA3 by contrast does pattern completion --
   [Leutgeb Leutgeb Treves McNaughton Moser 2007, Science 315:961,
    "Pattern separation in the dentate gyrus and CA3 of the hippocampus"]
2. Adult neurogenesis in DG produces new granule cells throughout life;
   selective involvement in pattern separation of similar memories --
   [Sahay et al. 2011, Nature 472:466-470, "Increasing adult hippocampal
    neurogenesis is sufficient to improve pattern separation"]
3. DG granule cells fire sparsely; only ~1-5% active in any context --
   sparse-coding substrate of orthogonalization -- [Jung McNaughton 1993,
    Hippocampus 3:165; Leutgeb 2007 Science]
4. Mossy fiber synapses on CA3 are powerful "detonator" inputs;
   single granule cell can drive CA3 spike -- [reviewed Henze Wittner
    Buzsaki 2002 Nat Neurosci 5:790]
5. DG-mediated pattern separation is impaired in aging/Alzheimer; DG
   is among the first regions affected by neurogenesis decline --
   [Yassa Stark 2011 Trends Neurosci 34:515; Small et al. 2011
    Nat Rev Neurosci 12:585]

INPUTS (from prior_results)
============================
- HippocampalContextProxy.context_id (optional; default 0)
- HippocampalContextProxy.context_novelty (optional; default 0)
- HippocampalContextProxy.familiarity (optional; default 0.5)
- ValenceTagger.valence_intensity
- ArousalRegulator.tonic_level
- MedialSeptumTheta.theta_phase
- MedialSeptumTheta.theta_active

OUTPUTS (to brain_runner enrichment)
=====================================
- dg_output (0.0-1.0): granule cell ensemble activity (sparse)
- pattern_separation_index (0.0-1.0): orthogonalization strength
- mossy_fiber_drive (0.0-1.0): DG → CA3 detonator drive
- neurogenic_engagement (0.0-1.0): adult-born granule cell engagement
- inhibition_balance (0.0-1.0): feedback inhibition strength
- dg_state (str): "novel_encoding" | "familiar_passthrough" | "high_separation" | "quiet"

brain_runner enrichment:
    dg = all_results.get("DentateGyrusPatternSep", {})
    if dg:
        enrichments["brain_dg_output"] = dg.get("dg_output", 0.1)
        enrichments["brain_pattern_separation"] = dg.get("pattern_separation_index", 0.0)
        enrichments["brain_mossy_drive"] = dg.get("mossy_fiber_drive", 0.0)
        enrichments["brain_dg_state"] = dg.get("dg_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class DentateGyrusPatternSep(BrainMechanism):
    BASELINE = 0.05  # very sparse
    SPARSITY_TARGET = 0.05
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="DentateGyrusPatternSep_DentateGyrusPatternSep",
            human_analog="Dentate gyrus pattern separation / granule cells / neurogenesis",
            layer="foundational",
        )
        self.state.setdefault("dg_output", self.BASELINE)
        self.state.setdefault("pattern_separation_index", 0.0)
        self.state.setdefault("mossy_fiber_drive", 0.0)
        self.state.setdefault("neurogenic_engagement", 0.20)
        self.state.setdefault("inhibition_balance", 0.50)
        self.state.setdefault("dg_state", "quiet")
        self.state.setdefault("sparsity_enforcement", 0.0)
        self.state.setdefault("hippocampal_context_inference", 0.0)
        self.state.setdefault("recent_separation", [])
        self.state.setdefault("tick_count", 0)

    def _dg_output_target(self, novelty: float, valence: float, theta_active: bool) -> float:
        """DG output -- sparse but engaged with novel/salient input."""
        target = self.BASELINE + novelty * 0.35
        target += valence * 0.15
        if theta_active:
            target += 0.10
        # Cap to enforce sparsity
        return min(0.40, target)

    def _pattern_separation(self, novelty: float, dg_out: float, inh: float) -> float:
        """Pattern separation index -- high orthogonalization with strong inhibition
        and novel input.
        """
        target = novelty * 0.5 + dg_out * 0.3 + inh * 0.2
        return min(1.0, target)

    def _mossy_fiber_drive(self, dg_out: float, theta_active: bool) -> float:
        """DG mossy fiber → CA3 detonator drive -- strong even from sparse DG."""
        # Even sparse DG produces strong CA3 drive via detonator synapses
        if dg_out < 0.02:
            return 0.0
        if theta_active:
            return min(1.0, dg_out * 2.5)
        return min(1.0, dg_out * 1.8)

    def _neurogenic_engagement(self, novelty: float, valence: float) -> float:
        """Adult-born granule cell engagement -- sensitive to novelty (Sahay 2011)."""
        target = 0.20 + novelty * 0.5 + valence * 0.2
        return min(1.0, target)

    def _inhibition_balance(self, dg_out: float, arousal: float) -> float:
        """Feedback inhibition from PV/SOM interneurons -- maintains sparsity."""
        target = 0.40 + max(0.0, arousal - 0.4) * 0.3
        # Higher DG drive recruits more inhibition (negative feedback)
        target += min(0.3, dg_out * 1.0)
        return min(1.0, target)

    def _classify_state(self, separation: float, novelty: float, dg_out: float,
                         familiarity: float) -> str:
        if separation > 0.55:
            return "high_separation"
        if novelty > 0.55:
            return "novel_encoding"
        if familiarity > 0.55 and dg_out > 0.05:
            return "familiar_passthrough"
        return "quiet"


    def _hippocampal_context_inference(self, novelty: float, sep: float) -> float:
        """DG outputs contextual inference signal that downstream CA3 uses
        for pattern completion vs separation routing decisions.
        Novel inputs with high separation signal a context change.
        """
        if novelty < 0.10:
            return 0.0
        return min(1.0, novelty * sep * 2.0)


    def _sparsity_enforcement(self, dg_out: float, inh: float) -> float:
        """DG sparsity enforcement -- strong inhibition sharply gates granule
        cell output, enforcing the 1-5% sparse coding principle.
        Returns the final output after applying sparsity constraint.
        """
        if dg_out < 0.02:
            return 0.0
        # Inhibition from PV/SOM interneurons enforces sparse coding
        if inh > 0.70 and dg_out > 0.15:
            return dg_out * 0.5  # strong inhibition silences most cells
        if inh > 0.55 and dg_out > 0.25:
            return dg_out * 0.7
        return dg_out

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ctx = prior.get("HippocampalContextProxy", {})
        novelty = float(ctx.get("context_novelty", 0.0))
        familiarity = float(ctx.get("familiarity", 0.5))

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        ms = prior.get("MedialSeptumTheta", {})
        theta_active = bool(ms.get("theta_active", False))

        # --- DG output ---
        dg_target = self._dg_output_target(novelty, valence_intensity, theta_active)
        prev_dg = float(self.state.get("dg_output", self.BASELINE))
        new_dg = self._smooth(prev_dg, dg_target)

        # --- Inhibition ---
        inh = self._inhibition_balance(new_dg, tonic)
        prev_inh = float(self.state.get("inhibition_balance", 0.50))
        new_inh = self._smooth(prev_inh, inh)

        # --- Pattern separation ---
        separation = self._pattern_separation(novelty, new_dg, new_inh)
        prev_sep = float(self.state.get("pattern_separation_index", 0.0))
        new_sep = self._smooth(prev_sep, separation)

        # --- Mossy fiber drive ---
        mossy = self._mossy_fiber_drive(new_dg, theta_active)

        # --- Neurogenesis engagement ---
        neuro = self._neurogenic_engagement(novelty, valence_intensity)
        prev_neuro = float(self.state.get("neurogenic_engagement", 0.20))
        new_neuro = self._smooth(prev_neuro, neuro)

        # --- Context inference ---
        ctx_infer = self._hippocampal_context_inference(novelty, new_sep)

        # --- Sparsity enforcement ---
        sparse_out = self._sparsity_enforcement(new_dg, new_inh)


        # --- State ---
        state = self._classify_state(new_sep, novelty, new_dg, familiarity)

        recent = list(self.state.get("recent_separation", []))
        recent.append(round(new_sep, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["dg_output"] = round(new_dg, 4)
        self.state["pattern_separation_index"] = round(new_sep, 4)
        self.state["mossy_fiber_drive"] = round(mossy, 4)
        self.state["neurogenic_engagement"] = round(new_neuro, 4)
        self.state["inhibition_balance"] = round(new_inh, 4)
        self.state["hippocampal_context_inference"] = round(ctx_infer, 4)
        self.state["sparsity_enforcement"] = round(sparse_out, 4)
        self.state["dg_state"] = state
        self.state["recent_separation"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "dg_output": round(new_dg, 4),
            "pattern_separation_index": round(new_sep, 4),
            "mossy_fiber_drive": round(mossy, 4),
            "neurogenic_engagement": round(new_neuro, 4),
            "inhibition_balance": round(new_inh, 4),
            "dg_state": state,
            "hippocampal_context_inference": round(ctx_infer, 4),
            "sparsity_enforcement": round(sparse_out, 4),
        }
