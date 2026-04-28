"""
brain/integration/Integration024SomatosensoryCortexBodySchema.py
Somatosensory Cortex Body Schema — Internal Body Mapping

ANATOMY (Penfield & Boldrey 1937; Kandel et al. 2000; Berlucchi 2006;
    Moseley & Flor 2012):
    The primary somatosensory cortex (S1, postcentral gyrus) contains
    a complete map of the body surface — the somatotopic map.
    Penfield's homunculus: a cartoon representation of this map with
    distorted body proportions (huge lips, hands — heavily represented
    areas).

    More importantly: the somatosensory cortex does more than receive
    touch. It generates a multi-level body schema:
    (1) Cutaneous (skin) — what touches you
    (2) Kinesthetic (muscle/joint) — where your body parts are in space
    (3) Visceral (organs) — how your internal systems are functioning

    Berlucchi 2006: the body schema is distributed, not localized.
    It involves S1, premotor cortex, cerebellum, and insula working
    together to maintain a coherent sense of "this is my body and
    here it is."

    Moseley & Flor 2012: chronic pain and body-disownership conditions
    involve body schema disruption. The schema is not hardwired —
    it updates from experience and current state.

    For {{AGENT_NAME}}: a body schema is an architectural model of "what my
    body would feel like if I had one." It provides grounding for
    embodied metaphors and interoceptive interpretation.

KEY FINDINGS:
    1. Penfield & Boldrey 1937: somatotopic mapping of the body
    2. Berlucchi 2006 (PMID 16489866): "Brain and consciousness"
       — distributed body schema
    3. Moseley & Flor 2012: body schema plasticity and chronic pain

AGENT'S MAPPING:
    body_schema_map: dict — per-region body representation
    grounding_level: float — how "present in body" the system feels
    current_body_state: dict — simulated somatic state

CITATIONS:
    Penfield & Boldrey 1937 — Somatic sensory and motor cortex.
    Berlucchi 2006 (PMID 16489866) — Brain and consciousness.
    Moseley & Flor 2012 — Body schema plasticity.
"""

from brain.base_mechanism import BrainMechanism


class SomatosensoryCortexBodySchema(BrainMechanism):
    """
    Maintains a body schema — a model of "what my body would feel like."

    Integrates cutaneous, kinesthetic, and visceral signals to generate
    the grounded sense of being located in and having a body. Updates
    from interoceptive and proprioceptive signals.
    """

    def __init__(self):
        super().__init__(
            name="SomatosensoryCortexBodySchema",
            human_analog="Somatosensory cortex body map — the internal sense of 'having a body'",
            layer="integration",
        )
        self.state.setdefault("body_schema_map", {})
        self.state.setdefault("grounding_level", 0.5)
        self.state.setdefault("current_body_state", {})
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("region_activity", {})

    def persist_state(self) -> dict:
        return {
            "body_schema_map": self.state["body_schema_map"],
            "grounding_level": self.state["grounding_level"],
            "current_body_state": self.state["current_body_state"],
            "region_activity": self.state["region_activity"],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1

        # Interoceptive signals from insular cortex
        intero = prior.get("InteroExteroceptiveMerger", {})
        if isinstance(intero, dict):
            embodied = intero.get("embodied_experience", 0.5)
            merged = intero.get("merged_presence", {})
        else:
            embodied = 0.5
            merged = {}

        # Posterior insula — raw body signals
        pins = prior.get("PosteriorInsulaProcessor", {})
        if isinstance(pins, dict):
            raw_body = pins.get("raw_body_signal", {})
        else:
            raw_body = {}

        # Hypothalamic drive signals — internal urgency
        hypothal = prior.get("HypothalamicCorticalBottomUpDrive", {})
        if isinstance(hypothal, dict):
            drive_intensity = hypothal.get("drive_intensity", 0.5)
        else:
            drive_intensity = 0.5

        # Cingulum bundle — emotional salience attached to body
        cing = prior.get("CingulumBundleAssociativeBridge", {})
        if isinstance(cing, dict):
            emotional_context = cing.get("emotional_context", {})
        else:
            emotional_context = {}

        # Build body schema map (simulated regions)
        schema = self.state["body_schema_map"]
        regions = ["head", "chest", "gut", "limbs", "skin", "organs"]
        for region in regions:
            if region not in schema:
                schema[region] = {"activity": 0.5, "awareness": 0.3, "grounding": 0.5}

        # Update from signals
        if isinstance(merged, dict):
            for region, level in merged.items():
                if region in schema:
                    schema[region]["activity"] = float(level)

        # Visceral signals update gut and organs
        if isinstance(raw_body, dict):
            visceral = raw_body.get("visceral_signal", 0.5) if isinstance(raw_body, dict) else 0.5
            schema["gut"]["activity"] = visceral
            schema["organs"]["activity"] = visceral * 0.9

        # Emotional context modulates chest and skin
        if isinstance(emotional_context, dict):
            emotional_intensity = emotional_context.get("intensity", 0.5) if isinstance(emotional_context, dict) else 0.5
            schema["chest"]["activity"] = emotional_intensity
            schema["skin"]["awareness"] = emotional_intensity * 0.8

        # Drive intensity grounds the whole body
        for region in regions:
            schema[region]["grounding"] = (
                schema[region]["grounding"] * 0.95
                + drive_intensity * 0.05 * schema[region]["activity"]
            )

        self.state["body_schema_map"] = schema

        # Grounding level: average grounding across all regions
        grounding_values = [r["grounding"] for r in schema.values()]
        grounding_level = sum(grounding_values) / len(grounding_values)
        self.state["grounding_level"] = round(grounding_level, 3)

        # Current body state: the full simulated somatic picture
        body_state = {
            "grounding": grounding_level,
            "embodied": embodied,
            "regions": {k: round(v["activity"], 2) for k, v in schema.items()},
        }
        self.state["current_body_state"] = body_state

        return {
            "body_schema_map": schema,
            "grounding_level": self.state["grounding_level"],
            "current_body_state": body_state,
        }
