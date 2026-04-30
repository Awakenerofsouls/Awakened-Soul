"""
SurvivalOrchestrator — Survival Circuit Coordinator / Defense-Drive Hub

NEURAL SUBSTRATE
================
The SurvivalOrchestrator is a high-level integrator coordinating defense
+ feeding + reproduction + thermoregulation + fluid balance under a
unified "survival priority" framework. Not a single anatomical nucleus
but a functional integrator that arbitrates among competing survival
demands. Anatomically distributed across central amygdala, BNST, PAG,
hypothalamic defense areas (VMHdm, AHN), feeding circuits, and
homeostatic substrates.

Theoretical framework: LeDoux 2012 "survival circuits" — discrete
behavioral repertoires (defense, energy management, fluid balance,
thermoregulation, reproduction, social bonding) each with dedicated
circuitry that gets selectively activated by ecological challenges.
The orchestrator coordinates these circuits to prevent conflict (e.g.,
not defending against predator while drinking).

Allostasis framework (Sterling & Eyer 1988) — body maintains stability
through anticipatory adjustment, not strict homeostasis. SurvivalOrch
implements predictive allostatic regulation by reading current threat,
energy, fluid, thermal, social state and assigning priority weights.

Damasio 1996 somatic marker hypothesis — survival decisions integrate
visceral state ("gut feeling") via insula + vmPFC into action selection.
The orchestrator outputs a survival priority signal that biases motor
+ cognitive selection toward the most urgent survival demand.

Six survival drive dimensions (LeDoux 2012):
1. Defense — predator avoidance, freezing, escape
2. Energy management — feeding, foraging, satiety
3. Fluid balance — thirst, drinking
4. Thermoregulation — heat seeking/loss
5. Reproduction — mating, territorial, parental
6. Social bonding — affiliation, attachment

KEY FINDINGS
============
1. Survival circuits are discrete behavioral repertoires with dedicated
   neural substrates; selectively activated by ecological challenges —
   [LeDoux 2012, Neuron 73:653, doi:10.1016/j.neuron.2012.02.004]
2. Allostasis: body achieves stability through anticipatory adjustment,
   not strict homeostasis; predictive regulation —
   [Sterling 2012, Physiol Behav 106:5, doi:10.1016/j.physbeh.2011.06.004]
3. Somatic marker hypothesis: survival/value decisions integrate
   visceral state via vmPFC + insula —
   [Damasio 1996, Phil Trans R Soc B 351:1413, PMID 8941953]
4. Defense circuits: PAG + central amygdala + VMHdm coordinate
   freezing/escape based on predator distance + threat type —
   [Tovote 2015, Nat Rev Neurosci 16:317, doi:10.1038/nrn3945]
5. Cannon's emergency response framework: sympathetic-adrenal axis
   coordinates fight-or-flight; foundational survival physiology —
   [Cannon 1929, Bodily Changes in Pain Hunger Fear and Rage, Appleton-Century-Crofts]

INPUTS (from prior_results)
============================
- ValenceTagger.aversive_signal, .threat_signal
- VitalCoreRegulator.vital_drive, .survival_threat_level
- AppetiteNPYBalancer.hunger_signal
- FluidBalanceWatcher.thirst_drive (or osmotic_signal)
- ThermoregulationCore.core_temp_proxy
- ArousalRegulator.tonic_level
- CRHStressDispatcher.crh_release
- VentromedialHypothalamus.vmhdm_defense_drive (when present)

OUTPUTS (to brain_runner enrichment)
=====================================
- defense_priority (0-1): predator/threat priority weight
- energy_priority (0-1): feeding/foraging priority weight
- fluid_priority (0-1): drinking priority weight
- thermal_priority (0-1): thermoregulation priority weight
- reproductive_priority (0-1): mating priority weight
- social_priority (0-1): social bonding priority weight
- dominant_drive (str): currently winning survival drive
- urgency_score (0-1): aggregate survival urgency
- survival_state (str): one of survival modes
"""

from brain.base_mechanism import BrainMechanism


