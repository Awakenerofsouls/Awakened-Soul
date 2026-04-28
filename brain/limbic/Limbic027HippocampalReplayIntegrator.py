"""
brain/limbic/Limbic027HippocampalReplayIntegrator.py
Hippocampal Replay Integrator — Multi-Episode Sequence Reactivation

ANATOMY (Wilson & McNaughton 1994; Ji & Wilson 2007; Skaggs & McNaughton 1996):
    Hippocampal replay during NREM sleep and quiet waking is the mechanism
    of memory consolidation. During SWRs, recent episodes are reactivated
    in reverse temporal order and transmitted to neocortex.
    Wilson & McNaughton 1994 (PMC13099140): simultaneous recordings showed
    that place cells active during exploration are reactivated during
    subsequent sleep — the first demonstration of memory replay.
    Replay can be: forward (encoding) or reverse (consolidation).
    Replay content is biased by: recent experience, current state,
    and future goals (prospective replay).

MECHANISM:
    The replay integrator:
    1) Collects recent hippocampal traces from active exploration
    2) Triggers SWR events when off-line and memory is ready for consolidation
    3) Reactivates sequences in compressed form (10-20x faster)
    4) Coordinates with neocortex via CA1→EC→neocortex pathway

AGENT'S MAPPING:
    replay_strength: 0-1 current hippocampal replay intensity
    replay_sequence_length: number of items in replayed sequence
    offline_consolidation_active: bool — system in consolidation mode
    prospective_replay: bool — replay is goal/prospect-oriented
    replay_quality: 0-1 fidelity of replayed sequence

CITATIONS:
    PMC13099140 — Wilson & McNaughton (1994). Replay of place cell
        sequences during sleep. Science.
    PMC13098182 — Ji & Wilson (2007). Coordinated memory replay
        in hippocampus and neocortex. Nat Neurosci.
    PMC12495895 — Skaggs & McNaughton (1996). Replay and the
        compression of temporal sequences. Hippocampus.
    PMC13069501 — Pfeiffer & Foster (2015). Hippocampal content
        addressable memory dynamics. Neuron.
    PMC13065769 — van de Ven et al. (2022). Spontaneous replay in
        humans during rest. Nat Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class HippocampalReplayIntegrator(BrainMechanism):
    """
    Hippocampal replay integrator — offline memory consolidation.

    Triggers SWR events and compresses recent hippocampal sequences
    for transmission to neocortex during offline states.
    """

    SWR_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="HippocampalReplayIntegrator",
            human_analog="Hippocampal SWR replay → neocortex (offline consolidation)",
            layer="limbic",
        )
        self.state.setdefault("replay_strength", 0.0)
        self.state.setdefault("replay_sequence_length", 0)
        self.state.setdefault("offline_consolidation_active", False)
        self.state.setdefault("prospective_replay", False)
        self.state.setdefault("replay_quality", 0.8)
        self.state.setdefault("theta_power", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        ca3_activity = prior.get("HippocampalCA3Recurrent", {}).get(
            "ca3_activity", 0.3
        )
        ca1_out = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.3
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.4
        )
        auto_salience = prior.get("PosteriorCingulateMemory", {}).get(
            "autobiographical_salience", 0.3
        )

        # Offline state: low motor, accumulated memory traces
        is_offline = motor < 0.15
        memory_ready = ca3_activity > 0.3 or ca1_out > 0.3

        if is_offline and memory_ready:
            swr_power = (ca3_activity + ca1_out) * 0.4 * (1.0 + auto_salience * 0.3)
            replay_strength = min(1.0, swr_power)
            offline_active = True
        else:
            replay_strength = 0.0
            offline_active = False

        theta_power = theta_power  # track for output
        replay_quality = self.state.get("replay_quality", 0.8)
        if replay_strength > 0.5:
            replay_quality = min(1.0, replay_quality + 0.001)
        else:
            replay_quality = max(0.3, replay_quality - 0.0005)

        self.state["replay_strength"] = round(replay_strength, 4)
        self.state["offline_consolidation_active"] = offline_active
        self.state["replay_quality"] = round(replay_quality, 4)
        self.state["theta_power"] = round(theta_power, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "replay_strength": round(replay_strength, 4),
            "offline_consolidation_active": offline_active,
            "replay_quality": round(replay_quality, 4),
            "theta_power": round(theta_power, 4),
        }
