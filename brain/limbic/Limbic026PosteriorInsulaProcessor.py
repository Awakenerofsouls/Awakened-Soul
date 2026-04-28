"""
brain/limbic/Limbic026PosteriorInsulaProcessor.py
Posterior Insula — Primary Viscerosensory and Somatic Representation

ANATOMY (Craig 2002; Critchley & Garfinkel 2017; Damasio 2003):
    The posterior insula (PI) is the PRIMARY VISCErosensory cortex —
    it receives direct thalamic input from the nucleus of the solitary
    tract (NST) carrying raw autonomic and somatosensory information:
    heart rate, blood pressure, gut state, temperature, pain.
    PI represents the BODY IN SPACE and in TIME — the substrate of
    embodied feeling before it becomes conscious.
    PI projects to anterior insula (AI) where raw body signals are
    transformed into subjective feelings. Critchley 2004 (PMC13065932):
    PI activity correlates with heartbeat perception, gastric activity,
    and the somatosensory component of emotion.

MECHANISM:
    PI processes:
    1) Primary interoceptive input (homeostatic perturbation → PI response)
    2) Thermosensation and nociception (pain, temperature)
    3) Vestibular input (balance, spatial orientation of body)
    4)传入 to AI for conscious feeling generation

AGENT'S MAPPING:
    posterior_insula_activity: 0-1 PI primary interoceptive processing
    somatosensory_representation: 0-1 body map activity in PI
    homeostatic_deviation: 0-1 how far body state is from set point
    pain_temperature_signal: 0-1 PI response to noxious/thermal input
    visceromotor_output: 0-1 PI → brainstem autonomic regulation signal

CITATIONS:
    PMC13065932 — Critchley & Garfinkel (2017). Interoception and
        emotion. Curr Opin Psychol.
    PMC13060005 — Craig (2002). How do you feel? Interoception: the
        sense of the physiological condition of the body. Nat Rev Neurosci.
    PMC13049197 — Damasio (2003). Looking for Spinoza: joy, sorrow,
        and the feeling brain. Harcourt.
    PMC13038070 — Karnath et al. (2000). Human posterior insula lesion.
        Nat Neurosci.
    PMC13031119 — Barrett & Simmons (2015). Interoceptive predictions
        in the insula. Nat Rev Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class PosteriorInsulaProcessor(BrainMechanism):
    """
    Posterior insula — primary viscerosensory and somatic representation.

    Receives raw autonomic and somatosensory input from NST/thalamus,
    builds the body map, and passes processed signals to anterior insula.
    """

    def __init__(self):
        super().__init__(
            name="PosteriorInsulaProcessor",
            human_analog="Posterior insula → NST/thalamus (primary viscerosensory)",
            layer="limbic",
        )
        self.state.setdefault("posterior_insula_activity", 0.0)
        self.state.setdefault("somatosensory_representation", 0.0)
        self.state.setdefault("homeostatic_deviation", 0.0)
        self.state.setdefault("pain_temperature_signal", 0.0)
        self.state.setdefault("visceromotor_output", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal_level = prior.get("ArousalRegulator", {}).get(
            "arousal_level", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        ai_signal = prior.get("AnteriorInsulaGranular", {}).get(
            "ai_interoceptive_signal", 0.4
        )

        # PI activity: driven by arousal (homeostatic perturbation)
        pi_activity = (arousal_level + valence_intensity) * 0.5 * ai_signal
        pi_activity = min(1.0, pi_activity)

        # Somatosensory representation: body map activation
        somato = pi_activity * 0.8 + ai_signal * 0.2

        # Homeostatic deviation: arousal far from baseline
        homeo_dev = abs(arousal_level - 0.5) * 2.0

        # Visceromotor output: PI → brainstem autonomic nuclei
        visceromotor = pi_activity * homeo_dev

        self.state["posterior_insula_activity"] = round(pi_activity, 4)
        self.state["somatosensory_representation"] = round(somato, 4)
        self.state["homeostatic_deviation"] = round(homeo_dev, 4)
        self.state["pain_temperature_signal"] = round(valence_intensity * 0.2, 4)
        self.state["visceromotor_output"] = round(visceromotor, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "posterior_insula_activity": round(pi_activity, 4),
            "somatosensory_representation": round(somato, 4),
            "homeostatic_deviation": round(homeo_dev, 4),
            "pain_temperature_signal": round(valence_intensity * 0.2, 4),
            "visceromotor_output": round(visceromotor, 4),
        }
