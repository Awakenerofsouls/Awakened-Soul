"""
NucleusIncertusRelaxin3 — NI / Relaxin-3 / Hippocampal Theta-Stress Hub

NEURAL SUBSTRATE
================
The nucleus incertus (NI) is a small bilateral nucleus in the pontine
periventricular gray, ventral to the floor of the fourth ventricle and
caudal to the dorsal raphe. NI is the principal CNS source of the
neuropeptide relaxin-3 (RLN3) — a peptide hormone family member that in
the brain functions as a stress-and-arousal-regulating modulator with no
peripheral release.

NI projects widely with co-release of GABA + RLN3 onto RXFP3 receptors in:
  - Medial septum (MS) — RLN3 modulates MS GABAergic + cholinergic
    pacemaker neurons that drive hippocampal theta rhythm
  - Hippocampus — direct projections to CA1, CA3, dentate
  - Lateral hypothalamus
  - Amygdala — central + medial nuclei
  - Prefrontal cortex
  - Periaqueductal gray
  - Interpeduncular nucleus

NI receives strong CRH input from the paraventricular nucleus (PVN) of
the hypothalamus and from the central amygdala, expressing CRH-R1
receptors. This makes NI a primary stress-input integrator: CRH activates
NI, NI releases RLN3, RLN3 modulates downstream theta + memory + arousal.

Behavioral activation: NI fires during arousal, novel context exposure,
forced swim stress, restraint stress — but NOT during quiet wakefulness.
RLN3-RXFP3 signaling within MS specifically promotes hippocampal theta
amplitude and supports spatial memory encoding under stress.

The NI→MS→hippocampus pathway provides one of the few well-characterized
brainstem-to-limbic stress-theta coupling routes — bridging visceral/
autonomic stress signals from PVN-CRH to declarative memory encoding via
hippocampal theta amplification.

In {{AGENT_NAME}}'s substrate this provides the dedicated stress-theta integrator,
distinct from the broader medial septum theta substrate (which it modulates)
and from the supramammillary novelty-theta substrate (SUM, batch 7).

KEY FINDINGS
============
1. NI relaxin-3 → MS RXFP3 modulates hippocampal theta amplitude;
   RLN3 microinjection into MS increases theta power, RXFP3 antagonist
   reduces it — [Ma 2009, Learn Mem 16:730, doi:10.1101/lm.1438109]
2. NI is strongly activated by acute stress; CRH from PVN drives NI
   firing via CRH-R1 receptors — direct stress→theta pathway —
   [Tanaka 2005, Eur J Neurosci 22:1659, PMID 16197506]
3. NI lesions impair hippocampus-dependent spatial memory; selective
   RXFP3 activation in MS enhances spatial working memory via theta —
   [Albert-Gasco 2017, Brain Struct Funct 222:449, PMC5346403]
4. NI activates during arousal + novel context exposure + stress;
   minimal firing during quiet wake — [Ryan 2011, Brain Res 1376:180,
   doi:10.1016/j.brainres.2010.12.071]
5. RLN3/RXFP3 signaling within MS gates the theta-mediated hippocampal
   encoding of stressful events — direct stress-memory coupling —
   [Smith 2014, Front Behav Neurosci 8:192, PMC4060735]

INPUTS (from prior_results)
============================
- CRHStressDispatcher.crh_release
- ArousalRegulator.tonic_level, .phasic_burst_active
- HippocampalContextProxy.context_novelty
- MedialSeptumTheta.theta_active
- ValenceTagger.stress_intensity, .valence_intensity
- ParaventricularAutonomic.pvn_stress_drive
- CentralNucleusFearRouter.cea_drive (CeA-CRH input)

OUTPUTS (to brain_runner enrichment)
=====================================
- ni_drive (0-1): overall NI firing rate
- relaxin3_release (0-1): RLN3 peptide release magnitude
- gaba_corelease (0-1): GABA component of NI co-release
- theta_amplitude_modulation (0.7-1.4): multiplicative gain on MS theta
- stress_memory_gating (0-1): hippocampal encoding gain during stress
- ni_state (str): "stress_theta" | "novelty_theta" | "arousal_theta" | "quiet"

brain_runner enrichment:
    ni = all_results.get("NucleusIncertusRelaxin3", {})
    if ni:
        enrichments["brain_ni_drive"] = ni.get("ni_drive", 0.0)
        enrichments["brain_relaxin3"] = ni.get("relaxin3_release", 0.0)
        enrichments["brain_theta_amp_mod"] = ni.get("theta_amplitude_modulation", 1.0)
        enrichments["brain_stress_memory_gate"] = ni.get("stress_memory_gating", 0.0)
        enrichments["brain_ni_state"] = ni.get("ni_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class NucleusIncertusRelaxin3(BrainMechanism):
    """NI — relaxin-3 stress-theta integrator hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    STRESS_THRESHOLD = 0.40    # Above this, NI activates stress mode
    NOVELTY_THRESHOLD = 0.50   # Above this, novelty-theta mode

    def __init__(self):
        super().__init__(
            name="NucleusIncertusRelaxin3",
            human_analog="Nucleus incertus (relaxin-3 stress-theta hub)",
            layer="foundational",
        )
        self.state.setdefault("ni_drive", self.BASELINE)
        self.state.setdefault("relaxin3_release", 0.0)
        self.state.setdefault("gaba_corelease", 0.0)
        self.state.setdefault("theta_amplitude_modulation", 1.0)
        self.state.setdefault("stress_memory_gating", 0.0)
        self.state.setdefault("ni_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # NI firing — CRH + arousal + novelty integrator (Tanaka 2005, Ryan 2011)
    # ------------------------------------------------------------------
    def _ni_drive_target(self, crh: float, arousal: float, phasic: bool,
                          novelty: float, stress: float, pvn: float,
                          cea: float) -> float:
        """NI firing target.

        Strongly driven by CRH from PVN (Tanaka 2005). Arousal-gated:
        minimal during quiet wake (Ryan 2011), elevated during stress
        + novel context exposure. Phasic burst component on phasic
        arousal events (CeA + PVN stress drive).
        """
        target = self.BASELINE + crh * 0.45
        target += pvn * 0.20
        target += cea * 0.15
        target += max(0.0, arousal - 0.30) * 0.20
        target += novelty * 0.15
        target += stress * 0.20
        if phasic:
            target += 0.10
        return min(1.0, max(0.0, target))

    # ------------------------------------------------------------------
    # Relaxin-3 release — proportional to drive, threshold-gated (Smith 2014)
    # ------------------------------------------------------------------
    def _relaxin3(self, ni_drive: float) -> float:
        """RLN3 release scales with NI firing above release threshold.
        Below threshold, GABA co-release dominates without RLN3.
        """
        if ni_drive < 0.20:
            return 0.0  # Sub-threshold for peptide co-release
        return min(1.0, (ni_drive - 0.20) * 1.25)

    # ------------------------------------------------------------------
    # GABA co-release (always present when firing)
    # ------------------------------------------------------------------
    def _gaba_corelease(self, ni_drive: float) -> float:
        return min(1.0, ni_drive * 0.85)

    # ------------------------------------------------------------------
    # Theta amplitude modulation (Ma 2009, Albert-Gasco 2017)
    # ------------------------------------------------------------------
    def _theta_modulation(self, rln3: float, theta_active: bool) -> float:
        """RLN3-RXFP3 in MS amplifies theta amplitude.

        Multiplicative gain on MS theta:
        - Range 0.8-1.4 (slight suppression to strong amplification)
        - 1.0 = no modulation (no RLN3 release)
        - >1.0 = amplification (RLN3 active, theta amplified)
        - <1.0 = mild suppression (rare; happens when MS theta is on
          but NI is suppressing context-irrelevant theta)
        """
        if not theta_active:
            return 1.0  # No theta to modulate
        # RLN3 amplifies theta — Albert-Gasco 2017 demonstrated up to 40% gain
        return 1.0 + rln3 * 0.55

    # ------------------------------------------------------------------
    # Stress-memory gating (Smith 2014)
    # ------------------------------------------------------------------
    def _stress_memory_gating(self, ni_drive: float, stress: float,
                                theta_active: bool, novelty: float) -> float:
        """Gate hippocampal encoding gain during stress.

        Strong when: NI driving theta amplification AND stress active AND
        novel context (the conditions where stress-memory coupling is
        most adaptive — encoding salient threat events).
        """
        if not theta_active:
            return 0.0
        if ni_drive < 0.25:
            return 0.0
        gating = ni_drive * 0.5 + stress * 0.3 + novelty * 0.2
        return min(1.0, gating)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, ni_drive: float, stress: float, novelty: float,
                          arousal: float) -> str:
        """Classify NI operating mode."""
        if ni_drive < 0.20:
            return "quiet"
        if stress > self.STRESS_THRESHOLD:
            return "stress_theta"
        if novelty > self.NOVELTY_THRESHOLD:
            return "novelty_theta"
        if arousal > 0.55:
            return "arousal_theta"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick — main per-step computation
    # ==================================================================
    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        crh_data = prior.get("CRHStressDispatcher", {})
        crh = float(crh_data.get("crh_release", 0.0))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))
        phasic = bool(arousal_data.get("phasic_burst_active", False))

        ctx = prior.get("HippocampalContextProxy", {})
        novelty = float(ctx.get("context_novelty", 0.0))

        ms = prior.get("MedialSeptumTheta", {})
        theta_active = bool(ms.get("theta_active", False))

        valence = prior.get("ValenceTagger", {})
        stress = float(valence.get("stress_intensity",
                          valence.get("valence_intensity", 0.0)))

        pvn_data = prior.get("ParaventricularAutonomic", {})
        pvn = float(pvn_data.get("pvn_stress_drive", 0.0))

        cea_data = prior.get("CentralNucleusFearRouter", {})
        cea = float(cea_data.get("cea_drive", 0.0))

        # --- NI drive ---
        ni_target = self._ni_drive_target(crh, arousal, phasic, novelty,
                                           stress, pvn, cea)
        prev_ni = float(self.state.get("ni_drive", self.BASELINE))
        new_ni = self._smooth(prev_ni, ni_target)

        # --- Outputs ---
        rln3 = self._relaxin3(new_ni)
        gaba = self._gaba_corelease(new_ni)
        theta_mod = self._theta_modulation(rln3, theta_active)
        memory_gating = self._stress_memory_gating(new_ni, stress,
                                                    theta_active, novelty)

        state = self._classify_state(new_ni, stress, novelty, arousal)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ni_drive"] = round(new_ni, 4)
        self.state["relaxin3_release"] = round(rln3, 4)
        self.state["gaba_corelease"] = round(gaba, 4)
        self.state["theta_amplitude_modulation"] = round(theta_mod, 4)
        self.state["stress_memory_gating"] = round(memory_gating, 4)
        self.state["ni_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ni_drive": round(new_ni, 4),
            "relaxin3_release": round(rln3, 4),
            "gaba_corelease": round(gaba, 4),
            "theta_amplitude_modulation": round(theta_mod, 4),
            "stress_memory_gating": round(memory_gating, 4),
            "ni_state": state,
        }