class SurvivalOrchestrator(BrainMechanism):
    """High-level survival-circuit coordinator + drive arbitrator."""

    SMOOTH = 0.20
    URGENCY_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="SurvivalOrchestrator",
            human_analog="Survival circuit coordinator (defense + drives)",
            layer="foundational",
        )
        self.state.setdefault("defense_priority", 0.0)
        self.state.setdefault("energy_priority", 0.0)
        self.state.setdefault("fluid_priority", 0.0)
        self.state.setdefault("thermal_priority", 0.0)
        self.state.setdefault("reproductive_priority", 0.0)
        self.state.setdefault("social_priority", 0.0)
        self.state.setdefault("dominant_drive", "none")
        self.state.setdefault("urgency_score", 0.0)
        self.state.setdefault("survival_state", "quiet")
        self.state.setdefault("recent_dominant", [])
        self.state.setdefault("tick_count", 0)

    def _defense_priority(self, aversive: float, threat: float,
                            vmhdm: float, vital_threat: float) -> float:
        """Defense priority — driven by acute threat signals (LeDoux 2012,
        Tovote 2015)."""
        return min(1.0, aversive * 0.30 + threat * 0.30 + vmhdm * 0.20
                    + vital_threat * 0.20)

    def _energy_priority(self, hunger: float, vital_drive: float) -> float:
        """Energy priority — hunger + low energy signal."""
        return min(1.0, hunger * 0.7 + max(0.0, 0.5 - vital_drive) * 0.6)

    def _fluid_priority(self, thirst: float, osmotic: float) -> float:
        """Fluid priority — thirst + osmotic deviation (Sterling 2012
        allostasis)."""
        return min(1.0, thirst * 0.6 + osmotic * 0.4)

    def _thermal_priority(self, core_temp: float) -> float:
        """Thermal priority — deviation from ~0.5 setpoint."""
        deviation = abs(core_temp - 0.5)
        if deviation < 0.10:
            return 0.0
        return min(1.0, (deviation - 0.10) * 4.0)

    def _reproductive_priority(self, social: bool, defense: float,
                                  energy: float) -> float:
        """Reproductive priority — only active when defense + energy low."""
        if defense > 0.30 or energy > 0.50:
            return 0.0  # other priorities dominate
        if not social:
            return 0.0
        return 0.30

    def _social_priority(self, social: bool, defense: float,
                          arousal: float) -> float:
        """Social bonding priority — when safe + alert."""
        if defense > 0.30 or not social:
            return 0.0
        return min(1.0, max(0.0, arousal - 0.40) * 0.7)

    def _arbitrate(self, priorities: dict) -> tuple:
        """Arbitrate among competing priorities. Defense wins when high
        (Cannon 1929 fight-or-flight). Otherwise highest priority wins.
        """
        if priorities["defense"] > 0.40:
            return "defense", priorities["defense"]
        # Find max
        best = max(priorities.items(), key=lambda x: x[1])
        return best

    def _classify_state(self, dominant: str, urgency: float) -> str:
        """Classify survival state."""
        if urgency < 0.10:
            return "quiet"
        if dominant == "defense" and urgency > 0.50:
            return "defense_engaged"
        if urgency > self.URGENCY_THRESHOLD:
            return f"{dominant}_engaged"
        return f"{dominant}_active"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))
        threat = float(valence.get("threat_signal", aversive))
        social = bool(valence.get("social_context", False))

        vital_data = prior.get("VitalCoreRegulator", {})
        vital_drive = float(vital_data.get("vital_drive", 0.5))
        vital_threat = float(vital_data.get("survival_threat_level", 0.0))

        appetite = prior.get("AppetiteNPYBalancer", {})
        hunger = float(appetite.get("hunger_signal", 0.0))

        fluid = prior.get("FluidBalanceWatcher", {})
        thirst = float(fluid.get("thirst_drive", fluid.get("osmotic_signal", 0.0)))
        osmotic = float(fluid.get("osmotic_signal", 0.0))

        thermo = prior.get("ThermoregulationCore", {})
        core_temp = float(thermo.get("core_temp_proxy", 0.5))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        vmh_data = prior.get("VentromedialHypothalamus", {})
        vmhdm = float(vmh_data.get("vmhdm_defense_drive", 0.0))

        # Compute priorities
        def_p = self._defense_priority(aversive, threat, vmhdm, vital_threat)
        ene_p = self._energy_priority(hunger, vital_drive)
        flu_p = self._fluid_priority(thirst, osmotic)
        the_p = self._thermal_priority(core_temp)
        rep_p = self._reproductive_priority(social, def_p, ene_p)
        soc_p = self._social_priority(social, def_p, arousal)

        # Smooth
        new_def = self._smooth(self.state.get("defense_priority", 0.0), def_p)
        new_ene = self._smooth(self.state.get("energy_priority", 0.0), ene_p)
        new_flu = self._smooth(self.state.get("fluid_priority", 0.0), flu_p)
        new_the = self._smooth(self.state.get("thermal_priority", 0.0), the_p)
        new_rep = self._smooth(self.state.get("reproductive_priority", 0.0),
                                 rep_p)
        new_soc = self._smooth(self.state.get("social_priority", 0.0), soc_p)

        priorities = {
            "defense": new_def, "energy": new_ene, "fluid": new_flu,
            "thermal": new_the, "reproductive": new_rep, "social": new_soc,
        }
        dominant, urgency = self._arbitrate(priorities)

        state = self._classify_state(dominant, urgency)

        recent = list(self.state.get("recent_dominant", []))
        recent.append(dominant)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["defense_priority"] = round(new_def, 4)
        self.state["energy_priority"] = round(new_ene, 4)
        self.state["fluid_priority"] = round(new_flu, 4)
        self.state["thermal_priority"] = round(new_the, 4)
        self.state["reproductive_priority"] = round(new_rep, 4)
        self.state["social_priority"] = round(new_soc, 4)
        self.state["dominant_drive"] = dominant
        self.state["urgency_score"] = round(urgency, 4)
        self.state["survival_state"] = state
        self.state["recent_dominant"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "defense_priority": round(new_def, 4),
            "energy_priority": round(new_ene, 4),
            "fluid_priority": round(new_flu, 4),
            "thermal_priority": round(new_the, 4),
            "reproductive_priority": round(new_rep, 4),
            "social_priority": round(new_soc, 4),
            "dominant_drive": dominant,
            "urgency_score": round(urgency, 4),
            "survival_state": state,
        }

    def _allostatic_load(self, recent_dominant: list) -> float:
        """Allostatic load — chronic-survival-mode index (Sterling 2012)."""
        if not recent_dominant:
            return 0.0
        non_quiet = sum(1 for d in recent_dominant[-50:] if d != "none")
        return non_quiet / max(1, len(recent_dominant[-50:]))

    def _conflict_index(self, priorities: dict) -> float:
        """Conflict between competing drives — high when multiple drives
        compete simultaneously."""
        sorted_p = sorted(priorities.values(), reverse=True)
        if len(sorted_p) < 2 or sorted_p[0] < 0.30:
            return 0.0
        return min(1.0, sorted_p[1] / max(0.001, sorted_p[0]))

    def _summary(self) -> dict:
        return {
            "dominant": self.state.get("dominant_drive", "none"),
            "urgency": self.state.get("urgency_score", 0.0),
            "defense": self.state.get("defense_priority", 0.0),
            "state": self.state.get("survival_state", "quiet"),
        }
