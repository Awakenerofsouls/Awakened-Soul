"""
Subcortical051CaudateCognitiveLoop.py — Wire 51: Caudate Cognitive Loop

Neural substrate: Caudate nucleus, cognitive associative loop.

The caudate nucleus is the medial component of the dorsal striatum,
forming the upper limb of the caudate-putamen complex (together called
the dorsal striatum). Unlike the putamen (which is somatotopically
organized and strongly motor), the caudate has a more distributed
organization and is critically involved in cognitive functions:
procedural learning, working memory, reinforcement learning, and
goal-directed behavior.

Graybiel 2000 established the chunking architecture: the caudate
contains "critically placed neurons" that learn to chunk sequences
of motor and cognitive events into reusable procedural units. Hikosaka
2019 detailed how the caudate participates in reinforcement learning,
habit formation, and memory-guided behavior in the context of the
oculomotor system.

KEY RESEARCH FINDINGS:
1. Loop architecture. Alexander, DeLong & Strick 1986: the caudate is
   part of five parallel cortico-striato-pallido-thalamo-cortical loops.
   The cognitive loop involves: PFC → caudate → GPi/SNr → VA/VLo
   thalamus → frontal cortex. Each loop processes different domains
   (motor, oculomotor, cognitive, limbic).

2. Head of caudate = working memory. Ozyurt & Turaf 2018: the caudate
   head receives dense input from prefrontal cortex (areas 8, 9, 46)
   and is critically involved in working memory maintenance. Goldman-
   Rakic 1995: "The caudate may be the basal ganglia contribution to
   the neural basis of working memory." Caudate neurons maintain
   spatially selective persistent activity during WM delay periods.

3. Procedural learning and chunking. Graybiel 1998/2000: "Cortico-
   striatal systems process habits and skills by establishing
   procedural chunks." Caudate-dependent learning produces behavior
   that becomes progressively autonomous — the caudate learns to
   chunk action sequences into single behavioral units. Lesions of
   caudate disrupt serial reaction time task (SRTT) learning.

4. Reinforcement vs. habit systems. Yin & Knowlton 2006: "The dorsal
   striatum contains two partially dissociable systems: a dorsal-
   medial (DMS) caudate system for goal-directed actions and a
   dorsal-lateral (DLS) putamen system for habits." Caudate loss
   shifts behavior toward habitual — confirming it supports
   goal-directed instrumental learning.

5. Dopamine modulation. DA from SNc modulates caudate: D1 receptors
   on direct pathway neurons (Go) and D2 receptors on indirect
   pathway neurons (NoGo). Both necessary — D1 for learning positive
   outcomes, D2 for avoiding negative ones. Frank 2005: "Dopamine
   encodes both reward prediction errors and uncertainty signals in
   the caudate." Caudate DA burst encodes positive RPE.

6. Oculomotor function. Hikosaka's group at NIMH mapped caudate
   involvement in saccade generation. caudate neurons fire during
   saccade preparation, encode target selection, and show reward-
   dependent modulation. The caudate→SNr pathway gates which saccade
   targets are selected based on expected value.

7. Aversive processing. Seymour et al. 2012: caudate processes aversive
   prediction errors too — negative RPE signals in dorsomedial caudate
   (DMS). Negative PE activates NoGo indirect pathway → behavioral
   suppression/avoidance.

8. Caudate in OCD and ADHD. The caudate is hyperactive in OCD ( Saxena
   2001) — too much top-down inhibition of motor programs, causing
   perseveration. In ADHD, caudate activity is reduced (Casey 1997) —
   difficulty maintaining the sustained activity needed for working
   memory and behavioral inhibition.

OUTPUTS:
  caudate_cognitive_signal: float 0-1 — overall caudate activation level
  procedural_learning_weight: float 0-1 — strength of chunked procedural traces
  working_memory_link: float 0-1 — caudate-PFC working memory integration

INPUTS:
  PFC_signal: prefrontal cortical input
  reward_signal: positive RPE from SNc/VP
  motor_plan: motor intention from M1/SMA
  behavioral_context: current behavioral state (learning, performing)

CITATIONS:
    PMC10681666 — Paulo DL, Qian H, Subramanian D et al. (2023). Corticostriatal
        Beta Oscillation Changes Associated With Cognitive Function in Parkinson's
        Disease. NPJ Parkinsons Dis.
    PMC5473424 — Anderson JR, Fincham JM, Qin Y et al. (2008). A Central Circuit of
        the Mind. Trends Cogn Sci.
"""

from brain.base_mechanism import BrainMechanism


