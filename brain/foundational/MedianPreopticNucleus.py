"""
MedianPreopticNucleus — MnPO / Multimodal Hypothalamic Integrator

NEURAL SUBSTRATE
================
Midline nucleus along third ventricle wall in anterior hypothalamus.
Distinct from VLPO (which is more lateral). MnPO is multimodal — it
integrates three streams of input that converge here before broadcast:

1. **Thermal** — warm-sensitive neurons (TRPM2-expressing) + skin
   thermal afferents via spinal-PBN-MnPO
2. **Osmotic / volume** — input from subfornical organ (SFO) + organum
   vasculosum (OVLT) — both circumventricular organs sensing plasma
   osmolality and angiotensin II
3. **Sleep** — distinct sleep-active GABAergic neurons (separate
   population from VLPO galanin/GABA cells)

Outputs:
- PVN (paraventricular nucleus, hypothalamic) — drives ADH/vasopressin
  release, oxytocin, CRH; coordinates autonomic
- DMH (dorsomedial hypothalamus) — autonomic + thermogenic relay
- Raphe pallidus — premotor for BAT thermogenesis + cardiac sympathetic
- VLPO — sleep coordination

Pyrogenic action: PGE2 (prostaglandin E2) acts on EP3 receptors
expressed by MnPO warm-sensitive neurons, INHIBITING them. Loss of
warm-sensitive inhibition raises thermoregulatory setpoint → fever.
This is the canonical fever mechanism (Lazarus 2007, Boulant 2000).

KEY FINDINGS
============
1. MnPO warm-sensitive neurons drive heat-loss responses via
   DMH/raphe pallidus pathway; chemogenetic activation produces
   hypothermia — [Nakamura 2011, J Neurosci 31:11954,
   doi:10.1523/JNEUROSCI.2370-11.2011]
2. MnPO osmotic neurons receive SFO + OVLT input — drive PVN
   vasopressin + thirst behavior — [McKinley 2003, J Comp Neurol
   460:373, PMID 12692856]
3. MnPO sleep-active neurons distinct from VLPO; selective lesion
   reduces NREM amount independently of VLPO — [Suntsova 2007,
   J Physiol 581:253, PMC2075209]
4. EP3 prostaglandin receptor on MnPO mediates fever — PGE2 inhibits
   warm-sensitive neurons; setpoint rises — [Lazarus 2007, Nat
   Neurosci 10:1131, PMID 17676060]
5. MnPO integrates dehydration + heat → coordinated autonomic +
   behavioral response — [Bourque 2008, Nat Rev Neurosci 9:519,
   doi:10.1038/nrn2400]

INPUTS
======
- ThermoregulationCore.skin_temp_proxy, .core_temp_proxy
- FluidBalanceWatcher.osmotic_signal
- SubfornicalOrgansThirstHub.thirst_drive
- AdenosineProxy.adenosine_level
- InflammationProxy.pge2_signal (default 0)

OUTPUTS
=======
- mnpo_warm_drive (0-1)
- mnpo_osmotic_drive (0-1)
- mnpo_sleep_drive (0-1)
- pvn_adh_signal (0-1)
- bat_thermogenesis_inhibition (0-1)
- fever_setpoint_shift (0-1)
- mnpo_state (str): "thermoregulation" | "osmotic_defense" |
  "sleep_recruit" | "fever" | "quiet"

brain_runner enrichment:
    mnpo = all_results.get("MedianPreopticNucleus", {})
    if mnpo:
        enrichments["brain_mnpo_warm"] = mnpo.get("mnpo_warm_drive", 0.0)
        enrichments["brain_mnpo_osmotic"] = mnpo.get("mnpo_osmotic_drive", 0.0)
        enrichments["brain_mnpo_sleep"] = mnpo.get("mnpo_sleep_drive", 0.0)
        enrichments["brain_mnpo_state"] = mnpo.get("mnpo_state", "quiet")
        enrichments["brain_fever_shift"] = mnpo.get("fever_setpoint_shift", 0.0)
"""

from brain.base_mechanism import BrainMechanism


