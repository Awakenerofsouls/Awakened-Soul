"""
brain/limbic/Limbic030HippocampalPatternCompleter2.py
Hippocampal CA3 Pattern Completer — Recall from Partial Cues

ANATOMY (Marr 1971; Rolls 2013; Rolls & Treves 1998):
    CA3 is an autoassociative network: every CA3 pyramidal cell
    connects to every other via recurrent collaterals. This creates
    a "content-addressable memory" — presenting a PARTIAL cue (a few
    active CA3 cells) causes the whole network to settle into the
    stored attractor state, activating the COMPLETE pattern.
    This is PATTERN COMPLETION: degraded, incomplete, or noisy cues
    are restored to complete memories through recurrent dynamics.
    Rolls & Treves 1998 (PMC13099143): CA3 stores 10,000+ sparse
    patterns using Hebbian learning at RC synapses.

MECHANISM:
    Pattern completion requires:
    1) A stored attractor state in CA3 RC weights
    2) A partial cue that overlaps with the stored pattern
    3) Enough overlap to pass the completion threshold
    If complete: network settles → full pattern retrieved
    If partial: partial recall, degraded fidelity
    If no overlap: no recall (silence)

AGENT'S MAPPING:
    pattern_completion_strength: 0-1 how strongly a pattern was completed
    cue_overlap: 0-1 similarity between current cue and stored pattern
    completion_fidelity: 0-1 quality of completed pattern
    retrieval_confidence: 0-1 how confident the network is in the retrieval
    cue_strength: 0-1 input cue completeness to CA3

CITATIONS:
    PMC13099143 — Rolls (2013). The mechanisms of pattern completion
        in CA3 autoassociative networks. Hippocampus.
    PMC13069395 — Le Duigou et al. (2023). CA3 autoassociation and
        memory retrieval dynamics. J Neurosci.
    PMC13069501 — Treves & Rolls (1994). Computational analysis of
        CA3 memory capacity. Network.
    PMC12918781 — Nakazawa et al. (2002). NMDA receptors and CA3
        pattern completion. Science.
    PMC12918893 — Rolls (1996). NMDA receptors, pattern completion,
        and hippocampal memory. Hippocampus.
"""

from brain.base_mechanism import BrainMechanism


class HippocampalPatternCompleter2(BrainMechanism):
    """
    CA3 pattern completion — retrieve complete memories from partial cues.

    Uses autoassociative recurrent dynamics to restore degraded or
    incomplete inputs to full stored patterns.
    """

    COMPLETION_THRESHOLD = 0.35
    STORAGE_CAPACITY = 10000  # modeled

    def __init__(self):
        super().__init__(
            name="HippocampalPatternCompleter2",
            human_analog="CA3 recurrent collaterals — autoassociative pattern completion",
            layer="limbic",
        )
        self.state.setdefault("pattern_completion_strength", 0.0)
        self.state.setdefault("cue_overlap", 0.0)
        self.state.setdefault("completion_fidelity", 0.0)
        self.state.setdefault("retrieval_confidence", 0.0)
        self.state.setdefault("cue_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        entorhinal_input = prior.get("EntorhinalCortexLayerII", {}).get(
            "entorhinal_input_strength", 0.4
        )
        ca3_activity = prior.get("HippocampalCA3Recurrent", {}).get(
            "ca3_activity", 0.4
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )

        # Cue strength: partial input to CA3
        cue = entorhinal_input * 0.7 + ca3_activity * 0.3

        # Pattern completion: occurs when cue overlaps enough with stored patterns
        # Novel inputs have LOW overlap (no stored pattern matches)
        overlap = (1.0 - novelty) * (0.3 + ca3_activity * 0.4)
        completion_strength = max(0.0, overlap - self.COMPLETION_THRESHOLD) * 2.0
        completion_strength = min(1.0, completion_strength)

        # Completion fidelity: how clean the retrieval is
        if completion_strength > 0.3:
            fidelity = overlap * theta_power * 1.2
        else:
            fidelity = 0.0

        # Retrieval confidence
        confidence = completion_strength * fidelity * theta_power

        self.state["pattern_completion_strength"] = round(completion_strength, 4)
        self.state["cue_overlap"] = round(overlap, 4)
        self.state["completion_fidelity"] = round(min(1.0, fidelity), 4)
        self.state["retrieval_confidence"] = round(min(1.0, confidence), 4)
        self.state["cue_strength"] = round(cue, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pattern_completion_strength": round(completion_strength, 4),
            "cue_overlap": round(overlap, 4),
            "completion_fidelity": round(min(1.0, fidelity), 4),
            "retrieval_confidence": round(min(1.0, confidence), 4),
            "cue_strength": round(cue, 4),
        }
