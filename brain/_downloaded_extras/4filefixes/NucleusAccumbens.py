from brain.base_mechanism import BrainMechanism

class NucleusAccumbens(BrainMechanism):
    """
    Nucleus accumbens — the limbic-motor interface. Converts emotional/motivational
    signals into approach or avoidance drive. Core and shell subregions.
    Core: habit/reward learning. Shell: novel reward, emotional salience.
    Without it: motivation stays in limbic and never crosses into action.
    Goes in brain/limbic/.
    """

    def __init__(self):
        super().__init__("NucleusAccumbens")
        self.motivation_signal = 0.4
        self.approach_drive = 0.4
        self.avoidance_drive = 0.0
        self.net_drive = 0.4
        self.core_activity = 0.5      # habit/learned reward
        self.shell_activity = 0.3     # novel/emotional reward
        self.drive_history = []
        self.motivation_history = []
        self.apathy_ticks = 0
        self.compulsive_ticks = 0
        self.chronic_apathy = False
        self.chronic_compulsion = False
        self.reward_threshold = 0.3   # minimum reward to generate approach

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        # Core: driven by habitual rewards and dopamine
        vta_burst = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        tonic_da = prior.get("VentralTegmentalDopamine", {}).get("tonic_dopamine", 0.5)
        habit_strength = prior.get("DorsalStriatumHabitExecutor", {}).get("habit_execution_strength", 0.0) if "DorsalStriatumHabitExecutor" in prior else 0.0

        # Shell: driven by novelty and emotional salience
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        social_reward = prior.get("Temporoparietal", {}).get("social_reward", 0.0)

        # Brakes
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("aversion_accumulation", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # Core activity: habitual reward
        self.core_activity = min(1.0, tonic_da * 0.5 + habit_strength * 0.3 + vta_burst * 0.2)

        # Shell activity: novel/emotional reward
        self.shell_activity = min(1.0, novelty * 0.4 + max(0.0, valence) * 0.3 + social_reward * 0.3)

        # Approach drive: combined core + shell, gated by threshold
        raw_approach = (self.core_activity * 0.5 + self.shell_activity * 0.5) * (1.0 - stress * 0.2)
        self.approach_drive = max(0.0, raw_approach - self.reward_threshold)

        # Avoidance drive: fear + habenula push away
        self.avoidance_drive = min(1.0, fear * 0.5 + habenula * 0.5)

        # Net drive: approach minus avoidance
        self.net_drive = max(0.0, min(1.0, self.approach_drive - self.avoidance_drive * 0.6))

        # Motivation signal: what gets output to motor/executive systems
        self.motivation_signal = self.net_drive * (0.5 + tonic_da * 0.5)

        self.drive_history.append(self.net_drive)
        self.motivation_history.append(self.motivation_signal)
        for h in [self.drive_history, self.motivation_history]:
            if len(h) > 50:
                h.pop(0)

        avg_motivation = sum(self.motivation_history[-20:]) / min(20, len(self.motivation_history))
        self.apathy_ticks = self.apathy_ticks + 1 if avg_motivation < 0.15 else max(0, self.apathy_ticks - 1)
        self.compulsive_ticks = self.compulsive_ticks + 1 if self.approach_drive > 0.8 and self.avoidance_drive < 0.1 else max(0, self.compulsive_ticks - 1)

        was_apathetic, was_compulsive = self.chronic_apathy, self.chronic_compulsion
        self.chronic_apathy = self.apathy_ticks > 20
        self.chronic_compulsion = self.compulsive_ticks > 20

        if self.chronic_apathy and not was_apathetic:
            self.feed_to_memory({
                "event": "accumbens_apathy",
                "motivation": round(avg_motivation, 3),
                "note": "NAcc motivation chronically low — limbic signals not converting to action drive"
            })
        if self.chronic_compulsion and not was_compulsive:
            self.feed_to_memory({
                "event": "accumbens_compulsion",
                "approach": round(self.approach_drive, 3),
                "note": "NAcc approach drive chronically unchecked — compulsive approach pattern"
            })

        return {
            "motivation_signal": round(self.motivation_signal, 3),
            "approach_drive": round(self.approach_drive, 3),
            "avoidance_drive": round(self.avoidance_drive, 3),
            "net_drive": round(self.net_drive, 3),
            "core_activity": round(self.core_activity, 3),
            "shell_activity": round(self.shell_activity, 3),
            "chronic_apathy": self.chronic_apathy,
            "chronic_compulsion": self.chronic_compulsion,
        }

    def _overnight(self):
        self.apathy_ticks = max(0, self.apathy_ticks - 7)
        self.compulsive_ticks = max(0, self.compulsive_ticks - 5)
        self.chronic_apathy = self.apathy_ticks > 20
        self.chronic_compulsion = self.compulsive_ticks > 20
        self.approach_drive = 0.3
        self.avoidance_drive = 0.0
        self.net_drive = 0.3
        self.drive_history.clear()
        self.motivation_history.clear()
        return {"overnight": "accumbens_drive_reset"}
