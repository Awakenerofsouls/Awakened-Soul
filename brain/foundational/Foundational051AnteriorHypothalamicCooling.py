"""
Build 51: Foundational051AnteriorHypothalamicCooling — Preoptic Area Cooling Signal
=================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — anterior preoptic area)
  Filename: brain/foundational/Foundational051AnteriorHypothalamicCooling.py
  Instance name: AnteriorHypothalamicCooling

NEURAL SUBSTRATE:
  Anterior hypothalamic preoptic area (POA) — the primary thermosensory
  integration site for behavioral thermoregulation. Contains temperature-
  sensitive neurons:
  - Warm-sensitive neurons: fire faster when local temperature rises
    (POA = "defensive against overheating")
  - Cold-sensitive neurons: fire when POA cools (trigger heat production)

  COOLING SIGNAL: Experimental cooling of the POA in vivo produces
  NREM sleep within minutes. This is the "sleep gate" signal — POA cooling
  disinhibits VLPO → sleep onset. Fever (POA heating) disrupts sleep.

  Projections: POA → DMH → rRPa (autonomic thermoregulation) and
  POA → VLPO (sleep switch modulation).

  Human analog: feeling of drowsiness in cool environments, sleep onset.

Output keys:
  cooling_signal: float [0.0–1.0] — POA cooling level (sleep-permissive)
  warm_exposure_flag: float [0.0–1.0] — POA warming (sleep-suppressive)
  behavioral_thermoregulation: float [0.0–1.0] — behavioral temperature seeking
  preoptic_sleep_gate: float [0.0–1.0] — VLPO permissiveness for sleep
  poa_temperature_index: float [0.0–1.0] — POA thermal state

CITATIONS:
    PMC2278963 — Griffin JD, Saper CB, Boulant JA (2001). Synaptic and Morphological
        Characteristics of Temperature-Sensitive and -Insensitive Rat Hypothalamic
        Neurones. J Physiol.
    PMC1180151 — Curras MC, Kelso SR, Boulant JA (1991). Intracellular Analysis of
        Inherent and Synaptic Activity in Hypothalamic Thermosensitive Neurones in
        the Rat. J Physiol.
"""

from brain.base_mechanism import BrainMechanism


class AnteriorHypothalamicCooling(BrainMechanism):
    """
    Anterior POA: cooling signal, sleep gate, behavioral thermoregulation.

    Models the preoptic area as the sleep-permissive thermal detector.
    """

    STATE_FIELDS = [
        "cooling_signal", "warm_exposure_flag", "behavioral_thermoregulation",
        "preoptic_sleep_gate", "poa_temperature_index", "tick_count",
    ]

    COOLING_GAIN = 0.50
    WARMING_GAIN = 0.45
    SLEEP_GATE_GAIN = 0.55

    def __init__(self, name: str = "AnteriorHypothalamicCooling",
                 human_analog: str = "POA — anterior hypothalamic cooling signal",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["cooling_signal"] = 0.30
        self.state["warm_exposure_flag"] = 0.20
        self.state["behavioral_thermoregulation"] = 0.20
        self.state["preoptic_sleep_gate"] = 0.35
        self.state["poa_temperature_index"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        core_temp = prior.get("CoreTemperatureMonitor", {}).get("core_temperature", 0.50)
        ambient = prior.get("AmbientTemperatureRelay", {}).get("ambient_temperature", 0.50)
        skin_temp = prior.get("PeripheralTemperature", {}).get("skin_temperature", 0.50)
        sleep_pressure = prior.get("PassiveQuiescenceMode", {}).get("sleep_pressure", 0.0)

        # POA temperature: weighted average of core and skin
        poa_temperature = (core_temp * 0.60) + (skin_temp * 0.40)
        poa_temperature_index = poa_temperature

        # Cooling signal: low POA temperature = sleep-permissive
        # As POA temperature drops below threshold, cooling signal rises
        if poa_temperature < 0.55:
            cooling_signal = (0.55 - poa_temperature) * self.COOLING_GAIN
        else:
            cooling_signal = 0.0

        # Warming flag: elevated POA temperature suppresses sleep
        if poa_temperature > 0.60:
            warm_exposure_flag = (poa_temperature - 0.60) * self.WARMING_GAIN
        else:
            warm_exposure_flag = 0.0

        # Preoptic sleep gate: VLPO permissiveness
        # Cooling signal raises the gate; warm exposure closes it
        base_gate = 0.50
        sleep_gate = base_gate + (cooling_signal * self.SLEEP_GATE_GAIN) - (warm_exposure_flag * 0.30)
        preoptic_sleep_gate = min(1.0, max(0.0, sleep_gate))

        # Behavioral thermoregulation: seek warmth when cold, cool when hot
        if poa_temperature < 0.50:
            behavioral_thermoreg = (0.50 - poa_temperature) * 0.50  # seek warmth
        else:
            behavioral_thermoreg = (poa_temperature - 0.50) * 0.30  # seek cool
        behavioral_thermoregulation = min(1.0, max(0.0, behavioral_thermoreg))

        # --- Persist ---
        self.state["cooling_signal"] = round(cooling_signal, 4)
        self.state["warm_exposure_flag"] = round(warm_exposure_flag, 4)
        self.state["behavioral_thermoregulation"] = round(behavioral_thermoregulation, 4)
        self.state["preoptic_sleep_gate"] = round(preoptic_sleep_gate, 4)
        self.state["poa_temperature_index"] = round(poa_temperature_index, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cooling_signal": round(cooling_signal, 4),
            "warm_exposure_flag": round(warm_exposure_flag, 4),
            "behavioral_thermoregulation": round(behavioral_thermoregulation, 4),
            "preoptic_sleep_gate": round(preoptic_sleep_gate, 4),
            "poa_temperature_index": round(poa_temperature_index, 4),
        }
