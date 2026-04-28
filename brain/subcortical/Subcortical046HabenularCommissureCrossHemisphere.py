"""
Subcortical046HabenularCommissureCrossHemisphere.py — Wire 46: HabenularCommissure
=================================================================================

Habenular commissure. Inter-hemispheric coordination of habenula nuclei.

Neural substrate: The habenula is a bilateral thalamic epithalamic
structure divided into medial (MHb) and lateral (LHb) subdivisions,
each further organized into subnuclei with distinct connectivity.
The habenular commissure (HC) is a compact fiber bundle that crosses
the midline at the level of the posterior third ventricle, connecting
the left and right habenulae. While small (~1mm in humans), the HC
carries remarkably dense commissural projections, especially from
the LHb, which encodes negative reward, aversion, disappointment,
and pain. The MHb is primarily cholinergic (substance P + acetylcholine)
and connects to the interpeduncular nucleus (IPN), regulating
arousal and REM sleep.

Inter-hemispheric coordination: The two habenulae are NOT independent
parallel processors. Electrophysiological recordings (Wang et al.
2022, Klepper & Herbert 2021) show synchronized firing patterns across
the commissure: unilateral LHb stimulation produces bilateral responses
in the IPN and median raphe within 5-10 ms. This suggests the HC
enables rapid bilateral integration of negative valence signals,
ensuring that aversion detected in one hemisphere affects the
whole brain's affective state simultaneously. This is functionally
critical: an unexpected negative outcome in one processing stream
should suppress reward-seeking globally.

Key functions served by HC coordination:
1. Bilateral conflict resolution: when one hemisphere signals
   "withhold" and the other "approach," the HC averages these signals
2. Shared negative affect: ensures that a threat detected anywhere
   suppresses motivation globally (LHb → raphe → serotonin)
3. Sleep-wake regulation: MHb commissural projections synchronize
   the IPN-mediated REM sleep switch
4. Pain integration: bilateral habenula responses to unilateral
   pain are coordinated via HC (fast-track anti-nociception)

Anatomical specificity: The HC is not a uniform bridge. Distinct
sub-pathways cross: some from LHb medial to LHb medial, some from
LHb lateral to LHb lateral, and some MHb-to-MHb cholinergic fibers.
Lesions of the HC disrupt bilateral synchrony without destroying
individual habenula function — confirming its role is integrative,
not essential for each habenula's basic computations.

Refs:
- Wang et al. 2022 Neuron — habenular commissure electrophysiology
- Klepper & Herbert 2021 J Comp Neurol — HC anatomy in mammals
- Bianco & Wilson 2009 Neurosci Biobehav Rev — LHb review
- Hikosaka 2010 Annu Rev Neurosci — basal ganglia and LHb
- Metzger et al. 2017 J Neurosci — habenula and pain
- Goto et al. 2005 J Neurosci — LHb-IPN-raphe pathway
- Andres et al. 1999 J Comp Neurol — habenular subnuclear organization

CITATIONS:
    PMC5797387 — Liu B, Zhou K, Wu X et al. (2018). Foxg1 Deletion Impairs the
        Development of the Epithalamus. Neuroscience.
    PMC5303669 — Torrisi S, Nord CL, Balderston NL et al. (2017). Resting State
        Connectivity of the Human Habenula at Ultra-High Field. Hum Brain Mapp.
"""

from brain.base_mechanism import BrainMechanism
import math


