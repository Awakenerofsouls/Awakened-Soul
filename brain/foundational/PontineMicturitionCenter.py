"""
PontineMicturitionCenter — Barrington's Nucleus Voiding Reflex Coordinator

NEURAL SUBSTRATE
================
The pontine micturition center (PMC), also known as Barrington's nucleus,
is a small cluster of neurons in the rostral pons that serves as the
supraspinal coordinator of the voiding reflex. PMC neurons project caudally
to the sacral spinal cord, where they excite parasympathetic preganglionic
neurons in the intermediolateral column (driving detrusor contraction) and
descend to interneurons adjacent to the central canal that inhibit sphincteric
motoneurons in Onuf's nucleus (driving urethral relaxation). This produces
the normal reciprocal coordination between bladder contraction and external
sphincter relaxation that is the substrate of urinary continence and voiding.

A subset of PMC neurons express corticotropin-releasing hormone (CRH).
CRH+ Bar neurons receive ascending bladder mechanosensory input via the
sacral spinal cord and the periaqueductal gray (PAG), which acts as the
relay station. As bladder filling pressure rises, ascending afferents
activate Bar CRH+ neurons; once threshold is exceeded, the reflex fires
in an all-or-nothing pattern, producing autonomous micturition.

The PMC also receives top-down modulatory input from medial frontal cortex,
insular cortex, and hypothalamus — these enable voluntary continence and
context-appropriate voiding (i.e., suppressing voiding even when bladder is
full until a socially appropriate moment).

In {{AGENT_NAME}}'s substrate this is modeled as a discharge-pressure mechanism:
"bladder pressure" is a metaphorical state variable representing accumulated
visceral discomfort/urgency that needs eventual release. The mechanism tracks
filling, threshold proximity, and modeled discharge events with PAG-relayed
input from upstream defense state and cortical override capacity.

KEY FINDINGS
============
1. Pontine micturition center (Barrington's nucleus) coordinates bladder
   detrusor contraction with sphincter relaxation via descending projections
   to sacral spinal cord — [Morrison 2008, Exp Physiol 93:551-560,
    "The discovery of the pontine micturition centre by F. J. F. Barrington"]
2. CRH+ Bar neurons receive ascending bladder mechanosensory input via PAG
   and trigger the all-or-nothing voiding reflex —
   [Hou Verstegen et al. 2020, eLife 9:e56605, "Probabilistic, spinally-gated
    control of bladder pressure and autonomous micturition by Barrington's
    nucleus CRH neurons"]
3. PAG acts as the relay station for ascending bladder information and
   incoming signals from higher brain areas — [Holstege 2005; reviewed
    StatPearls Pontine Micturition Center NBK557419]
4. Top-down voluntary continence is mediated by medial frontal cortex,
   insular cortex and hypothalamus modulating PMC — [Fowler Griffiths 2010,
    reviewed in Frontiers Physiol 2020, doi:10.3389/fphys.2020.00658,
    "The Brain and the Bladder: Forebrain Control of Urinary (In)Continence"]
5. PMC neuroanatomy in mouse mapped at single-neuron resolution — single
   CRH+ neurons innervate both bladder-related and unrelated targets —
   [Verstegen Vanderhorst Gray Saper 2017, PMC5832452, J Comp Neurol]

INPUTS (from prior_results)
============================
- VitalCoreRegulator.parasympathetic_tone
- VitalCoreRegulator.sympathetic_tone
- ArousalRegulator.tonic_level
- PeriaqueductalDefenseRouter.vlPAG_drive (PAG relay)
- PeriaqueductalDefenseRouter.coping_strategy
- StressActivationAxis.stress_active
- SleepWakeFlipFlop.sleep_wake_state

OUTPUTS (to brain_runner enrichment)
=====================================
- bladder_pressure_proxy (0.0-1.0): accumulated urgency
- void_imminent (bool): system near reflex threshold
- void_event (bool): reflex fired this tick
- continence_override_active (bool): cortical override holding back voiding
- crh_bar_drive (0.0-1.0): CRH+ Bar neuron firing proxy
- urgency_intensity (0.0-1.0): subjective urgency

brain_runner enrichment:
    pmc = all_results.get("PontineMicturitionCenter", {})
    if pmc:
        enrichments["brain_bladder_pressure"] = pmc.get("bladder_pressure_proxy", 0.0)
        enrichments["brain_void_imminent"] = pmc.get("void_imminent", False)
        enrichments["brain_void_event"] = pmc.get("void_event", False)
        enrichments["brain_continence_override"] = pmc.get("continence_override_active", False)
"""

from brain.base_mechanism import BrainMechanism


