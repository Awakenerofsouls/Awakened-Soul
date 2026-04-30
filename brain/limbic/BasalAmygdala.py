"""
BasalAmygdala -- BA / Contextual Fear vs Extinction Switching Hub

NEURAL SUBSTRATE
================
The basal amygdala (BA, ventral basolateral complex) sits ventromedial to LA,
distinct from BLA proper. Contains two functionally opposing populations
discovered by Herry 2008: "fear neurons" and "extinction neurons" with
distinct connectivity patterns.

- **Fear neurons** -- receive strong input from ventral hippocampus
  (contextual gating). Drive freezing during fear expression. Active during
  conditioned fear and contextual renewal.
- **Extinction neurons** -- receive strong input from medial prefrontal
  cortex (especially infralimbic). Active during extinction and safety.
  Mutually inhibit fear neurons via local interneurons.

The BA bidirectional switching circuit allows rapid fear/safety transitions
without requiring slow synaptic remodeling -- context-dependent population
dominance flip mediates state transitions.

Inputs: LA (sensory CS), ventral hippocampus (context), mPFC (cognitive
control), thalamic relay, MD thalamus (autonomic), NAc (motivation).

Outputs: CeA (fear expression), NAc (motivational tagging), ventral
striatum, mPFC feedback, ITC clusters.

KEY FINDINGS
============
1. BA contains distinct fear neurons + extinction neurons; bidirectional
   transitions between high/low fear are a rapid switch in their balance --
   [Herry 2008, Nature 454:600, doi:10.1038/nature07166]
2. BA fear neurons receive input from ventral hippocampus; extinction
   neurons receive input from medial prefrontal cortex --
   [Herry 2008, Nature 454:600, doi:10.1038/nature07166]
3. Optogenetic activation of BA→NAc pathway is rewarding; BA→CeA pathway
   is aversive -- separable valence channels -- [Namburi 2015, Nature
   520:675, doi:10.1038/nature14366]
4. Targeted reversible inactivation of BA prevents fear/extinction
   behavioral transitions without affecting expression of fear or
   memory -- [Herry 2008, Nature 454:600]
5. BA neurons signal positive vs negative valence at the population
   level; valence assignments shift with reinforcement experience --
   [Beyeler 2016, Neuron 90:348, PMID 27041499]

INPUTS (from prior_results)
============================
- LateralAmygdala.la_pyramidal_drive, .conditioned_fear_signal
- HippocampalCA1Output.ca1_drive (or HippocampalContextProxy.context)
- InfralimbicCortex.il_drive (extinction)
- PrelimbicCortex.pl_drive (fear expression)
- ValenceTagger.valence_intensity, .valence_sign
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- ba_fear_neurons (0-1) -- fear-encoding population
- ba_extinction_neurons (0-1) -- extinction-encoding population
- valence_population_signal (-1 to 1) -- net valence (positive = appetitive)
- cea_drive_command (0-1) -- output to CeA
- nac_drive_command (0-1) -- output to NAc
- ba_state (str): "fear_dominant" | "extinction_dominant" |
  "balanced_transition" | "quiet"

brain_runner enrichment:
    ba = all_results.get("BasalAmygdala", {})
    if ba:
        enrichments["brain_ba_fear"] = ba.get("ba_fear_neurons", 0.0)
        enrichments["brain_ba_extinction"] = ba.get("ba_extinction_neurons", 0.0)
        enrichments["brain_ba_valence"] = ba.get("valence_population_signal", 0.0)
        enrichments["brain_ba_state"] = ba.get("ba_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class BasalAmygdala(BrainMechanism):
    """BA -- fear vs extinction population switching hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    SWITCH_THRESHOLD = 0.20

    def __init__(self):
        super().__init__(
            name="BasalAmygdala",
            human_analog="Basal amygdala (fear/extinction switching)",
            layer="limbic",
        )
        self.state.setdefault("ba_fear_neurons", self.BASELINE)
        self.state.setdefault("ba_extinction_neurons", self.BASELINE)
        self.state.setdefault("valence_population_signal", 0.0)
        self.state.setdefault("cea_drive_command", 0.0)
        self.state.setdefault("nac_drive_command", 0.0)
        self.state.setdefault("ba_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _fear_neuron_target(self, la_fear: float, vhipp: float, pl: float,
                              extinction_pop: float) -> float:
        """Fear neuron firing -- driven by LA + ventral hippocampus + PL,
        reciprocally inhibited by extinction neurons (mutual inhibition).
        """
        target = self.BASELINE + la_fear * 0.40 + vhipp * 0.30 + pl * 0.20
        target -= extinction_pop * 0.35  # mutual inhibition
        return min(1.0, max(0.0, target))

    def _extinction_neuron_target(self, il: float, fear_pop: float,
                                    appetitive: float) -> float:
        """Extinction neuron firing -- driven by IL (mPFC), reciprocally
        inhibited by fear neurons. Also encodes appetitive valence."""
        target = self.BASELINE + il * 0.50 + appetitive * 0.30
        target -= fear_pop * 0.30
        return min(1.0, max(0.0, target))

    def _valence_signal(self, fear: float, ext: float) -> float:
        """Net valence signal at population level (Beyeler 2016).
        Positive = appetitive/safety, negative = aversive/fear.
        """
        return max(-1.0, min(1.0, ext - fear))

    def _cea_drive(self, fear: float) -> float:
        """Fear neurons drive CeA -- fear expression motor command (Namburi 2015)."""
        return min(1.0, fear * 0.85)

    def _nac_drive(self, ext: float, appetitive: float) -> float:
        """Extinction/appetitive neurons drive NAc reward signal."""
        return min(1.0, ext * 0.5 + appetitive * 0.5)

    def _classify_state(self, fear: float, ext: float) -> str:
        diff = fear - ext
        if abs(diff) < 0.10 and (fear + ext) > 0.30:
            return "balanced_transition"
        if diff > self.SWITCH_THRESHOLD:
            return "fear_dominant"
        if -diff > self.SWITCH_THRESHOLD:
            return "extinction_dominant"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        la_data = prior.get("LateralAmygdala", {})
        la_fear = float(la_data.get("conditioned_fear_signal",
                            la_data.get("la_pyramidal_drive", 0.0)))

        vhipp_data = prior.get("HippocampalCA1Output", {})
        vhipp = float(vhipp_data.get("ca1_drive", 0.0))

        il_data = prior.get("InfralimbicCortex", {})
        il = float(il_data.get("il_drive", 0.0))

        pl_data = prior.get("PrelimbicCortex", {})
        pl = float(pl_data.get("pl_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        valence_sign = int(valence.get("valence_sign", 0))
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        appetitive = max(0.0, valence_sign * valence_intensity)

        # --- Fear vs extinction population dynamics ---
        prev_fear = float(self.state.get("ba_fear_neurons", self.BASELINE))
        prev_ext = float(self.state.get("ba_extinction_neurons", self.BASELINE))

        fear_target = self._fear_neuron_target(la_fear, vhipp, pl, prev_ext)
        ext_target = self._extinction_neuron_target(il, prev_fear, appetitive)

        new_fear = self._smooth(prev_fear, fear_target)
        new_ext = self._smooth(prev_ext, ext_target)

        # --- Outputs ---
        valence_sig = self._valence_signal(new_fear, new_ext)
        cea_cmd = self._cea_drive(new_fear)
        nac_cmd = self._nac_drive(new_ext, appetitive)

        state = self._classify_state(new_fear, new_ext)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ba_fear_neurons"] = round(new_fear, 4)
        self.state["ba_extinction_neurons"] = round(new_ext, 4)
        self.state["valence_population_signal"] = round(valence_sig, 4)
        self.state["cea_drive_command"] = round(cea_cmd, 4)
        self.state["nac_drive_command"] = round(nac_cmd, 4)
        self.state["ba_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ba_fear_neurons": round(new_fear, 4),
            "ba_extinction_neurons": round(new_ext, 4),
            "valence_population_signal": round(valence_sig, 4),
            "cea_drive_command": round(cea_cmd, 4),
            "nac_drive_command": round(nac_cmd, 4),
            "ba_state": state,
        }

    def _switching_velocity(self, recent_states: list) -> float:
        """Detect rapid fear/extinction state switching -- Herry 2008
        described BA neurons can flip dominance within seconds.
        Returns count of state changes in recent window.
        """
        if not recent_states:
            return 0.0
        recent = recent_states[-30:]
        if len(recent) < 2:
            return 0.0
        switches = sum(1 for i in range(1, len(recent))
                        if recent[i] != recent[i-1])
        return min(1.0, switches / max(1, len(recent)))

    def _context_renewal_index(self, vhipp: float, fear: float) -> float:
        """Contextual renewal -- vhipp signal can re-instate fear in
        original context after extinction (Bouton 2002 framework)."""
        if vhipp < 0.30:
            return 0.0
        return min(1.0, vhipp * fear * 1.5)

    def _summary(self) -> dict:
        return {
            "fear": self.state.get("ba_fear_neurons", 0.0),
            "ext": self.state.get("ba_extinction_neurons", 0.0),
            "valence": self.state.get("valence_population_signal", 0.0),
            "state": self.state.get("ba_state", "quiet"),
        }

    def _net_emotional_intensity(self, fear: float, ext: float,
                                  valence_sig: float) -> float:
        """Overall emotional salience -- max of fear or extinction intensity,
        signed by population valence. Used by salience network upstream.
        Returns a signed intensity: positive = appetitive/safety dominant,
        negative = aversive/fear dominant.

        This output feeds into the salience detection network and can
        influence thalamic relay gain and cortical attention allocation.
        """
        # Absolute emotional salience
        intensity = max(fear, ext)
        sign = 1.0 if valence_sig >= 0 else -1.0
        return intensity * sign