class HabenularCommissure(BrainMechanism):
    """
    Habenular commissure — bilateral habenula coordination.

    Models the fiber tract connecting left and right habenulae,
    enabling synchronized negative valence signaling, bilateral
    conflict averaging, and global suppression of reward-seeking
    when aversion is detected. Uses lateral habenula (LHb) signals
    as the primary driver; medial habenula (MHb) contributes
    arousal state modulation.

    The HC acts as a bilateral averaging filter: when both hemispheres
    agree on a negative signal, commissural reinforcement amplifies it
    globally. When they disagree (one-sided aversion), the HC produces
    a weaker cross-hemisphere signal that alerts but doesn't override.

    Outputs:
      cross_hemisphere_signal: bilateral averaged negative valence
      commissure_strength: fidelity of inter-hemispheric coordination
      bilateral_coherence: degree of synchronization between hemispheres
    """

    HEMISPHERE_INTEGRATION = 0.5  # how much the HC weights contralateral input
    COHERENCE_WINDOW = 12         # ticks for coherence calculation
    DECAY_RATE = 0.07             # signal decay per tick
    INHIBITORY_WEIGHT = 0.65      # LHb is predominantly inhibitory to reward

    def __init__(self):
        super().__init__(
            name="HabenularCommissure",
            human_analog="Habenular commissure — bilateral habenula integration",
            layer="subcortical",
        )
        self.state.setdefault("left_habenula_activity", 0.0)
        self.state.setdefault("right_habenula_activity", 0.0)
        self.state.setdefault("left_buffer", [])
        self.state.setdefault("right_buffer", [])
        self.state.setdefault("commissure_strength", 0.0)
        self.state.setdefault("bilateral_coherence", 0.5)
        self.state.setdefault("cross_hemisphere_signal", 0.0)
        self.state.setdefault("last_strong_bilateral_tick", -100)
        self.state.setdefault("mhB_arousal_component", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        tick = self.state.get("tick_count", 0)

        # --- Input: left and right LHb signals ---
        # Primary input: lateral habenula negative reward signals
        # In full architecture: Subcortical025Lateral habenula
        left_lhb = prior.get("LateralHabNegReward", {}).get("lhb_negative_signal", 0.0)
        right_lhb = prior.get("LateralHabNegReward", {}).get("lhb_negative_signal", 0.0)

        # Medial habenula arousal component (sleep/wake, cholinergic)
        mhb_arousal = prior.get("MedialHabStressResp", {}).get("mhb_stress_modulation", 0.3)
        mhb_arousal = mhb_arousal if mhb_arousal is not None else 0.3

        # Use valence tagger as proxy if dedicated habenula mechanisms unavailable
        if left_lhb == 0.0:
            valence = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
            # Negative valence drives LHb
            left_lhb = max(0.0, 0.5 - valence) * 0.6
        if right_lhb == 0.0:
            valence = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
            right_lhb = max(0.0, 0.5 - valence) * 0.6

        # Add asymmetry: simulate lateralized aversion signals
        # (e.g., one hemisphere processing a specific threat type)
        import random
        _seed = tick % 100
        asymmetry = 0.05 * math.sin(tick * 0.3)
        left_lhb_raw = max(0.0, min(1.0, left_lhb + asymmetry))
        right_lhb_raw = max(0.0, min(1.0, right_lhb - asymmetry))

        # --- Bilateral coherence ---
        left_buffer = list(self.state["left_buffer"])
        right_buffer = list(self.state["right_buffer"])
        left_buffer.append(left_lhb_raw)
        right_buffer.append(right_lhb_raw)
        if len(left_buffer) > self.COHERENCE_WINDOW:
            left_buffer = left_buffer[-self.COHERENCE_WINDOW:]
        if len(right_buffer) > self.COHERENCE_WINDOW:
            right_buffer = right_buffer[-self.COHERENCE_WINDOW:]

        # Pearson-like coherence: dot product of normalized vectors
        n = len(left_buffer)
        mean_l = sum(left_buffer) / n
        mean_r = sum(right_buffer) / n
        cov = sum((l - mean_l) * (r - mean_r) for l, r in zip(left_buffer, right_buffer))
        std_l = math.sqrt(sum((v - mean_l)**2 for v in left_buffer) + 0.001)
        std_r = math.sqrt(sum((v - mean_r)**2 for v in right_buffer) + 0.001)
        coherence = cov / (std_l * std_r)
        coherence = (coherence + 1.0) / 2.0  # remap to 0-1

        # EMA update for bilateral coherence
        current_coherence = self.state["bilateral_coherence"]
        bilateral_coherence = current_coherence * 0.88 + coherence * 0.12

        # --- Cross-hemisphere signal computation ---
        # When both hemispheres agree: signal reinforced
        # When asymmetric: partial cross-inhibition
        bilateral_avg = (left_lhb_raw + right_lhb_raw) / 2.0
        bilateral_diff = abs(left_lhb_raw - right_lhb_raw)

        # Cross-hemisphere transmission strength (HC fidelity)
        # Coherence boosts transmission; asymmetry attenuates it
        coherent_strength = bilateral_coherence * bilateral_avg
        asymmetric_penalty = bilateral_diff * 0.3
        hc_transmission = max(0.0, coherent_strength - asymmetric_penalty)

        # Medial habenula adds arousal component
        mhb_component = mhb_arousal * 0.2

        # Final cross-hemisphere signal: bilateral averaged LHb + MHb
        cross_signal = (
            hc_transmission * self.HEMISPHERE_INTEGRATION +
            bilateral_avg * (1 - self.HEMISPHERE_INTEGRATION) +
            mhb_component
        )
        cross_signal = max(0.0, min(1.0, cross_signal))

        # --- Commissure strength ---
        # Strength is high when both hemispheres are active and coherent
        current_strength = self.state["commissure_strength"]
        target_strength = bilateral_avg * bilateral_coherence
        commissure_strength = current_strength * 0.85 + target_strength * 0.15

        # Decay when no active signals
        if bilateral_avg < 0.1:
            commissure_strength = max(0.0, commissure_strength - 0.05)

        # --- Left/right individual habenula activity ---
        left_activity = left_lhb_raw * 0.7 + right_lhb_raw * 0.3 * bilateral_coherence
        right_activity = right_lhb_raw * 0.7 + left_lhb_raw * 0.3 * bilateral_coherence

        # Track strong bilateral events
        last_strong = self.state["last_strong_bilateral_tick"]
        if bilateral_coherence > 0.75 and bilateral_avg > 0.4:
            self.state["last_strong_bilateral_tick"] = tick
            strong_bilateral_event = True
        else:
            strong_bilateral_event = False

        # --- Persist ---
        self.state["left_habenula_activity"] = left_activity
        self.state["right_habenula_activity"] = right_activity
        self.state["left_buffer"] = left_buffer
        self.state["right_buffer"] = right_buffer
        self.state["commissure_strength"] = commissure_strength
        self.state["bilateral_coherence"] = bilateral_coherence
        self.state["cross_hemisphere_signal"] = cross_signal
        self.state["mhb_arousal_component"] = mhb_arousal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cross_hemisphere_signal": round(cross_signal, 4),
            "commissure_strength": round(commissure_strength, 4),
            "bilateral_coherence": round(bilateral_coherence, 4),
            "hemisphere_detail": {
                "left_habenula": round(left_activity, 4),
                "right_habenula": round(right_activity, 4),
                "asymmetry": round(abs(left_activity - right_activity), 4),
            },
            "medial_habenula_arousal": round(mhb_arousal, 4),
            "strong_bilateral_event": strong_bilateral_event,
            "suppression_output": round(
                cross_signal * self.INHIBITORY_WEIGHT, 4
            ),  # how much reward suppression this drives
        }
