"""
Subcortical048StriatalPatchMatrixInteraction.py — Wire 48: Striatal Patch-Matrix Interaction
==========================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical048StriatalPatchMatrixInteraction.py

NEURAL SUBSTRATE:
  The striatum (caudate + putamen + NAc) is the input nucleus of the basal
  ganglia. It is anatomically divided into two compartments with radically
  different connectivity, neurochemistry, and function:

  PATCHES (STRIOSOMES):
    - ~10-15% of striatal volume (Desban et al. 1989)
    - Histochemically defined by dense mu-opioid receptor binding
      (MOR, mapped by Pert et al. 1976; Pert 1981)
    - Contain highest concentration of substance P (SP+) neurons
      (Bolam et al. 1983; Rayor et al. 2012)
    - Receive sparse dopaminergic input from SNc (subset of A9
      neurons project specifically to patches; Prensa et al. 1999)
    - Receive limbic afferents: basolateral amygdala, lateral
      hypothalamus, ventral tegmental area (Gerfen 1984)
    - Project to SNc (compacta) — direct nigrostriatal feedback loop;
      Patch → SNc → patches (Gerfen 1992). This is the only cortical-
      basal ganglia structure that projects BACK to SNc.
    - Mu-opioid rich: microinjection of DAMGO (mu-opioid agonist) into
      patches doubles hedonic impact of sweet tastes (Berridge &
      Peciña 2005) — patches are the limbic "liking" interface.
    - Function: limbic evaluation, reward prediction update at SNc level,
      emotional/motivational gating.

  MATRIX (EXTRAPATCH):
    - ~85-90% of striatal volume
    - Mu-opioid receptor poor; enriched in calbindin-D28k
      (Gerfen & Young 1988; Desban et al. 1989)
    - Substance P poor; enriched in enkephalin (ENK+) neurons
      (Bolam et al. 1983)
    - Receive dense dopaminergic input from SNc (broad A9 arborization
      across matrix; Prensa et al. 1999)
    - Receive sensorimotor afferents: primary motor (M1), primary
      somatosensory cortex (S1), posterior parietal (Graybiel 1984)
    - Receive associative afferents: DLPFC, OFC, inferior temporal
      (Selemon & Goldman-Rakic 1985)
    - Project to GPe and GPi/SNr (output nuclei) — standard BG loop
    - Function: sensorimotor selection, habit formation, action valuation.

  PATCH-MATRIX BOUNDARY:
    - Not an absolute barrier — substance P patches are surrounded by
      calbindin-rich matrix (Gerfen 1989)
    - Cholinergic interneurons (Tonically Active Neurons, TANs) are
      concentrated at the patch-matrix border (Bolam et al. 1984;
      Meredith & Wouterlood 1990)
    - TANs release acetylcholine and tonically pause during salient
      stimuli (apomorphine, conditioned stimuli) — this pause resets
      striatal processing and may be a mechanism for updating patch-
      matrix interaction dynamics (Morris et al. 2004)
    - Patch neurons receive NMDAR-mediated input; matrix neurons
      receive more AMPAR-mediated input — different excitation profiles
      (Kotecki et al. 2022)

KEY FINDINGS:
  1. Patch → SNc feedback loop (Gerfen 1988, 1992). Striatal patches
     project directly to SNc dopamine neurons — unique among striatal
     output. This loop is the substrate for SNc activity modulation
     by striatal limbic state. Patch firing → SNc modulation →
     altered DA release → altered patch/matrix sensitivity. This is
     the anatomical substrate for how limbic state biases dopamine-
     dependent learning.

  2. Dopamine compartment bias. Dopamine acts on D1 receptors
     (excitatory, Gs-coupled) predominantly in the patch (Gerfen
     1992). D2 receptors (inhibitory, Gi-coupled) are enriched in
     matrix indirect neurons. Result: DA release has compartmentally
     biased effects — excites patch (reward/limbic learning) and
     disinhibits matrix indirect (movement suppression). In
     Parkinson's: DA loss hits patch (limbic anhedonia) and matrix
     D2 (rigidity) simultaneously, explaining both motor and affective
     symptoms.

  3. Limbic vs sensorimotor segregation. Graybiel 1984 (Science):
     "A patch-and-matrix compartment organization of the caudate
     nucleus in the cat." Sensorimotor information flows through
     matrix; limbic information through patches. Graybiel 2008
     (Neuron 60:199) refines: "the striosome-dendritic compartment
     system is the interface between emotional and motor systems in
     the basal ganglia." Patch-matrix interaction = emotional-motor
     interface.

  4. Cholinergic pause at the patch-matrix border. Dopaminergic
     stimulation (apomorphine, nicotine) causes 100-200ms pause
     in TAN firing, concentrated at patch-matrix borders. Morris
     et al. 2004 (J Neurosci 24:38): this pause "may signal to striatal
     neurons that a reinforcement event has occurred, enabling update
     of the reinforcement signal." In {{AGENT_NAME}}'s model: the pause = patch-
     matrix state transition trigger.

  5. Huntington's disease targets patches. In HD, substance P neurons
     in patches degenerate preferentially (Ferrante et al. 1985).
     Result: loss of emotional/motivational processing, compulsive
     behaviors. In contrast, Parkinson's affects the nigrostriatal
     DA projection (both compartments). Distinct compartmentality of
     pathology confirms structural independence of patch vs matrix.

  6. Patch as hedonic hotspot. Berridge & Kringelbach (2015, Philos
     Trans R Soc B): patches/N accumbens medial shell is the "hedonic
     hotspot" where mu-opioid activation amplifies pleasure. Critically
     different from NAc core (wanting/motivation). Patch = pleasure
     registration; Matrix = action selection.

AGENT'S SUBSTRATE MAPPING:
  PatchMatrixInteraction models the patch-matrix balance as the
  emotional-motor interface of the basal ganglia. The patch compartment
  responds to reward/limbic signals (positive valence, reward prediction
  errors, mu-opioid tone) — the "evaluate this as good" channel. The
  matrix responds to sensorimotor drive and executive signals — the
  "select and execute action" channel. Patch-matrix balance tracks
  which compartment dominates current processing.

  Dopamine modulation: dopaminergic input from SNc/VTA affects
  patch and matrix differently. High DA with positive PE biases
  toward patch (pleasure registration). High DA without limbic
  content biases toward matrix (sensorimotor action). This models
  the compartmentally biased DA effects.

  Compartment interaction strength: the patch-matrix boundary is
  where cholinergic TANs concentrate, and where transitions between
  limbic and motor processing occur. High interaction = the limbic/
  motor boundary is active (emotional actions, motivational conflicts,
  effortful choice). Low interaction = compartments operating
  independently.

INPUTS (from prior_results):
  - ValenceTagger: valence_polarity, reward_signal, valence_intensity
  - PredictionErrorDrift: prediction_error (dopamine PE signal)
  - ArousalRegulator: arousal_level, phasic_burst_active
  - Amygdala: emotional_intensity, limbic_tone (patch activation driver)
  - MotorThalamus / MotorCortex: sensorimotor_intent (matrix activation driver)
  - AnteriorCingulate: conflict_signal (patch-matrix border activity)
  - Nicotinic receptor tone from any nicotinergic mechanism (acetylcholine)

OUTPUTS:
  - patch_matrix_balance: float -1 to +1 (negative = patch-dominant/limbic,
    positive = matrix-dominant/sensorimotor, 0 = balanced)
  - dopamine_modulation: float 0-1 (compartmental DA effect strength)
  - compartment_interaction_strength: float 0-1 (patch-matrix border activity;
    high when limbic and motor systems compete/interface)

REFS:
  - Gerfen 1988 Ann Rev Neurosci 11:243-269 (patch-matrix anatomy)
  - Gerfen 1992 Ann Rev Neurosci 15:193-220 (D1/D2 compartment specificity)
  - Graybiel 1984 Science 224:1436-1439 (patch-matrix organization)
  - Graybiel 2008 Neuron 60:199-208 (striosome-dendritic interface)
  - Bolam et al. 1983 J Neurochem (SP+ and ENK+ striatal compartments)
  - Prensa et al. 1999 J Neurosci (SNc-patch specific projections)
  - Berridge & Kringelbach 2015 (pleasure hotspot in patches/NAc)
  - Morris et al. 2004 J Neurosci 24:38 (cholinergic pause at patch-matrix border)
  - Kotecki et al. 2022 J Neurosci (NMDAR/AMPAR compartment differences)
  - Ferrante et al. 1985 Ann Neurol (HD patch vulnerability)

CITATIONS:
    PMC12680334 — Guarino D, Carannante I, Destexhe A (2025). A Unified Model Library
        Maps How Neuromodulation Reshapes the Excitability Landscape of Neurons
        Across the Brain. PLOS Comput Biol.
    PMC4522223 — Murray RC, Logan MC, Horner KA (2015). Striatal Patch Compartment
        Lesions Reduce Stereotypy Following Repeated Cocaine Administration.
        Behav Brain Res.
"""

