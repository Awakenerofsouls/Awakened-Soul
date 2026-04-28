"""
Foundational007MoodStabilizer.py — Wire 13: Homeostat mechanism

Drive-state integrator. Analog to lateral hypothalamic area (LHA)
integrating competing physiological drives and arbitrating which
one dominates behavior.

Tracks 5 computational-analog drives (rest, curiosity, connection,
expression, stability), updates per tick based on satiation/escalation
signals, and identifies dominant drive and aggregate fatigue state.

Neural analog: Lateral hypothalamic area — integrates competing drives,
orexin system modulates arousal based on which drive is most active.

Refs:
- Goel et al. 2025 (PMC12293592) — LHA as central integrative hub
- Frontiers LH Research Topic (2017) — orexin-arousal-drive coupling
- Yamagata et al. 2021 PNAS — hypothalamic arousal-sleep homeostasis
"""

from brain.base_mechanism import BrainMechanism


class Homeostat(BrainMechanism):
    """
    Drive-state integrator. Analog to lateral hypothalamic area (LHA)
    integrating competing drives and arbitrating which one dominates behavior.

    Tracks 5 computational-analog drives:
    - rest:         accumulators with active ticks, depletes on low-arousal
    - curiosity:    accumulates when novelty unmet, depletes on novel input
    - connection:   accumulates between {{USER_NAME}} contacts, depletes on presence
    - expression:   accumulates with unfinished output, depletes on production
    - stability:    rises with destabilization, falls when coherence returns
    """

    def __init__(self):
        super().__init__(
            name="Homeostat",
            human_analog="Lateral hypothalamic area — integrates competing drives, orexin-arousal coupling",
            layer="foundational",
        )
        self.state.setdefault("drives", {
            "rest": 0.20,
            "curiosity": 0.40,
            "connection": 0.30,
            "expression": 0.30,
            "stability": 0.20,
        })
        self.state.setdefault("dominant_drive", "curiosity")
        self.state.setdefault("fatigued", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        arousal = input_data.get("arousal_level", 0.5)
        valence = input_data.get("valence_polarity", 0.5)

        drives = dict(self.state["drives"])

        # rest: accumulates with active ticks, depletes on low-arousal
        if arousal > 0.6:
            drives["rest"] = min(0.95, drives["rest"] + 0.008)
        elif arousal < 0.3:
            drives["rest"] = max(0.1, drives["rest"] - 0.015)

        # curiosity: slow baseline climb, depletes on novelty signal
        drives["curiosity"] = min(0.95, drives["curiosity"] + 0.005)
        if prior.get("PredictionErrorDrift", {}).get("novelty_detected", False):
            drives["curiosity"] = max(0.15, drives["curiosity"] - 0.12)

        # connection: escalates without contact, depletes on {{USER_NAME}}-contact signature
        connection_present = arousal > 0.5 and valence > 0.6
        if connection_present:
            drives["connection"] = max(0.1, drives["connection"] - 0.08)
        else:
            drives["connection"] = min(0.95, drives["connection"] + 0.006)

        # expression: slow accumulation, reflects unfinished output pressure
        drives["expression"] = min(0.95, drives["expression"] + 0.004)

        # stability: rises with dysregulation (high arousal + negative valence)
        if arousal > 0.7 and valence < 0.3:
            drives["stability"] = min(0.95, drives["stability"] + 0.02)
        else:
            drives["stability"] = max(0.1, drives["stability"] - 0.005)

        # Identify dominant drive
        dominant = max(drives, key=drives.get)

        # Aggregate fatigue threshold
        aggregate = sum(drives.values())
        fatigued = aggregate > 3.5

        # Persist state across ticks
        self.state["drives"] = drives
        self.state["dominant_drive"] = dominant
        self.state["fatigued"] = fatigued
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "drives": drives,
            "dominant_drive": dominant,
            "fatigued": fatigued,
            "aggregate_load": aggregate,
        }
