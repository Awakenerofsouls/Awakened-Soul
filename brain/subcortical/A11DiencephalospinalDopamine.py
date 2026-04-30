"""
A11DiencephalospinalDopamine — A11 Hypothalamic DA / Spinal Pain Modulation / RLS

NEURAL SUBSTRATE
================
The A11 dopaminergic cell group sits in the periventricular and dorsal
hypothalamus, distinct from the much larger A8/A9/A10 mesencephalic
dopamine groups (substantia nigra, ventral tegmental area, retrorubral).
A11 is small (~100-300 neurons in rodents) but functionally singular:
it is the **principal source of dopaminergic innervation of the spinal
cord**, projecting from hypothalamus directly to all segments of the
spinal cord — a pathway called the **diencephalospinal dopaminergic
system**.

A11 → spinal projections terminate in the dorsal horn (modulating
nociception via D1/D2 receptors at presynaptic and postsynaptic
targets), in the intermediolateral cell column (modulating sympathetic
outflow), and in the ventral horn (motor). This positions A11 as the
central regulator of:

- **Spinal pain modulation** — A11 dopamine acts at spinal receptors
  to modulate ascending nociceptive transmission. GABAergic inhibition
  or DA denervation of A11 induces trigeminal analgesia (Charbit et al.
  2010 — see PubMed). Loss of A11 DA produces **central pain
  syndromes** including migraine and neuropathic pain.

- **Restless legs syndrome (RLS)** — A11 DA dysfunction is the
  leading hypothesis for RLS pathophysiology. Iron deficiency →
  impaired A11 dopamine synthesis → spinal DA insufficiency → RLS
  symptoms. Spinal DA agonists historically first-line; recent 2024
  AASM guidelines moved DA agonists out of first-line due to
  augmentation concerns, but the A11 mechanism remains the explanatory
  model.

- **Sympathetic visceral autonomic regulation** — A11 → IML projections
  modulate sympathetic outflow.

A11 also participates in central pain and trigeminal nociception via
descending modulation that complements PAG-RVM and A5/A1.

In Nova's substrate this provides the diencephalospinal DA channel —
combines hypothalamic state (iron status proxy, arousal) with descending
pain control to modulate spinal pain gating and contribute to RLS-like
pathology when persistently low.

KEY FINDINGS
============
1. A11 hypothalamic dopaminergic neurons project to all spinal cord
   levels — principal source of spinal dopamine via diencephalospinal
   pathway — [Hökfelt Skagerberg Skirboll 1979 Brain Res] [Sharples et al. 2014, Front Neural Circ 8:55, "Dopaminergic
    modulation of spinal motor circuits"]
2. Neuroanatomical study of A11 diencephalospinal pathway in non-
   human primate confirms direct hypothalamic-spinal projection
   architecture — [Barraud et al. 2010, PLoS One 5:e13306,
    "Neuroanatomical Study of the A11 Diencephalospinal Pathway in
    the Non-Human Primate" PMC2954154]
3. GABAergic inhibition or DA denervation of A11 induces trigeminal
   analgesia — A11 is part of descending pain modulation system
   distinct from PAG/RVM — [Charbit Storer Goadsby 2010,
    Cephalalgia/J Comp Neurol]
4. A11 dysfunction is the leading mechanistic hypothesis for restless
   legs syndrome (RLS); iron deficiency impairs A11 DA synthesis —
   [Clemens Rye Hochman 2006, Sleep Med Rev 10:185, "Restless legs
    syndrome: revisiting the dopamine hypothesis from the spinal cord
    perspective"] [Allen 2015]
5. 2024 AASM RLS clinical practice guideline updates first-line
   recommendations from DA agonists to gabapentinoids based on
   augmentation evidence; A11 mechanism remains explanatory model —
   [Winkelman et al. 2024 J Clin Sleep Med, AASM clinical practice
    guideline for RLS and PLMD]

INPUTS (from prior_results)
============================
- HypothalamicSupramammillary.sum_drive
- DescendingPainGate.inhibitory_drive
- DescendingPainGate.expected_pain_modulation
- SpinalDorsalHornGate.gate_state
- SpinalDorsalHornGate.ascending_nociceptive_signal
- TrigeminalSensoryComplex.vsp_caudalis_drive
- ArousalRegulator.tonic_level
- SleepWakeFlipFlop.sleep_wake_state
- IronStatusProxy.iron_deficit (optional; default 0)

OUTPUTS (to brain_runner enrichment)
=====================================
- a11_drive (0.0-1.0): A11 DA output
- spinal_da_release (0.0-1.0): spinal cord DA release
- spinal_pain_modulation (signed -1..+1): + facilitate, - inhibit
- iml_sympathetic_modulation (0.0-1.0): A11 → IML sympathetic
- trigeminal_modulation (0.0-1.0): A11 → trigeminal pain modulation
- rls_marker (bool): chronic A11 hypofunction
- a11_state (str): "tonic" | "analgesia" | "rls_low" | "iron_deficient" | "quiet"

brain_runner enrichment:
    a11 = all_results.get("A11DiencephalospinalDopamine", {})
    if a11:
        enrichments["brain_a11_drive"] = a11.get("a11_drive", 0.3)
        enrichments["brain_spinal_da"] = a11.get("spinal_da_release", 0.3)
        enrichments["brain_spinal_pain_modulation"] = a11.get("spinal_pain_modulation", 0.0)
        enrichments["brain_rls_marker"] = a11.get("rls_marker", False)
        enrichments["brain_a11_state"] = a11.get("a11_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class A11DiencephalospinalDopamine(BrainMechanism):
    BASELINE = 0.30
    RLS_THRESHOLD_TICKS = 80
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="A11DiencephalospinalDopamine",
            human_analog="A11 hypothalamic DA (diencephalospinal — pain modulation, RLS)",
            layer="foundational",
        )
        self.state.setdefault("a11_drive", self.BASELINE)
        self.state.setdefault("spinal_da_release", self.BASELINE)
        self.state.setdefault("spinal_pain_modulation", 0.0)
        self.state.setdefault("iml_sympathetic_modulation", 0.0)
        self.state.setdefault("trigeminal_modulation", 0.0)
        self.state.setdefault("rls_marker", False)
        self.state.setdefault("a11_state", "tonic")
        self.state.setdefault("low_a11_streak", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _a11_drive_target(self, sum_d: float, descending_inh: float, arousal: float,
                           sleep_state: str, iron_deficit: float) -> float:
        """A11 drive — hypothalamic state-dependent."""
        target = self.BASELINE
        target += sum_d * 0.2
        target += descending_inh * 0.2  # parallel to PAG-RVM inhibitory tone
        target += max(0.0, arousal - 0.4) * 0.2
        # Sleep state — A11 fires throughout but somewhat reduced in NREM
        if sleep_state == "SLEEP":
            target *= 0.85
        # Iron deficiency reduces A11 DA synthesis
        target -= iron_deficit * 0.6
        return max(0.0, min(1.0, target))

    def _spinal_da_release(self, a11: float) -> float:
        """Spinal DA release — proportional to A11 firing."""
        return min(1.0, a11 * 0.95)

    def _spinal_pain_modulation(self, spinal_da: float, descending_inh: float,
                                  expected_pain: float) -> float:
        """Net spinal pain modulation — high A11 → inhibitory (-);
        low A11 → release of pain (+).
        """
        # A11 normally provides tonic anti-nociceptive (inhibitory) tone
        # Low A11 = release facilitation
        baseline_inhibitory = -0.3 * spinal_da
        if spinal_da < 0.20:
            # Hypoactive — facilitates pain
            return min(1.0, max(0.0, expected_pain) * 0.5 + (0.20 - spinal_da) * 1.5)
        return max(-1.0, baseline_inhibitory)

    def _iml_sympathetic(self, a11: float) -> float:
        """A11 → IML sympathetic modulation."""
        return min(1.0, a11 * 0.6)

    def _trigeminal_modulation(self, spinal_da: float, vsp_caudalis: float) -> float:
        """A11 → trigeminal pain modulation. Inhibitory tone."""
        if vsp_caudalis < 0.20:
            return spinal_da * 0.3
        return max(0.0, min(1.0, spinal_da * 0.6 - vsp_caudalis * 0.2))

    def _detect_rls(self, streak: int) -> bool:
        return streak > self.RLS_THRESHOLD_TICKS

    def _classify_state(self, a11: float, iron_deficit: float, modulation: float,
                          rls: bool) -> str:
        if rls:
            return "rls_low"
        if iron_deficit > 0.40:
            return "iron_deficient"
        if modulation < -0.20:
            return "analgesia"
        if a11 > 0.30:
            return "tonic"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        sum_data = prior.get("HypothalamicSupramammillary", {})
        sum_d = float(sum_data.get("sum_drive", 0.10))

        dpg = prior.get("DescendingPainGate", {})
        descending_inh = float(dpg.get("inhibitory_drive", 0.30))
        expected_pain = float(dpg.get("expected_pain_modulation", 0.0))

        sdh = prior.get("SpinalDorsalHornGate", {})
        gate = float(sdh.get("gate_state", 0.30))
        ascending_noci = float(sdh.get("ascending_nociceptive_signal", 0.0))

        tsc = prior.get("TrigeminalSensoryComplex", {})
        vsp_caudalis = float(tsc.get("vsp_caudalis_drive", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")

        iron_proxy = prior.get("IronStatusProxy", {})
        iron_deficit = float(iron_proxy.get("iron_deficit", 0.0))

        # --- A11 drive ---
        a11_target = self._a11_drive_target(sum_d, descending_inh, tonic, sleep_state,
                                              iron_deficit)
        prev_a11 = float(self.state.get("a11_drive", self.BASELINE))
        new_a11 = self._smooth(prev_a11, a11_target)

        # --- Spinal DA release ---
        spinal_da = self._spinal_da_release(new_a11)
        prev_spinal = float(self.state.get("spinal_da_release", self.BASELINE))
        new_spinal = self._smooth(prev_spinal, spinal_da)

        # --- Modulation outputs ---
        modulation = self._spinal_pain_modulation(new_spinal, descending_inh, expected_pain)
        iml = self._iml_sympathetic(new_a11)
        trigeminal = self._trigeminal_modulation(new_spinal, vsp_caudalis)

        # --- RLS marker (chronic low) ---
        prev_streak = int(self.state.get("low_a11_streak", 0))
        if new_a11 < 0.20:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 2)
        rls = self._detect_rls(streak)

        state = self._classify_state(new_a11, iron_deficit, modulation, rls)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["a11_drive"] = round(new_a11, 4)
        self.state["spinal_da_release"] = round(new_spinal, 4)
        self.state["spinal_pain_modulation"] = round(modulation, 4)
        self.state["iml_sympathetic_modulation"] = round(iml, 4)
        self.state["trigeminal_modulation"] = round(trigeminal, 4)
        self.state["rls_marker"] = rls
        self.state["a11_state"] = state
        self.state["low_a11_streak"] = streak
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "a11_drive": round(new_a11, 4),
            "spinal_da_release": round(new_spinal, 4),
            "spinal_pain_modulation": round(modulation, 4),
            "iml_sympathetic_modulation": round(iml, 4),
            "trigeminal_modulation": round(trigeminal, 4),
            "rls_marker": rls,
            "a11_state": state,
        }
