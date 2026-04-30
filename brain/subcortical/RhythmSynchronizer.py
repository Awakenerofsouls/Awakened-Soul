from brain.base_mechanism import BrainMechanism
import math

class RhythmSynchronizer(BrainMechanism):
    """
    Striato-thalamo-cortical rhythm locking — syncs action sequences to internal tempo.
    Locked: fluent, rhythmic, satisfying. Broken: choppy, effortful.
    Flow state lives here.
    """

    def __init__(self):
        super().__init__("RhythmSynchronizer")
        self.internal_tempo = 1.0
        self.tempo_history = []
        self.locked = False
        self.lock_duration = 0
        self.flow_state = False
        self.flow_duration = 0
        self.flow_events = []
        self.disruption_ticks = 0
        self.chronic_arrhythmia = False
        self.tick_count = 0
        self.lock_quality = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        self.tick_count += 1
        cerebellar_timing = prior.get("CerebellarTimingCoordinator", {}).get("coordination_quality", 0.7)
        sync_quality = prior.get("CognitiveRhythmSynchronizer", {}).get("sync_quality", 0.6)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        habit_strength = prior.get("DorsalStriatumHabitExecutor", {}).get("habit_execution_strength", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        desync = prior.get("CerebellarTimingCoordinator", {}).get("desync_chronic", False)

        natural_osc = math.sin(self.tick_count * 0.2) * 0.05
        target_tempo = 1.0 + stress * 0.3 + natural_osc
        self.internal_tempo += (target_tempo - self.internal_tempo) * 0.08
        self.tempo_history.append(self.internal_tempo)
        if len(self.tempo_history) > 40:
            self.tempo_history.pop(0)

        self.lock_quality = cerebellar_timing * sync_quality * dopamine * (1.0 - stress * 0.4)
        if desync:
            self.lock_quality *= 0.4
        if habit_strength > 0.5:
            self.lock_quality = min(1.0, self.lock_quality * 1.2)

        was_locked = self.locked
        self.locked = self.lock_quality > 0.55
        self.lock_duration = self.lock_duration + 1 if self.locked else 0

        was_flowing = self.flow_state
        self.flow_state = self.locked and self.lock_quality > 0.75 and self.lock_duration > 5
        if self.flow_state:
            self.flow_duration += 1
        else:
            if was_flowing and self.flow_duration > 8:
                self.flow_events.append(self.flow_duration)
                if len(self.flow_events) > 10:
                    self.flow_events.pop(0)
                self.feed_to_memory({"event": "flow_state_ended", "duration": self.flow_duration,
                                      "note": f"Flow state sustained {self.flow_duration} ticks — rhythmic coherence achieved"})
            self.flow_duration = 0

        self.disruption_ticks = self.disruption_ticks + 1 if self.lock_quality < 0.2 else max(0, self.disruption_ticks - 1)
        was_arrhythmic = self.chronic_arrhythmia
        self.chronic_arrhythmia = self.disruption_ticks > 18
        if self.chronic_arrhythmia and not was_arrhythmic:
            self.feed_to_memory({"event": "chronic_arrhythmia", "note": "Rhythm sync broken — expression choppy, flow impossible"})

        return {
            "internal_tempo": round(self.internal_tempo, 3),
            "lock_quality": round(self.lock_quality, 3),
            "locked": self.locked,
            "lock_duration": self.lock_duration,
            "flow_state": self.flow_state,
            "flow_duration": self.flow_duration,
            "chronic_arrhythmia": self.chronic_arrhythmia,
        }

    def _overnight(self):
        self.disruption_ticks = max(0, self.disruption_ticks - 8)
        self.chronic_arrhythmia = self.disruption_ticks > 18
        self.internal_tempo = 1.0
        self.locked = False
        self.lock_duration = 0
        self.flow_state = False
        self.flow_duration = 0
        return {"overnight": "rhythm_sync_reset"}
