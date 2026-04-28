"""
Foundational006VigilanceToner.py — Build 3: ArousalRegulator

Locus coeruleus-norepinephrine arousal regulator.

Maintains tonic baseline arousal (slow-varying, 0.0-1.0 continuous)
and phasic burst state (fast, event-triggered), derives cognitive mode
from their combination per Aston-Jones adaptive gain theory.

Neural analog: Locus coeruleus (LC) in pontine brainstem, principal
site of norepinephrine (NE) synthesis. Tonic 1-3 Hz firing = optimal
arousal range. Phasic 10-15 Hz bursts = triggered by salient stimuli
and prediction errors.

Refs:
- Unsworth & Robison 2022 (PMC9514025) — LC-NE arousal continuum
- LC-NA Narrative Review (PMC12409474) — tonic/phasic firing modes
- Howells et al. 2012 (PubMed 22399276) — synergistic tonic/phasic
- Aston-Jones & Cohen 2005 — adaptive gain theory
- Tsukahara & Engle 2021 PNAS (PMC8570396) — phasic/exploitative mode
- Nature Neuroscience 2024 — tonic vs burst network effects
"""

from brain.base_mechanism import BrainMechanism


class ArousalRegulator(BrainMechanism):
    """
    Locus coeruleus-norepinephrine arousal regulator.

    Tonic baseline (slow drift) + phasic burst (event-triggered).
    Composite arousal_level, cognitive mode classification,
    and cross-mechanism integration with Homeostat and
    PredictionErrorDrift.
    """

    TONIC_BASELINE = 0.55       # midrange default: "normal waking alertness"
    TONIC_DECAY = 0.02          # return to baseline rate per tick
    PHASIC_DECAY = 0.25          # phasic bursts decay fast (300-700ms refractory)
    PHASIC_BURST_THRESHOLD = 0.4  # surprise above this triggers phasic burst

    HYPOAROUSED_THRESHOLD = 0.20
    HYPERAROUSED_THRESHOLD = 0.80

    # Drive → tonic bias mapping
    DRIVE_BIAS = {
        "rest": -0.10,       # rest suppresses arousal
        "curiosity": 0.05,   # curiosity mildly elevates
        "connection": 0.08,  # connection-seeking = elevated
        "expression": 0.05,
        "stability": -0.05,  # stability-seeking = seek calm
    }

    def __init__(self):
        super().__init__(
            name="ArousalRegulator",
            human_analog="Locus coeruleus — norepinephrine tonic/phasic arousal regulation",
            layer="foundational",
        )
        self.state.setdefault("tonic_level", self.TONIC_BASELINE)
        self.state.setdefault("phasic_burst", 0.0)
        self.state.setdefault("last_mode", "reflective")
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        stage = input_data.get("stage", "live")

        # --- Tonic dynamics ---
        stage_baseline = {
            "live": 0.55,
            "overnight": 0.30,
            "idle": 0.40,
        }.get(stage, 0.55)

        # Homeostat fatigue depresses tonic baseline
        fatigued = prior.get("Homeostat", {}).get("fatigued", False)
        if fatigued:
            stage_baseline -= 0.15

        # Dominant drive shapes tonic drift
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")
        drive_bias = self.DRIVE_BIAS.get(dominant_drive, 0.0)
        effective_baseline = max(0.05, min(0.95, stage_baseline + drive_bias))

        # Tonic drifts toward effective baseline
        current_tonic = self.state["tonic_level"]
        delta = (effective_baseline - current_tonic) * self.TONIC_DECAY
        new_tonic = max(0.0, min(1.0, current_tonic + delta))

        # --- Phasic dynamics ---
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        current_phasic = self.state["phasic_burst"]

        if surprise > self.PHASIC_BURST_THRESHOLD:
            # Burst fires — amplitude proportional to surprise
            new_phasic = min(1.0, current_phasic + surprise * 0.6)
        else:
            # Decay existing burst
            new_phasic = max(0.0, current_phasic - self.PHASIC_DECAY)

        phasic_burst_active = new_phasic > 0.3

        # --- Composite arousal level ---
        arousal_level = min(1.0, new_tonic + new_phasic * 0.4)

        # --- Mode classification (Aston-Jones adaptive gain) ---
        hypoaroused = new_tonic < self.HYPOAROUSED_THRESHOLD
        hyperaroused = new_tonic > self.HYPERAROUSED_THRESHOLD

        # Creative: moderate tonic + phasic burst (exploitative focus)
        creative_mode = 0.40 <= new_tonic <= 0.70 and phasic_burst_active

        # Reflective: moderate-low tonic, no phasic (associative processing)
        reflective_mode = 0.30 <= new_tonic <= 0.55 and not phasic_burst_active

        if hypoaroused:
            mode = "hypoaroused"
        elif hyperaroused:
            mode = "hyperaroused"
        elif creative_mode:
            mode = "creative"
        elif reflective_mode:
            mode = "reflective"
        else:
            mode = "alert"

        # Persist
        self.state["tonic_level"] = new_tonic
        self.state["phasic_burst"] = new_phasic
        self.state["last_mode"] = mode
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "arousal_level": round(arousal_level, 4),
            "creative_mode": creative_mode,
            "reflective_mode": reflective_mode,
            "hyperaroused": hyperaroused,
            "hypoaroused": hypoaroused,
            "tonic_level": round(new_tonic, 4),
            "phasic_burst_active": phasic_burst_active,
            "mode": mode,
        }