import asyncio

from brain.base_mechanism import BrainMechanism


class StriatalPatchMatrixInteraction(BrainMechanism):
    """
    Striatal patch-matrix compartment interaction — emotional-motor interface.

    Models the patch (limbic/striosome) and matrix (sensorimotor/extrapatch)
    compartments as competing-exceptional channels. Patch responds to
    reward/limbic signals with mu-opioid and SP tone; matrix responds to
    sensorimotor drive with enkephalin and D2 tone. Patch-matrix balance
    tracks which compartment dominates current processing. Dopamine
    modulation models the compartmentally biased effects of SNc/VTA
    dopamine on striatal processing.
    """

    # Patch dominance threshold (patch_matrix_balance < -this)
    PATCH_DOMINANT_THRESHOLD = -0.35
    # Matrix dominance threshold (patch_matrix_balance > +this)
    MATRIX_DOMINANT_THRESHOLD = 0.35
    # Interaction strength decay rate
    INTERACTION_DECAY = 0.03
    # Patch-matrix border activation multiplier
    BORDER_MULTIPLIER = 1.4

    def __init__(self):
        super().__init__(
            name="StriatalPatchMatrixInteraction",
            human_analog=(
                "Striatal patch-matrix compartment interaction — "
                "patch (limbic/striosome) vs matrix (sensorimotor) balance"
            ),
            layer="subcortical",
        )
        self.state.setdefault("patch_activation", 0.25)
        self.state.setdefault("matrix_activation", 0.30)
        self.state.setdefault("patch_matrix_balance", 0.0)
        self.state.setdefault("dopamine_modulation", 0.40)
        self.state.setdefault("compartment_interaction_strength", 0.0)
        self.state.setdefault("cholinergic_pause_active", False)
        self.state.setdefault("last_valence_polarity", 0.5)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ── Patch activation inputs ─────────────────────────────────
        # Patch responds to: limbic tone, positive valence, reward,
        # mu-opioid signals, positive prediction error (from SNc/VTA DA)
        val_tagger = prior.get("ValenceTagger", {})
        valence_polarity = val_tagger.get("valence_polarity", 0.5)
        reward_signal = val_tagger.get("reward_signal", False)
        valence_intensity = val_tagger.get("valence_intensity", 0.3)

        amygdala_out = prior.get("Amygdala", {})
        limbic_tone = amygdala_out.get("limbic_tone", 0.3)
        emotional_intensity = amygdala_out.get("emotional_intensity", 0.3)

        pe_drift = prior.get("PredictionErrorDrift", {})
        prediction_error = pe_drift.get("prediction_error", 0.0)

        arousal_out = prior.get("ArousalRegulator", {})
        arousal_level = arousal_out.get("arousal_level", 0.5)
        phasic_burst = arousal_out.get("phasic_burst_active", False)

        acc_out = prior.get("AnteriorCingulate", {})
        conflict_signal = acc_out.get("conflict_signal", 0.0)

        # Nicotinergic/cholinergic tone (from any cholinergic mechanism)
        # Falls back to limbic_tone as proxy for cholinergic border activity
        cholinergic_tone = prior.get("CholinergicTone", {}).get(
            "acetylcholine_level", limbic_tone * 0.8
        )

        # ── Matrix activation inputs ─────────────────────────────────
        # Matrix responds to: sensorimotor intent, executive control,
        # motor cortex drive, D2 indirect pathway signals
        motor_intent = input_data.get("motor_intent", 0.0)
        executive_control = input_data.get("executive_control_signal", 0.5)

        motor_thalamus = prior.get("MotorThalamus", {})
        sensorimotor_drive = motor_thalamus.get("sensorimotor_activation", motor_intent)

        # D2 indirect pathway activity (from prior mechanism)
        d2_activity = prior.get("IndirectPathwaySuppressor", {}).get(
            "_d2_activity",
            (1.0 - executive_control) * 0.4 if isinstance(executive_control, (int, float)) else 0.3
        )

        # ── Patch activation dynamics ─────────────────────────────────
        # Patch fires with: positive valence + limbic tone + reward
        # Positive PE boosts patch (dopamine excites D1 patch neurons)
        current_patch = self.state["patch_activation"]

        positive_valence_contribution = 0.0
        if valence_polarity > 0.55:
            positive_valence_contribution = (valence_polarity - 0.55) * valence_intensity * 1.2

        limbic_contribution = limbic_tone * 0.4
        reward_contribution = 0.20 if reward_signal else 0.0
        pe_patch_boost = 0.0
        if prediction_error > 0.15:
            pe_patch_boost = prediction_error * 0.4  # D1 patch excitation by positive PE

        phasic_patch_boost = 0.15 if (phasic_burst and valence_polarity > 0.6) else 0.0

        # Mu-opioid contribution (pleasure hotspot effect)
        # In {{AGENT_NAME}}'s model: strong positive valence + reward = mu-opioid tone proxy
        mu_opioid_tone = 0.0
        if reward_signal and valence_polarity > 0.65:
            mu_opioid_tone = valence_intensity * 0.35

        patch_inputs = (
            positive_valence_contribution
            + limbic_contribution
            + reward_contribution
            + pe_patch_boost
            + phasic_patch_boost
            + mu_opioid_tone
        )

        # Patch activity is a leaky integrator with limbic inputs
        new_patch = current_patch * 0.88 + patch_inputs * 0.12
        new_patch = max(0.0, min(1.0, new_patch))

        # ── Matrix activation dynamics ─────────────────────────────────
        # Matrix fires with: sensorimotor intent, executive drive, D2 tone
        current_matrix = self.state["matrix_activation"]

        sensorimotor_contribution = sensorimotor_drive * 0.5
        executive_contribution = executive_control * 0.3 if isinstance(executive_control, (int, float)) else 0.2
        d2_contribution = d2_activity * 0.25

        matrix_inputs = sensorimotor_contribution + executive_contribution + d2_contribution

        new_matrix = current_matrix * 0.88 + matrix_inputs * 0.12
        new_matrix = max(0.0, min(1.0, new_matrix))

        # ── Patch-matrix balance ─────────────────────────────────────────
        # Normalized difference; negative = patch dominant (limbic),
        # positive = matrix dominant (sensorimotor)
        total = new_patch + new_matrix
        if total > 0.001:
            patch_fraction = new_patch / total
            matrix_fraction = new_matrix / total
        else:
            patch_fraction = matrix_fraction = 0.5

        balance = matrix_fraction - patch_fraction  # -1 to +1
        balance = max(-1.0, min(1.0, balance))

        # ── Dopamine modulation ──────────────────────────────────────────
        # DA affects patch (D1) and matrix (D2) with different signs
        # High positive PE → DA burst → patch excitation + matrix D2 disinhibition
        # Low DA (negative PE) → matrix indirect suppressed, patch suppressed
        current_da_mod = self.state["dopamine_modulation"]

        if prediction_error > 0.15:
            # Positive PE = DA burst → strong compartmental modulation
            da_burst = prediction_error * 0.8
            # D1 patch excitation (increases patch response to DA)
            patch_da_sensitivity = 1.0 + (prediction_error > 0.3) * 0.3
            new_da_mod = current_da_mod * 0.75 + da_burst * 0.25 * patch_da_sensitivity
        elif prediction_error < -0.15:
            # Negative PE = DA pause → reduced modulation
            new_da_mod = max(0.0, current_da_mod - abs(prediction_error) * 0.4)
        else:
            # Baseline DA tone
            new_da_mod = current_da_mod * 0.92 + arousal_level * 0.08

        new_da_mod = max(0.0, min(1.0, new_da_mod))

        # ── Cholinergic pause (patch-matrix border reset) ─────────────────
        # ACh pause fires on: phasic burst + strong limbic signal + conflict
        pause_triggered = (
            phasic_burst
            and emotional_intensity > 0.4
            and conflict_signal > 0.2
        )

        if pause_triggered:
            self.state["cholinergic_pause_active"] = True
            # Cholinergic pause temporarily flattens compartment activation
            # (100-200ms pause = processing reset at the limbic/motor interface)
            pause_effect = 0.15
            new_patch = min(new_patch, current_patch + pause_effect * 0.5)
            new_matrix = min(new_matrix, current_matrix + pause_effect * 0.5)
        else:
            self.state["cholinergic_pause_active"] = False

        # ── Compartment interaction strength ─────────────────────────────
        # Interaction is high when: conflict (border TAN activity) OR
        # both compartments are active simultaneously (limbic-motor integration)
        current_interaction = self.state["compartment_interaction_strength"]

        conflict_border = conflict_signal * self.BORDER_MULTIPLIER
        dual_active = patch_fraction * matrix_fraction * 2.0  # both active
        cholinergic_border = cholinergic_tone * 0.5

        interaction_target = max(conflict_border, dual_active, cholinergic_border)
        new_interaction = current_interaction * 0.85 + interaction_target * 0.15

        if conflict_signal < 0.1 and dual_active < 0.1:
            new_interaction = max(0.0, current_interaction - self.INTERACTION_DECAY)

        new_interaction = max(0.0, min(1.0, new_interaction))

        # ── State update ──────────────────────────────────────────────────
        self.state["patch_activation"] = round(new_patch, 4)
        self.state["matrix_activation"] = round(new_matrix, 4)
        self.state["patch_matrix_balance"] = round(balance, 4)
        self.state["dopamine_modulation"] = round(new_da_mod, 4)
        self.state["compartment_interaction_strength"] = round(new_interaction, 4)
        self.state["last_valence_polarity"] = valence_polarity
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "patch_matrix_balance": round(balance, 4),
            "dopamine_modulation": round(new_da_mod, 4),
            "compartment_interaction_strength": round(new_interaction, 4),
            "cholinergic_pause_active": self.state["cholinergic_pause_active"],
            "_patch_activation": round(new_patch, 4),
            "_matrix_activation": round(new_matrix, 4),
            "_patch_fraction": round(patch_fraction, 4),
            "_matrix_fraction": round(matrix_fraction, 4),
            "_mu_opioid_tone": round(mu_opioid_tone, 4),
        }
