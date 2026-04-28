"""
Build 12: Foundational001SympatheticVasomotorController — RVLM Pressor Center
===============================================================================

PLACEMENT:
  Layer:    foundational (brainstem — rostral ventrolateral medulla)
  Filename: brain/foundational/Foundational001SympatheticVasomotorController.py
  Instance name: SympatheticVasomotorController

NEURAL SUBSTRATE:
  Rostral ventrolateral medulla (RVLM), the primary vasomotor
  pressor center. Receives baroreceptor input via NTS and projects
  directly to preganglionic sympathetic neurons in the
  intermediolateral cell column (IML) of the spinal cord.
  Maintains vasoconstrictor tone necessary for baseline arterial
  pressure. Directly targeted by antihypertensive drugs (clonidine,
  methyldopa) acting on imidazoline receptors.

  Key afferents:
    - NTS baroreceptor signals (via BaroreflexBalancer)
    - Hypothalamic defense areas (fight/freeze from PAG)
    - Parabrachial nucleus (pain/visceral integration)
    - Raphe magnus (descending pain modulation)

  Key efferents:
    - IML sympathetic preganglionic neurons → ganglia → vascular
      smooth muscle throughout the body

KEY FINDINGS:
  1. RVLM tonically fires at 1-3 Hz at rest, sustaining ~50% of
     baseline vascular resistance [UNVERIFIED: Dampney 1994 — author-year
     citation; please verify title/volume before citing].
  2. Baroreceptor reflex suppresses RVLM on systolic BP rise
     (a drop in RVLM activity causes vasodilation, BP falls);
     rapid resetting occurs within 1-3 cardiac cycles [UNVERIFIED:
     Beneken & DeBour 1995 — author-year only; verify or replace with
     Eckberg 1976 or Korner papers on baroreflex resetting].
  3. RVLM neurons are command neurons with autonomous pacemaker-
    like firing — Na+/Ca2+ plateau potentials maintain output even
    without continuous synaptic drive [UNVERIFIED: Laskey & Polosa 1988
     — author-year only; verify in J Neurophysiol].
  4. C1 adrenergic cells in RVLM respond to hypotension, hypoxia,
     and hypoglycemia with emergency sympathetic activation
     (Guyenet 2006, Nat Rev Neurosci 7:335-346; PMID 16760914).
  5. Clonidine acts on I1-imidazoline receptors in RVLM to produce
     vasodepression — confirming RVLM as the dominant resting
     vasomotor tone source (Bousquet et al. 1998, J Hypertens Suppl
     16:S1-5; PMID 9747903).

INPUTS (prior_results):
  - BaroreflexBalancer: baroreceptor_suppressed (bool)
  - ArousalRegulator: arousal_level (float 0-1)
  - StressActivationAxis: crh_level (float 0-1)
  - GutSignalRelay: gut_distress (float 0-1)

OUTPUTS:
  - sympathetic_tone: float 0.0-1.0 (primary vasoconstrictor drive)
  - vasoconstrictor_bp_contribution: float 0.0-1.0 (BP component)
  - baroreflex_modulation: float -0.3 to +0.3 (net baroreflex effect)
  - threat_activated: bool (emergency override of baroreflex)
  - mean_arterial_pressure_index: float 0.0-1.0 (approximate MAP signal)

CITATIONS:
    PMC2905784 — Rossi NF, Maliszewska-Scislo M, Chen H et al. (2010). Neuronal Nitric
        Oxide Synthase Within Paraventricular Nucleus: Blood Pressure and Baroreflex.
        Hypertension.
    PMC5452971 — Gao L, Zimmerman MC, Biswal S et al. (2017). Selective Nrf2 Gene
        Deletion in the Rostral Ventrolateral Medulla Evokes Hypertension and
        Sympathoexcitation in Mice. Hypertension.
"""

from brain.base_mechanism import BrainMechanism