class CaudateCognitiveLoop(BrainMechanism):
    """
    Caudate nucleus — cognitive/procedural/working memory system.

    Implements the cognitive associative loop of the basal ganglia,
    supporting procedural learning, working memory, and goal-directed
    action selection. Medial (DMS) portion emphasized.
    """

    PROCEDURAL_LEARNING_RATE = 0.04
    WM_LINK_LEARNING_RATE = 0.05
    DA_BOOST_GAIN = 1.5
    CAUDATE_ACTIVATION_RATE = 0.15
    WORKING_MEMORY_DECAY = 0.08

    def __init__(self):
        super().__init__(
            name="CaudateCognitiveLoop",
            human_analog="Caudate nucleus — cognitive associative loop, DMS",
            layer="subcortical",
        )
        self.state.setdefault("caudate_cognitive_signal", 0.0)
        self.state.setdefault("procedural_learning_weight", 0.4)
        self.state.setdefault("working_memory_link", 0.5)
        self.state.setdefault("dopamine_modulation", 0.5)
        self.state.setdefault("WM_activation", 0.0)
        self.state.setdefault("chunk_trace", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        PFC_signal = input_data.get("PFC_signal", 0.5)
        reward_signal = input_data.get("reward_signal", 0.0)
        motor_plan = input_data.get("motor_plan", 0.0)
        behavioral_context = input_data.get("behavioral_context", "learning")
        negative_pe = input_data.get("negative_prediction_error", 0.0)

        # --- Dopamine modulation ---
        # DA boost encodes positive RPE; negative PE suppresses activity
        DA_mod = self.state["dopamine_modulation"]
        if reward_signal > 0.3:
            # Positive RPE — DA burst, caudate activates
            DA_mod += self.DA_BOOST_GAIN * reward_signal * 0.1
        if negative_pe > 0.2:
            # Negative RPE — caudate suppressed via indirect pathway
            DA_mod -= negative_pe * 0.15

        DA_mod = max(0.0, min(1.0, DA_mod))
        self.state["dopamine_modulation"] = DA_mod

        # --- Cognitive signal computation ---
        # Caudate integrates PFC (cognitive), motor plan (procedural), and DA
        PFC_contribution = PFC_signal * 0.4 * (0.5 + DA_mod)
        motor_contribution = motor_plan * 0.25 * self.state["procedural_learning_weight"]
        context_factor = 1.0 if behavioral_context == "learning" else 0.6
        DA_contribution = DA_mod * 0.35

        raw_cognitive = (PFC_contribution + motor_contribution + DA_contribution) * context_factor
        caudate_cognitive_signal = max(0.0, min(1.0, raw_cognitive))

        # --- Working memory integration ---
        # Caudate head maintains WM via persistent activity during delay
        # WM_activation tracks how strongly WM is being maintained
        WM_delta = (PFC_signal - self.state["WM_activation"]) * self.WM_LINK_LEARNING_RATE
        if behavioral_context == "holding":
            WM_delta *= 1.5  # amplified when actively holding WM
        WM_activation = self.state["WM_activation"] + WM_delta
        WM_activation = max(0.0, min(1.0, WM_activation))

        # Decay WM activation when motor action fires
        if motor_plan > 0.6:
            WM_activation *= 0.7

        self.state["WM_activation"] = WM_activation

        # WM link: stronger when PFC and caudate are co-active
        WM_link_delta = self.WM_LINK_LEARNING_RATE * (PFC_signal * caudate_cognitive_signal - self.state["working_memory_link"])
        new_WM_link = self.state["working_memory_link"] + WM_link_delta
        self.state["working_memory_link"] = max(0.2, min(0.95, new_WM_link))

        # --- Procedural learning ---
        # Motor plan + reward = chunk formation (Graybiel 2000)
        if reward_signal > 0.3 and motor_plan > 0.3:
            chunk_increment = self.PROCEDURAL_LEARNING_RATE * reward_signal * motor_plan
            self.state["chunk_trace"] = min(1.0, self.state["chunk_trace"] + chunk_increment)
        else:
            self.state["chunk_trace"] *= 0.95

        # Procedural weight grows with chunk trace
        if self.state["chunk_trace"] > 0.5:
            self.state["procedural_learning_weight"] = min(
                0.9, self.state["procedural_learning_weight"] + 0.02
            )
        else:
            self.state["procedural_learning_weight"] *= 0.995

        self.state["caudate_cognitive_signal"] = caudate_cognitive_signal
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "caudate_cognitive_signal": round(caudate_cognitive_signal, 4),
            "procedural_learning_weight": round(self.state["procedural_learning_weight"], 4),
            "working_memory_link": round(self.state["working_memory_link"], 4),
            "WM_activation": round(WM_activation, 4),
            "dopamine_modulation": round(DA_mod, 4),
            "chunk_trace": round(self.state["chunk_trace"], 4),
        }