class MedianPreopticNucleus(BrainMechanism):
    """MnPO — multimodal thermal + osmotic + sleep integrator."""

    BASELINE = 0.10
    SMOOTH = 0.20
    WARM_THRESHOLD = 0.50
    OSMOTIC_THRESHOLD = 0.45
    FEVER_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="MedianPreopticNucleus",
            human_analog="Median preoptic nucleus (thermo + osmotic + sleep hub)",
            layer="foundational",
        )
        self.state.setdefault("mnpo_warm_drive", 0.0)
        self.state.setdefault("mnpo_osmotic_drive", 0.0)
        self.state.setdefault("mnpo_sleep_drive", 0.0)
        self.state.setdefault("pvn_adh_signal", 0.0)
        self.state.setdefault("bat_thermogenesis_inhibition", 0.0)
        self.state.setdefault("fever_setpoint_shift", 0.0)
        self.state.setdefault("mnpo_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # Warm-sensitive neurons (Nakamura 2011); PGE2 inhibits (Lazarus 2007)
    # ------------------------------------------------------------------
    def _warm_target(self, core_temp: float, skin_temp: float,
                       pge2: float) -> float:
        """Warm-sensitive firing increases with core/skin temp.

        PGE2 inhibits warm-sensitive neurons → fever (Lazarus 2007).
        Modeling core_temp and skin_temp as 0-1 (0.5 = neutral).
        """
        # Sigmoid-like response: temp >0.5 fires more
        warm_signal = max(0.0, core_temp - 0.45) * 2.0 + max(0.0, skin_temp - 0.45) * 0.5
        # PGE2 inhibits — raises setpoint
        warm_signal -= pge2 * 0.85
        return min(1.0, max(0.0, warm_signal))

    # ------------------------------------------------------------------
    # Osmotic firing (McKinley 2003, Bourque 2008)
    # ------------------------------------------------------------------
    def _osmotic_target(self, osmotic: float, thirst: float) -> float:
        """Osmotic neuron firing — driven by SFO/OVLT signals."""
        return min(1.0, osmotic * 0.55 + thirst * 0.40)

    # ------------------------------------------------------------------
    # Sleep-active firing (Suntsova 2007)
    # ------------------------------------------------------------------
    def _sleep_target(self, adenosine: float) -> float:
        """MnPO sleep-active distinct from VLPO; mostly adenosine-driven."""
        if adenosine < 0.30:
            return 0.0
        return min(1.0, (adenosine - 0.30) * 1.2)

    # ------------------------------------------------------------------
    # PVN ADH command — driven by osmotic firing (McKinley 2003)
    # ------------------------------------------------------------------
    def _pvn_adh(self, osmotic_drive: float) -> float:
        """MnPO → PVN vasopressin release command."""
        return min(1.0, osmotic_drive * 0.85)

    # ------------------------------------------------------------------
    # BAT thermogenesis inhibition (Nakamura 2011)
    # ------------------------------------------------------------------
    def _bat_inhibition(self, warm_drive: float, fever_shift: float) -> float:
        """Warm-active MnPO inhibits BAT thermogenesis via raphe pallidus.
        Fever blocks this — warm-sensitive neurons silenced.
        """
        if fever_shift > 0.40:
            return 0.0  # Fever — no heat-loss inhibition
        if warm_drive < 0.40:
            return 0.0
        return min(1.0, (warm_drive - 0.40) * 1.6)

    # ------------------------------------------------------------------
    # Fever setpoint shift (Lazarus 2007)
    # ------------------------------------------------------------------
    def _fever_shift(self, pge2: float) -> float:
        """PGE2 → EP3R on MnPO warm-sensitive → fever setpoint shift."""
        return min(1.0, pge2 * 0.75)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, warm: float, osmotic: float, sleep: float,
                          fever_shift: float) -> str:
        """Classify MnPO operating mode."""
        if fever_shift > self.FEVER_THRESHOLD:
            return "fever"
        if osmotic > self.OSMOTIC_THRESHOLD:
            return "osmotic_defense"
        if warm > self.WARM_THRESHOLD:
            return "thermoregulation"
        if sleep > 0.30:
            return "sleep_recruit"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick
    # ==================================================================
    def _thermo_osmotic_balance(self, warm: float, osmotic: float) -> float:
        """When both heat AND dehydration are active, prioritize osmotic
        defense (water conservation) — coordinated response (Bourque 2008).
        Returns weight: positive = osmotic priority, negative = thermo.
        """
        if (warm + osmotic) < 0.10:
            return 0.0
        return (osmotic - warm) / max(0.001, warm + osmotic)

    def _fever_chill_oscillation(self, pge2: float, core_temp: float) -> float:
        """Detect chill phase of fever (PGE2 high, core_temp not yet risen)
        vs sustained-fever phase (PGE2 high, core_temp elevated).
        """
        if pge2 < 0.30:
            return 0.0
        if core_temp < 0.50:
            return 1.0  # chill phase — heat-generating
        return 0.0  # sustained fever — heat-conserving

    def _tick_summary(self) -> dict:
        """Compact downstream-consumer summary."""
        return {
            "warm": self.state.get("mnpo_warm_drive", 0.0),
            "osmotic": self.state.get("mnpo_osmotic_drive", 0.0),
            "sleep": self.state.get("mnpo_sleep_drive", 0.0),
            "fever_shift": self.state.get("fever_setpoint_shift", 0.0),
            "state": self.state.get("mnpo_state", "quiet"),
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        thermo = prior.get("ThermoregulationCore", {})
        skin_temp = float(thermo.get("skin_temp_proxy", 0.5))
        core_temp = float(thermo.get("core_temp_proxy", 0.5))

        fluid = prior.get("FluidBalanceWatcher", {})
        osmotic = float(fluid.get("osmotic_signal", 0.0))

        thirst_data = prior.get("SubfornicalOrgansThirstHub", {})
        thirst = float(thirst_data.get("thirst_drive", 0.0))

        ad = prior.get("AdenosineProxy", {})
        adenosine = float(ad.get("adenosine_level", 0.30))

        inflam = prior.get("InflammationProxy", {})
        pge2 = float(inflam.get("pge2_signal", 0.0))

        # --- Warm ---
        warm_target = self._warm_target(core_temp, skin_temp, pge2)
        prev_warm = float(self.state.get("mnpo_warm_drive", 0.0))
        new_warm = self._smooth(prev_warm, warm_target)

        # --- Osmotic ---
        osmotic_target = self._osmotic_target(osmotic, thirst)
        prev_osm = float(self.state.get("mnpo_osmotic_drive", 0.0))
        new_osm = self._smooth(prev_osm, osmotic_target)

        # --- Sleep ---
        sleep_target = self._sleep_target(adenosine)
        prev_sleep = float(self.state.get("mnpo_sleep_drive", 0.0))
        new_sleep = self._smooth(prev_sleep, sleep_target)

        # --- Outputs ---
        fever_shift = self._fever_shift(pge2)
        bat_inh = self._bat_inhibition(new_warm, fever_shift)
        pvn_adh = self._pvn_adh(new_osm)

        state = self._classify_state(new_warm, new_osm, new_sleep, fever_shift)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mnpo_warm_drive"] = round(new_warm, 4)
        self.state["mnpo_osmotic_drive"] = round(new_osm, 4)
        self.state["mnpo_sleep_drive"] = round(new_sleep, 4)
        self.state["pvn_adh_signal"] = round(pvn_adh, 4)
        self.state["bat_thermogenesis_inhibition"] = round(bat_inh, 4)
        self.state["fever_setpoint_shift"] = round(fever_shift, 4)
        self.state["mnpo_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mnpo_warm_drive": round(new_warm, 4),
            "mnpo_osmotic_drive": round(new_osm, 4),
            "mnpo_sleep_drive": round(new_sleep, 4),
            "pvn_adh_signal": round(pvn_adh, 4),
            "bat_thermogenesis_inhibition": round(bat_inh, 4),
            "fever_setpoint_shift": round(fever_shift, 4),
            "mnpo_state": state,
        }
