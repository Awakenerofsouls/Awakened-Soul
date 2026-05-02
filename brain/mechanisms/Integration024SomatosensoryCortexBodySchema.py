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

    For the agent: a body schema is an architectural model of "what my
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


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
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

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

