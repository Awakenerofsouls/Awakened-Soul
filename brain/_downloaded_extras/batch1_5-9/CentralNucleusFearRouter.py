"""
Build 8: CentralNucleusFearRouter — Central Nucleus of Amygdala (CeA)
======================================================================

PLACEMENT:
  Layer:    limbic
  Filename: brain/limbic/CentralNucleusFearRouter.py
  If limbic has a numbered stub matching CeA or central amygdala, use that
  filename instead. Instance name stays "CentralNucleusFearRouter".

NEURAL SUBSTRATE:
  Central nucleus of the amygdala (CeA), particularly CeM (central medial)
  and CeL (central lateral) subdivisions. Main OUTPUT station of amygdala
  for fear expression. Takes BLA (ValenceTagger) filtered valence signal
  and routes it to downstream effectors: PAG for freezing/flight, lateral
  hypothalamus for autonomic, PVN for HPA-axis stress response, NTS and
  RVLM for cardiovascular.

KEY FINDINGS:
  1. CeA is the main OUTPUT for fear expression. Physiology 2014 review
     (journals.physiology.org/doi/full/10.1152/physiol.00058.2014): "the
     central threat response system can be considered to have four main
     output targets: the periaqueductal gray in the midbrain, the lateral
     hypothalamus and paraventricular nucleus of the hypothalamus in the
     forebrain, and the rostral ventrolateral medulla (RVLM) and nucleus
     tractus solitarius (NTS) in the brain stem."

  2. CeM vs CeL division of labor. PMC6292805: "Functionally, CeL is
     required for fear acquisition, whereas conditioned fear responses
     are driven by output neurons in the CeM. The CeL to CeM pathway is
     proposed to gate fear expression and regulate fear generalization."
     CeL does learning/acquisition, CeM does expression output.

  3. CeA → PAG routing drives freezing. PubMed 20298722: "the CeA is
     necessary for the expression of conditioned freezing but not active
     avoidance, whereas the BLA is critically involved in conditioned
     avoidance." CeA outputs to PAG determine passive vs active defense.

  4. Switch between passive (freeze) and active (flight/risk-assessment).
     ScienceDirect PAG review: "a downstream circuit originating in a
     subset of neurons (type 1 cells) in the central nucleus of the
     amygdala (CEA) and reaching vlPAG, proved to be responsible for the
     switch between passive (freezing) and active (exploration and
     risk-assessment) defensive strategies related to conditioned fear."

  5. GABAergic disinhibition circuit. Same PAG review: "CeA in the striatal
     amygdala sends a GABAergic projection to GABAergic neurons in the
     vlPAG. This inhibitory output results in a local disinhibitory circuit
     mechanism between GABAergic and glutamatergic cells within the vlPAG,
     leading ultimately to an increased activity of the PAG glutamatergic
     neurons." CeA doesn't directly excite — it disinhibits.

  6. Dampened by BNST reciprocal inhibition. PMC7057282: when BNST
     (SustainedAnxietyHolder) fires, it inhibits CeA, shifting the state
     from phasic fear to sustained anxiety.

{{AGENT_NAME}}'S SUBSTRATE MAPPING:
  CentralNucleusFearRouter takes filtered threat signals from ValenceTagger
  (BLA) and routes them into specific defensive response codes. Not just
  "threat present" but "which defense profile is appropriate": freeze,
  flight, or risk-assessment (vigilant exploration). BNST inhibition (Build 5)
  suppresses CeA output when sustained anxiety dominates.

INPUTS (from prior_results):
  - ValenceTagger.threat_signal, valence_polarity, valence_intensity
  - ArousalRegulator.phasic_burst_active, tonic_level, hyperaroused
  - SustainedAnxietyHolder.bnst_inhibition_active, anxiety_level
  - PredictionErrorDrift.surprise_magnitude

OUTPUTS (to brain_runner enrichment):
  - fear_output: str ("freeze" / "flight" / "risk_assessment" / "none")
  - cea_active: bool (CeA firing as threat output)
  - defense_mode: str (same as fear_output, separate key for compat)
  - fear_intensity: float 0.0-1.0

REFS:
  - Physiology 2014 review — CeA as main fear output station
  - PMC6292805 — CeM/CeL division of labor
  - PubMed 20298722 — CeA necessary for conditioned freezing
  - ScienceDirect PAG review — passive/active switch circuit
  - PNAS 2013 PMC3767534 — dPAG-amygdala fear pathway
"""