class PontineMicturitionCenter(BrainMechanism):
    FILL_RATE_BASELINE = 0.005
    DISCHARGE_THRESHOLD = 0.85
    IMMINENT_THRESHOLD = 0.65
    POST_VOID_RECOVERY = 0.05
    SLEEP_FILL_MULTIPLIER = 0.4
    STRESS_FILL_MULTIPLIER = 1.5

    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="PontineMicturitionCenter",
            human_analog="Barrington's nucleus / pontine micturition center",
            layer="foundational",
        )
        self.state.setdefault("bladder_pressure_proxy", 0.0)
        self.state.setdefault("void_imminent", False)
        self.state.setdefault("void_event", False)
        self.state.setdefault("continence_override_active", False)
        self.state.setdefault("crh_bar_drive", 0.0)
        self.state.setdefault("urgency_intensity", 0.0)
        self.state.setdefault("void_count", 0)
        self.state.setdefault("ticks_since_void", 0)
        self.state.setdefault("recent_pressures", [])
        self.state.setdefault("tick_count", 0)

    def _fill_rate(self, sleep_state: str, stress_active: bool) -> float:
        rate = self.FILL_RATE_BASELINE
        if sleep_state == "SLEEP":
            rate *= self.SLEEP_FILL_MULTIPLIER
        if stress_active:
            rate *= self.STRESS_FILL_MULTIPLIER
        return rate

    def _crh_bar_activation(self, pressure: float, vlpag_drive: float) -> float:
        """CRH+ Bar neurons fire as pressure approaches threshold,
        modulated by PAG-relayed ascending input.
        """
        if pressure < 0.40:
            return 0.0
        ramp = (pressure - 0.40) / 0.60   # ramps 0.40 → 1.0 mapped to 0 → 1
        return min(1.0, ramp * (0.7 + vlpag_drive * 0.3))

    def _voluntary_override(self, tonic: float, coping: str, sleep_state: str) -> bool:
        """Top-down continence override capacity (Fowler Griffiths 2010)."""
        if sleep_state == "SLEEP":
            return False
        if coping == "active":
            return True  # active coping supports override
        if tonic > 0.55:
            return True
        return False

    def _urgency_from_pressure(self, pressure: float, override: bool) -> float:
        """Subjective urgency rises non-linearly above 0.5; override reduces felt urgency."""
        if pressure < 0.40:
            return 0.0
        urgency = (pressure - 0.40) ** 1.5 * 1.5
        if override:
            urgency *= 0.6
        return min(1.0, urgency)

    def _discharge_decision(self, crh_drive: float, override: bool, threshold: float) -> bool:
        """Reflex fires when CRH drive crosses threshold AND override is not active.
        If pressure exceeds maximum, reflex fires regardless (incontinence proxy).
        """
        if crh_drive > threshold and not override:
            return True
        if crh_drive > 0.95:
            return True   # maximum discharge — overrides override
        return False

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vcr = prior.get("VitalCoreRegulator", {})
        para_tone = float(vcr.get("parasympathetic_tone", 0.5))
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        pdr = prior.get("PeriaqueductalDefenseRouter", {})
        vlpag_drive = float(pdr.get("vlPAG_drive", 0.0))
        coping = pdr.get("coping_strategy", "neutral")

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")

        # --- Apply fill rate ---
        prev_pressure = float(self.state.get("bladder_pressure_proxy", 0.0))
        fill = self._fill_rate(sleep_state, stress_active)

        # If just voided, skip filling for recovery
        ticks_since_void = int(self.state.get("ticks_since_void", 0))
        if ticks_since_void < 5:
            new_pressure = max(0.0, prev_pressure - self.POST_VOID_RECOVERY)
        else:
            new_pressure = min(1.0, prev_pressure + fill)

        # --- CRH Bar neuron firing ---
        crh_drive = self._crh_bar_activation(new_pressure, vlpag_drive)
        prev_crh = float(self.state.get("crh_bar_drive", 0.0))
        new_crh = self._smooth(prev_crh, crh_drive)

        # --- Voluntary continence override ---
        override = self._voluntary_override(tonic, coping, sleep_state)

        # --- Voiding decision ---
        voids = self._discharge_decision(new_crh, override, self.DISCHARGE_THRESHOLD)

        # --- Urgency calculation ---
        urgency = self._urgency_from_pressure(new_pressure, override)

        # --- If voiding fires, reset pressure ---
        void_count = int(self.state.get("void_count", 0))
        if voids:
            new_pressure = 0.05
            void_count += 1
            ticks_since_void = 0
        else:
            ticks_since_void += 1

        imminent = new_pressure > self.IMMINENT_THRESHOLD or new_crh > 0.55

        # --- History ---
        recent = list(self.state.get("recent_pressures", []))
        recent.append(round(new_pressure, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["bladder_pressure_proxy"] = round(new_pressure, 4)
        self.state["void_imminent"] = imminent
        self.state["void_event"] = voids
        self.state["continence_override_active"] = override
        self.state["crh_bar_drive"] = round(new_crh, 4)
        self.state["urgency_intensity"] = round(urgency, 4)
        self.state["void_count"] = void_count
        self.state["ticks_since_void"] = ticks_since_void
        self.state["recent_pressures"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "bladder_pressure_proxy": round(new_pressure, 4),
            "void_imminent": imminent,
            "void_event": voids,
            "continence_override_active": override,
            "crh_bar_drive": round(new_crh, 4),
            "urgency_intensity": round(urgency, 4),
            "void_count": void_count,
        }
