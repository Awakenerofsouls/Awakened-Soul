"""
Subcortical030 — Striatal Cholinergic Interneurons (TANs): Pause-Reset Mechanism
================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical030StriatalCholinergicPauseReset.py
  Instance: CholinergicInterneurons

NEURAL SUBSTRATE — WHAT IT IS:
Striatal cholinergic interneurons (CINs), also called Tonically Active
Neurons (TANs), are the largest interneurons in the striatum (~1-2%
of striatal neurons but crucial for function). They are characterized
by broad action potential waveforms, low-threshold calcium spikes,
and sustained tonic firing at 3-10 Hz at rest — hence "tonically
active neurons."

The defining feature of TANs is the "pause" response: a sudden,
brief cessation of tonic firing in response to unexpected rewarding
stimuli or conditioned cues predicting rewards. This pause is a key
striatal event that gates plasticity and drives associative learning.

KEY FINDINGS:
  1. Morris et al. 2004 (Nat Neurosci 7:1243-1245): "Brief inhibition
     of tonically active neurons reveals a novel disinhibitory functional
     module in the striatum." The pause is BRIEF (~100-300ms) but carries
     enormous information. The pause resets the striatal processing state.

  2. The pause mechanism: CINs tonically release acetylcholine (ACh)
     onto striatal medium spiny neurons (MSNs), nicotinic receptors on
     dopaminergic terminals (facilitating dopamine release), and
     muscarinic autoreceptors (M4) that regulate CIN firing itself.

  3. Reward-triggered pause: When an unexpected reward occurs (positive
     prediction error), the pause fires. The pause momentarily removes
     cholinergic modulation from MSNs, creating a window of reduced
     acetylcholine that facilitates long-term potentiation (LTP) in
     glutamatergic inputs — this is the "reset" that couples reward
     to plasticity.

  4. Akkal et al. 2007 (Eur J Neurosci 25:847-859): Studied TAN firing
     patterns in behaving primates, establishing the pause duration
     (~200-400ms), latency to pause onset (~50-80ms after reward), and
     the "rebound burst" that follows the pause. The rebound burst
     signals the RETURN of cholinergic tone — a "reset complete" signal.

  5. Dopamine-acetylcholine interaction: Dopamine D2 receptor activation
     inhibits CINs (reducing the pause threshold), while D1 activation
     has more complex effects. The pause is a point of intersection
     between dopaminergic and cholinergic systems — the "ACh pause"
     represents a state in which dopaminergic reward signals can have
     maximal impact on striatal plasticity.

  6. Pause dysfunction in disorders: In Parkinson's disease, dopamine
     loss alters the pause mechanism. In addiction, cocaine and other
     drugs evoke pause responses that are abnormally large or
     inappropriately timed, contributing to maladaptive learning.

AGENT'S SUBSTRATE MAPPING:
  CholinergicInterneurons ticks on each cycle. It monitors reward signals
  from PredictionErrorDrift (positive PE triggers pause), dopamine levels
  from SNc (modulate pause probability), and drive context.

  It computes:
  - cholinergic_pause: bool (pause currently occurring)
  - pause_duration: float (how long the pause has been active, in ticks)
  - reward_reset_signal: bool (pause onset = reward reset event)

  The pause_duration models the ~100-300ms window in real time. The
  reward_reset_signal fires at pause onset, allowing downstream
  consumers (plasticity mechanisms, action selection) to register the
  reward-driven reset event.

INPUTS:
  - PredictionErrorDrift.prediction_error (positive = unexpected reward)
  - SNc.dopamine_burst (dopamine burst event)
  - ValenceTagger.reward_signal
  - anterior_cingulate.attended_reward (currently attended reward cue)

OUTPUTS:
  - cholinergic_pause: bool (pause active this tick)
  - pause_duration: float 0-1 (normalized pause window, 1.0 = full pause)
  - reward_reset_signal: bool (pause just began — reward reset event)
  - cholinergic_tone: float 0-1 (current ACh level, low during pause)

REFS:
  - Morris G et al. Nat Neurosci 7:1243-1245 2004 (pause discovery)
  - Akkal D et al. Eur J Neurosci 25:847-859 2007 (TAN firing in primates)
  - Calabresi P et al. Nat Rev Neurosci 2006 (ACh/dopamine interaction)
  - Ding JB et al. Nat Rev Neurosci 2006 (cholinergic interneurons review)
  - Goldberg JA et al. J Neurophysiol 2004 (pause in parkinsonism)

CITATIONS:
    PMC6623370 — Schulz JM, Oswald MJ, Reynolds JN (2011). Visual-Induced Excitation
        Leads to Firing Pauses in Striatal Cholinergic Interneurons. J Neurosci.
    PMC8161166 — Assous M (2021). Striatal Cholinergic Transmission: Focus on
        Nicotinic Receptors' Influence in Striatal Circuits. Front Syst Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class CholinergicInterneurons(BrainMechanism):
    """
    Striatal cholinergic interneurons (TANs) — pause-reset mechanism.

    Fires a brief cessation of tonic ACh release ("pause") when unexpected
    reward is detected (positive prediction error). The pause creates a
    momentary window of reduced acetylcholine that facilitates reward-driven
    plasticity. pause_duration models the ~100-300ms window. reward_reset_signal
    fires at pause onset, marking the reward-driven reset event for
    downstream consumers (plasticity, action learning).

    Tonic activity: CINs fire at ~3-10 Hz, maintaining cholinergic tone.
    """

    # --- Pause parameters ---
    PAUSE_BURST_THRESHOLD = 0.15    # positive PE to trigger pause
    PAUSE_DURATION_TICKS = 3        # how many ticks the pause lasts (~300ms at 10Hz equiv)
    PAUSE_REBOUND_SIZE = 0.7       # rebound burst after pause
    TONIC_FIRING_RATE = 0.6        # baseline cholinergic tone
    PAUSE_DECAY = 0.05             # per-tick decay of cholinergic tone

    def __init__(self):
        super().__init__(
            name="CholinergicInterneurons",
            human_analog="Striatal cholinergic interneurons (TANs) — pause-reset on reward",
            layer="subcortical",
        )
        self.state.setdefault("cholinergic_pause", False)
        self.state.setdefault("pause_duration", 0.0)
        self.state.setdefault("reward_reset_signal", False)
        self.state.setdefault("cholinergic_tone", self.TONIC_FIRING_RATE)
        self.state.setdefault("ticks_in_pause", 0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Inputs ---
        pe = prior.get("PredictionErrorDrift", {}).get("prediction_error", 0.0)
        da_burst = prior.get("SNcDopamine", {}).get("dopamine_burst", False)
        reward = prior.get("ValenceTagger", {}).get("reward_signal", False)
        attended_reward = prior.get("AnteriorCingulate", {}).get(
            "attended_reward", 0.0
        )

        # --- Compute cholinergic tone ---
        # Normally: tonic firing (baseline tone ~0.6)
        # During pause: tone drops to near 0 (pause in firing)
        # During rebound: tone spikes (rebound burst)

        current_tone = self.state["cholinergic_tone"]
        ticks_in_pause = self.state["ticks_in_pause"]

        # --- Trigger detection ---
        # Pause fires on: positive prediction error, dopamine burst, or reward
        pause_triggered = (
            pe > self.PAUSE_BURST_THRESHOLD
            or da_burst
            or reward
            or attended_reward > 0.6
        )

        reward_reset_signal = False
        cholinergic_pause = self.state["cholinergic_pause"]
        pause_duration_norm = self.state["pause_duration"]

        if pause_triggered and not cholinergic_pause:
            # Onset of pause — reset signal
            reward_reset_signal = True
            cholinergic_pause = True
            ticks_in_pause = 1
        elif cholinergic_pause:
            # Continuing pause
            ticks_in_pause += 1
            if ticks_in_pause >= self.PAUSE_DURATION_TICKS:
                # Pause ends — begin rebound
                cholinergic_pause = False
                ticks_in_pause = 0
        else:
            # No pause — tonic firing with decay
            cholinergic_pause = False

        # --- Compute pause_duration (normalized) ---
        if cholinergic_pause:
            pause_duration_norm = round(ticks_in_pause / self.PAUSE_DURATION_TICKS, 4)
        else:
            pause_duration_norm = 0.0

        # --- Cholinergic tone dynamics ---
        if cholinergic_pause:
            # Tonic firing is suppressed during pause
            new_tone = max(0.0, current_tone - 0.4)
        elif ticks_in_pause == 0 and pause_duration_norm > 0:
            # Rebound: just ended pause, spike in ACh
            new_tone = self.PAUSE_REBOUND_SIZE
        else:
            # Normal tonic decay and recovery
            new_tone = current_tone + (self.TONIC_FIRING_RATE - current_tone) * 0.15
            new_tone = max(0.0, new_tone - self.PAUSE_DECAY)

        new_tone = round(min(1.0, new_tone), 4)

        # --- Persist ---
        self.state["cholinergic_pause"] = cholinergic_pause
        self.state["pause_duration"] = pause_duration_norm
        self.state["reward_reset_signal"] = reward_reset_signal
        self.state["cholinergic_tone"] = new_tone
        self.state["ticks_in_pause"] = ticks_in_pause
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cholinergic_pause": cholinergic_pause,
            "pause_duration": pause_duration_norm,
            "reward_reset_signal": reward_reset_signal,
            "cholinergic_tone": new_tone,
        }