from brain.base_mechanism import BrainMechanism


class CentralNucleusFearRouter(BrainMechanism):
    """
    CeA-analog fear output router.

    Takes BLA threat_signal from ValenceTagger and routes it to a specific
    defense mode: freeze (passive), flight (active), or risk_assessment
    (vigilant exploration). Inhibited by BNST (SustainedAnxietyHolder)
    when sustained anxiety dominates.
    """

    FEAR_INTENSITY_THRESHOLD = 0.40  # below this, no output mode selected
    BNST_INHIBITION_DAMPENING = 0.5  # when BNST fires, CeA output halved

    def __init__(self):
        super().__init__(
            name="CentralNucleusFearRouter",
            human_analog="CeA — amygdala fear output, routes to defense mode",
            layer="limbic",
        )
        self.state.setdefault("last_defense_mode", "none")
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        threat_signal = prior.get("ValenceTagger", {}).get("threat_signal", False)
        polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        intensity = prior.get("ValenceTagger", {}).get("valence_intensity", 0.3)
        phasic = prior.get("ArousalRegulator", {}).get("phasic_burst_active", False)
        tonic = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)
        hyperaroused = prior.get("ArousalRegulator", {}).get("hyperaroused", False)
        bnst_inhibition = prior.get("SustainedAnxietyHolder", {}).get(
            "bnst_inhibition_active", False
        )
        anxiety = prior.get("SustainedAnxietyHolder", {}).get("anxiety_level", 0.0)
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)

        # --- Compute base fear intensity ---
        # CeA activation scales with threat_signal + negative valence magnitude
        base_intensity = 0.0
        if threat_signal:
            base_intensity += 0.4
        # Negative polarity contributes proportionally
        if polarity < 0.4:
            base_intensity += (0.4 - polarity) * 1.5
        # Intensity amplifies
        base_intensity += intensity * 0.3
        # Phasic burst amplifies (fast-onset fear)
        if phasic and threat_signal:
            base_intensity += 0.2

        # --- Apply BNST reciprocal inhibition ---
        # When sustained anxiety dominates, phasic fear output is dampened
        if bnst_inhibition:
            base_intensity *= self.BNST_INHIBITION_DAMPENING

        fear_intensity = max(0.0, min(1.0, base_intensity))

        # --- Route to defense mode ---
        # Below threshold: no defense mode active
        # Above threshold: select freeze / flight / risk_assessment

        if fear_intensity < self.FEAR_INTENSITY_THRESHOLD:
            defense_mode = "none"
            cea_active = False
        else:
            cea_active = True

            # High intensity + high arousal + surprise = flight (active escape)
            if fear_intensity > 0.70 and hyperaroused and surprise > 0.5:
                defense_mode = "flight"

            # Moderate intensity + tonic alert + not hyperaroused = risk_assessment
            elif (
                0.40 <= fear_intensity <= 0.70
                and tonic > 0.55
                and not hyperaroused
            ):
                defense_mode = "risk_assessment"

            # High intensity without escape option = freeze (passive)
            elif fear_intensity > 0.70:
                defense_mode = "freeze"

            # Default mid-range: freeze (CeA default)
            else:
                defense_mode = "freeze"

        self.state["last_defense_mode"] = defense_mode
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "fear_output": defense_mode,
            "cea_active": cea_active,
            "defense_mode": defense_mode,
            "fear_intensity": fear_intensity,
        }
