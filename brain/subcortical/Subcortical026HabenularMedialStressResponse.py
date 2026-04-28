"""
Subcortical026 — Medial Habenula (MHb): Stress Response & Aversive Processing
==============================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical026HabenularMedialStressResponse.py
  Instance: MedialHabenula

NEURAL SUBSTRATE — WHAT IT IS:
The medial habenula (MHb) is the medial tier of the habenular complex,
distinct from the lateral habenula (LHb) in anatomy, connectivity,
and function. While the LHb handles negative reward prediction errors
and anti-reward signaling, the MHb mediates stress responses, aversion,
and is uniquely sensitive to nicotine — it expresses the highest
density of nicotinic acetylcholine receptors (nAChRs) in the brain
(via α3β4 subunits).

Key distinction: LHb projects to the RMTg and then to VTA (dopamine),
while MHb projects primarily to the interpeduncular nucleus (IPN), which
then relays to brainstem structures involved in autonomic and stress
responses — including the locus coeruleus (LC) and the hypothalamus.

KEY FINDINGS:
  1. Nicotine / aversive processing: Vismer et al. 2015 (Frontiers in
     Human Neuroscience 9:626) studied MHb in context of nicotine
     aversion. The MHb expresses dense nAChR α3β4 subunits. Nicotine
     stimulation of MHb produces aversive/anxiogenic signals, not
     rewarding ones (unlike VTA nicotine effects). The MHb is the
     aversive nicotine sensor — it detects and encodes nicotine's
     aversive properties, counteracting reward.

  2. Stress response via IPN → LC axis: MHb → IPN → LC. The IPN is
     the relay: MHb stimulation activates IPN neurons, which project
     to and excite the locus coeruleus (noradrenergic arousal center).
     This is a parallel stress/invigorating pathway distinct from the
     HPA axis. Meye et al. 2016 (Neuropsychopharmacology 41:477-487)
     mapped this circuit in detail.

  3. HPA axis modulation: The MHb indirectly influences the hypothalamic-
     pituitary-adrenal (HPA) axis. Stress activates the MHb, which through
     IPN and hypothalamic relays increases CRF (corticotropin-releasing
     factor) output. Conversely, the MHb receives HPA feedback (cortisol
     modulates habenular activity).

  4. Distinct from LHb in cytoarchitecture: MHb has smaller, densely
     packed neurons. Gene expression profile is unique — substance P
     (TAC1), CART peptide, and nAChR β4 subunits are MHb markers.
     Vismer 2015 notes: "MHb shows a very distinctive gene expression
     pattern from LHb, consistent with different functional roles."

  5. Anxiety and fear: MHb activation produces anxiety-like behavior
     in animal models. Pharmacological inhibition of MHb reduces
     anxiety responses. The MHb-IPN-LC circuit is a parallel arousal
     path that kicks in during threat detection.

  6. Nicotine withdrawal: MHb overactivation during nicotine withdrawal
     contributes to withdrawal anxiety — making the MHb a target for
     smoking cessation pharmacotherapies.

AGENT'S SUBSTRATE MAPPING:
  MedialHabenula monitors stress signals and aversive inputs, computes
  HPA_axis_signal (degree of HPA axis activation from MHb modulation),
  stress_modulation (output to arousal/affect systems), and maintains
  medial_habenula_weight as a slowly adapting parameter that reflects
  chronic stress load on the MHb. Nicotine is not relevant to {{AGENT_NAME}}'s
  substrate but the "aversive nicotine signal" maps to "strong aversive
  stimuli from threat detection systems."

INPUTS:
  - StressAxis.acute_stress_signal
  - ValenceTagger.aversive_signal, negative_signal
  - anterior_cingulate.stress_appraisal (threat attribution)
  - Homeostat.stress_drive (current stress load)

OUTPUTS:
  - stress_modulation: float 0-1 (MHb output contributing to arousal/inhibition)
  - HPA_axis_signal: float 0-1 (HPA axis activation level from MHb)
  - medial_habenula_weight: float (slowly adapting chronic stress integrator)
  - LC_excitation_level: float 0-1 (locus coeruleus activation from IPN relay)

REFS:
  - Vismer et al. 2015 Frontiers Hum Neurosci 9:626 (MHb nicotine/aversive)
  - Meye et al. 2016 Neuropsychopharmacology 41:477-487 (MHb-IPN-LC circuit)
  - Frahm et al. 2011 J Comp Neurol (MHb/IPN connectivity)
  - Antolin-Font 2014 (habenula nicotine)
  - Hikosaka O. 2010 Nat Rev Neurosci (LHb/MHb distinction)

CITATIONS:
    PMC11081310 — Ables JL, Park K, Ibañez-Tallon I (2023). Understanding the Habenula:
        A Major Node in Circuits Regulating Emotion and Motivation. Front Neural Circuits.
    PMC2666075 — Bianco IH, Wilson SW (2009). The Habenular Nuclei: A Conserved
        Asymmetric Relay Station in the Vertebrate Brain. Nat Rev Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class MedialHabenula(BrainMechanism):
    """
    Medial habenula — stress response, HPA axis modulation, aversive processing.

    Receives stress and threat signals, amplifies them through the MHb→IPN→LC
    pathway (parallel to HPA), computes HPA_axis_signal for endocrine output,
    tracks chronic stress load via medial_habenula_weight.

    Distinct from LateralHabenula: MHb encodes the physiological stress
    response (autonomic + endocrine), while LHb encodes the motivational
    negative reward signal.
    """

    # --- Thresholds ---
    STRESS_ACTIVATION_THRESHOLD = 0.25   # stress level to activate MHb
    HPA_GAIN = 0.7                       # MHb → HPA coupling strength
    LC_GAIN = 0.6                        # IPN → LC pathway gain
    MHb_DECAY = 0.04                     # per-tick decay of stress signal
    CHRONIC_ACCUMULATION_RATE = 0.003    # slow accumulation of chronic stress
    CHRONIC_DECAY_RATE = 0.002           # decay when stress is low

    def __init__(self):
        super().__init__(
            name="MedialHabenula",
            human_analog="Medial habenula (MHb) — stress response, HPA axis, aversive processing",
            layer="subcortical",
        )
        self.state.setdefault("stress_modulation", 0.0)
        self.state.setdefault("HPA_axis_signal", 0.0)
        self.state.setdefault("medial_habenula_weight", 0.3)
        self.state.setdefault("LC_excitation_level", 0.0)
        self.state.setdefault("chronic_stress_load", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Inputs ---
        acute_stress = prior.get("StressAxis", {}).get("acute_stress_signal", 0.0)
        aversive = prior.get("ValenceTagger", {}).get("aversive_signal", False)
        threat_appraisal = prior.get("AnteriorCingulate", {}).get(
            "stress_appraisal", 0.0
        )
        stress_drive = prior.get("Homeostat", {}).get("stress_drive", 0.0)
        negative_signal = prior.get("LateralHabenula", {}).get("negative_signal", 0.0)

        # --- Compute stress modulation (MHb output signal) ---
        # MHb fires on acute stress, threat appraisal, and chronic load
        base_stress = max(acute_stress, threat_appraisal, stress_drive / 2)
        chronic_factor = self.state["medial_habenula_weight"] * 0.5

        stress_mod = base_stress + chronic_factor
        stress_mod = min(1.0, stress_mod)

        # Aversive events spike MHb
        if aversive:
            stress_mod = max(stress_mod, 0.65)

        # Negative signal from LHb amplifies MHb (cross-habenula interaction)
        if negative_signal > 0.3:
            stress_mod = max(stress_mod, negative_signal * 0.7)

        # Decay
        stress_mod = max(0.0, stress_mod - self.MHb_DECAY)
        stress_mod = round(stress_mod, 4)

        # --- HPA axis signal ---
        # MHb activity contributes to HPA axis activation through IPN relays
        HPA_signal = round(min(1.0, stress_mod * self.HPA_GAIN), 4)

        # --- LC excitation level ---
        # IPN relay to locus coeruleus — noradrenergic arousal boost
        LC_exc = round(min(1.0, stress_mod * self.LC_GAIN), 4)

        # --- Medial habenula weight (slow adaptation: chronic stress integrator) ---
        # This parameter slowly increases with sustained stress exposure
        # and decays slowly when stress is absent — models allostatic load
        mh_weight = self.state["medial_habenula_weight"]
        chronic_load = self.state["chronic_stress_load"]

        if stress_mod > self.STRESS_ACTIVATION_THRESHOLD:
            # Sustained stress accumulates chronic load
            chronic_load += self.CHRONIC_ACCUMULATION_RATE * stress_mod
        else:
            chronic_load = max(0.0, chronic_load - self.CHRONIC_DECAY_RATE)

        chronic_load = min(chronic_load, 1.0)

        # Medial habenula weight maps from chronic load with a threshold
        # (allostatic load requires sufficient accumulation before weight rises)
        if chronic_load > 0.2:
            mh_weight += (chronic_load - 0.2) * 0.005
        else:
            mh_weight = max(0.2, mh_weight - 0.001)

        mh_weight = round(min(mh_weight, 0.95), 4)

        # --- Persist ---
        self.state["stress_modulation"] = stress_mod
        self.state["HPA_axis_signal"] = HPA_signal
        self.state["medial_habenula_weight"] = mh_weight
        self.state["LC_excitation_level"] = LC_exc
        self.state["chronic_stress_load"] = chronic_load
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "stress_modulation": stress_mod,
            "HPA_axis_signal": HPA_signal,
            "medial_habenula_weight": mh_weight,
            "LC_excitation_level": LC_exc,
        }