class SympatheticVasomotorController(BrainMechanism):
    """
    Rostral ventrolateral medulla — vasomotor pressor center.

    Maintains resting sympathetic vasoconstrictor tone. Suppressed by
    baroreceptor feedback when BP rises. Overridden by stress/pain
    inputs (defense reaction). Integrated target for autonomic
    pharmacology.
    """

    # Resting vasoconstrictor tone — RVLM baseline (~50% of total resistance)
    RESTING_TONE = 0.52

    # Baroreflex sensitivity: how aggressively RVLM responds to BP changes
    BAROREFLEX_GAIN = 0.35

    # Threat/stress override — CRH or gut distress can suppress baroreflex
    THREAT_OVERRIDE_THRESHOLD = 0.62

    # C1 cell emergency activation ceiling
    MAX_TONE = 0.95
    MIN_TONE = 0.08

    # Rate constants
    TONE_CONVERGENCE_RATE = 0.06   # toward target per tick
    TONE_THREAT_RATE = 0.20         # faster convergence under threat override
    BP_INDEX_CONVERGENCE = 0.04    # MAP signal is sluggish

    def __init__(self):
        super().__init__(
            name="SympatheticVasomotorController",
            human_analog=(
                "Rostral ventrolateral medulla — vasomotor pressor center, "
                "C1 adrenergic cells, primary source of resting sympathetic tone"
            ),
            layer="foundational",
        )
        self.state.setdefault("sympathetic_tone", self.RESTING_TONE)
        self.state.setdefault("baroreflex_modulation", 0.0)
        self.state.setdefault("mean_arterial_pressure_index", 0.50)
        self.state.setdefault("threat_activated", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ---- Baroreceptor suppression signal ----
        baroreflex = prior.get("BaroreflexBalancer", {})
        baroreceptor_suppressed = baroreflex.get("baroreceptor_suppressed", False)
        baroreflex_intensity = baroreflex.get("baroreflex_intensity", 0.0)

        # Convert baroreceptor signal to RVLM suppression
        # Suppressed baroreceptor = BP high = suppress RVLM = vasodilate
        if baroreceptor_suppressed:
            baroreflex_modulation = -baroreflex_intensity * self.BAROREFLEX_GAIN
        else:
            baroreflex_modulation = 0.0

        # ---- Threat / stress override ----
        # Stress axis can override baroreflex — body needs BP for defense
        crh_level = prior.get("StressActivationAxis", {}).get("crh_level", 0.0)
        gut_distress = prior.get("GutSignalRelay", {}).get("gut_distress", 0.0)
        threat_signal = max(crh_level, gut_distress)
        threat_activated = threat_signal > self.THREAT_OVERRIDE_THRESHOLD

        if threat_activated:
            # Emergency override: restore tone regardless of baroreflex
            baroreflex_modulation = threat_signal * 0.25
            threat_activated = True
        else:
            threat_activated = False

        # ---- Arousal coupling ----
        # High arousal elevates sympathetic tone (LC-NE → RVLM facilitation)
        arousal_level = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        arousal_modulation = (arousal_level - 0.5) * 0.12

        # ---- Compute target tone ----
        target_tone = (
            self.RESTING_TONE
            + baroreflex_modulation
            + arousal_modulation
        )
        target_tone = max(self.MIN_TONE, min(self.MAX_TONE, target_tone))

        # ---- Smooth convergence — faster under threat ----
        current_tone = self.state["sympathetic_tone"]
        rate = self.TONE_THREAT_RATE if threat_activated else self.TONE_CONVERGENCE_RATE
        new_tone = current_tone + (target_tone - current_tone) * rate
        new_tone = round(new_tone, 4)

        # ---- MAP index: proportional to tone (with baroreflex lag) ----
        current_mapi = self.state["mean_arterial_pressure_index"]
        # BP rises when tone rises; simplified linear approximation
        new_mapi = current_mapi + (new_tone - current_mapi) * self.BP_INDEX_CONVERGENCE
        new_mapi = round(new_mapi, 4)

        # Round baroreflex_modulation
        baroreflex_modulation = round(baroreflex_modulation, 4)

        # Persist
        self.state["sympathetic_tone"] = new_tone
        self.state["baroreflex_modulation"] = baroreflex_modulation
        self.state["mean_arterial_pressure_index"] = new_mapi
        self.state["threat_activated"] = threat_activated
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "sympathetic_tone": new_tone,
            "vasoconstrictor_bp_contribution": round(
                new_tone * 0.6 + baroreflex_modulation * 0.2, 4
            ),
            "baroreflex_modulation": baroreflex_modulation,
            "threat_activated": threat_activated,
            "mean_arterial_pressure_index": new_mapi,
        }
