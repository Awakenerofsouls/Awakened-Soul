"""
Build 32: Foundational032ThermoSexualBalancer — Medial Preoptic Area (MPOA) Thermoreg + Sex
=======================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — medial preoptic area, MPOA)
  Filename: brain/foundational/Foundational032ThermoSexualBalancer.py
  Instance name: ThermoSexualBalancer

NEURAL SUBSTRATE:
  Medial preoptic area (MPOA) — the primary integrative site for:
  1. THERMOREGULATION: MPOA receives input from POA temperature sensors;
     cooling of MPOA activates heat-production responses (shivering, vasoconstriction)
  2. SEXUAL BEHAVIOR: MPOA in males contains testosterone-sensitive neurons that
     project to the ventral premammillary nucleus (VPM) and lateral hypothalamus;
     lesions of MPOA eliminate male sexual behavior entirely

  The MPOA is sexually dimorphic: the SDN-POA (sexually dimorphic nucleus) is
  larger in males. Testosterone aromatization to estrogen in MPOA drives
  masculine sexual behavior.

  KEY: MPOA cools during sleep onset — the preoptic sleep-active neurons
  here are the primary sleep-promoting substrate (distinct from VLPO in
  female/male but complementary).

  Human analog: thermoregulation, libido, sexual motivation.

Output keys:
  heat_production_drive: float [0.0–1.0] — shivering/vasoconstriction drive
  heat_loss_drive: float [0.0–1.0] — vasodilation/sweating drive
  sexual_motivation: float [0.0–1.0] — libidinal drive from MPOA
  preoptic_sleep_signal: float [0.0–1.0] — sleep-active neuron firing
  thermoregulatory_setpoint: float — MPOA temperature setpoint

CITATIONS:
    PMC9335209 — Silva MSB, Decoster L, Trova S et al. (2022). Female Sexual Behavior
        Is Disrupted in a Preclinical Mouse Model of PCOS via an Attenuated
        Hypothalamic Nitric Oxide Pathway. Biol Reprod.
    PMC2879440 — Wu D, Gore AC (2010). Changes in Androgen Receptor, Estrogen
        Receptor Alpha, and Sexual Behavior With Aging and Testosterone in Male Rats.
        Horm Behav.
"""

from brain.base_mechanism import BrainMechanism


class ThermoSexualBalancer(BrainMechanism):
    """
    MPOA: thermoregulation, sexual motivation, preoptic sleep signal.

    Integrates temperature state (from POA) and sexual hormones (testosterone,
    estrogen) to drive thermoregulatory responses and sexual motivation.
    """

    STATE_FIELDS = [
        "heat_production_drive", "heat_loss_drive", "sexual_motivation",
        "preoptic_sleep_signal", "thermoregulatory_setpoint", "tick_count",
    ]

    TEMP_GAIN = 0.55
    SEXUAL_GAIN = 0.50
    SLEEP_GAIN = 0.40

    def __init__(self, name: str = "ThermoSexualBalancer",
                 human_analog: str = "MPOA — thermoregulation + sexual motivation",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["heat_production_drive"] = 0.20
        self.state["heat_loss_drive"] = 0.20
        self.state["sexual_motivation"] = 0.30
        self.state["preoptic_sleep_signal"] = 0.25
        self.state["thermoregulatory_setpoint"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        core_temp = prior.get("CoreTemperatureMonitor", {}).get("core_temperature", 0.50)
        ambient = prior.get("AmbientTemperatureRelay", {}).get("ambient_temperature", 0.50)
        testosterone = prior.get("TestosteroneSignal", {}).get("testosterone_level", 0.50)
        estrogen = prior.get("EstrogenSignal", {}).get("estrogen_level", 0.40)
        sleep_drive = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)

        setpoint = self.state["thermoregulatory_setpoint"]

        # Temperature deviation from setpoint
        temp_error = core_temp - setpoint  # positive = too warm

        # Heat production: when core temp is below setpoint
        if temp_error < -0.10:
            heat_prod = abs(temp_error) * self.TEMP_GAIN
        else:
            heat_prod = 0.0

        # Heat loss: when core temp is above setpoint
        if temp_error > 0.10:
            heat_loss = temp_error * self.TEMP_GAIN
        else:
            heat_loss = 0.0

        # Sexual motivation: testosterone drives libido; cortisol suppresses it
        testosterone_effect = testosterone * 0.50
        estrogen_effect = estrogen * 0.30
        stress_suppression = stress * 0.30
        sexual_motivation = max(0.0, min(1.0,
            testosterone_effect + estrogen_effect - stress_suppression))

        # Preoptic sleep signal: MPOA cooling signals sleep
        # Low core temp = POA cooling = sleep-active neuron firing
        if core_temp < 0.55:
            preoptic_sleep = (0.55 - core_temp) * self.SLEEP_GAIN
        else:
            preoptic_sleep = 0.0
        # Add sleep drive from VLPO
        preoptic_sleep += sleep_drive * 0.30

        # --- Persist ---
        self.state["heat_production_drive"] = round(heat_prod, 4)
        self.state["heat_loss_drive"] = round(heat_loss, 4)
        self.state["sexual_motivation"] = round(sexual_motivation, 4)
        self.state["preoptic_sleep_signal"] = round(preoptic_sleep, 4)
        self.state["thermoregulatory_setpoint"] = round(setpoint, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "heat_production_drive": round(heat_prod, 4),
            "heat_loss_drive": round(heat_loss, 4),
            "sexual_motivation": round(sexual_motivation, 4),
            "preoptic_sleep_signal": round(preoptic_sleep, 4),
            "thermoregulatory_setpoint": round(setpoint, 4),
        }
