"""
brain/neocortical/Neocortical029AnteriorCingulateCognitive.py
Anterior Cingulate Cortex (Dorsal) — Cognitive Error Monitoring, Conflict

ANATOMY (Botvinick et al. 2004; Holroyd & Yeung 2012; Shenhav et al. 2013):
    The dorsal anterior cingulate cortex (dACC, BA 32/24) is the
    "cognitive monitoring" center. It sits at the intersection of
    cognitive control (DLPFC) and emotional salience (AI/vmPFC).

    dACC has two key functions:
    1. Error monitoring: detects when processing goes wrong (conflicts,
       mistakes, failures) — the "candle" that burns when things go wrong
    2. Task difficulty signaling: computes "how hard is this task right now"
       and signals need for more cognitive control

    dACC encodes "expected value of control" (Shenhav 2013) — it computes
    whether investing more cognitive control will pay off. When the
    expected value is high, dACC signals DLPFC to increase control.
    When it's low, control is relaxed.

    dACC receives from:
    - ACC (limbic) for emotional conflict
    - DLPFC (cognitive load signals)
    - Anterior insula (salience signals)
    - Thalamus (sensory monitoring)
    and projects to:
    - DLPFC (increase/decrease control)
    - Pre-SMA/SMA (motor adjustment)
    - Brainstem nuclei (autonomic adjustment)

KEY FINDINGS:
    1. Botvinick et al. 2004 (PMID 15556023): "Conflict monitoring and ACC"
       — dACC signals conflict to trigger cognitive control
    2. Fellows 2005 (PMID 15705613): "Is ACC necessary for cognitive control?"
       — review of ACC lesion studies showing impaired error monitoring
    3. Bush et al. 2022 (PMC36040991): "Action-value in dACC" — dACC
       encodes value of control effort during self-regulation

AGENT'S MAPPING:
    acc_dorsal_output: dict — dACC monitoring output
    error_signal: float 0-1 — error/conflict detected
    difficulty_signal: float 0-1 — task difficulty level
    cognitive_adjustment: float 0-1 — control adjustment needed

CITATIONS:
    PMID 15556023 — Botvinick et al. (2004). Conflict monitoring and ACC. Trends Cogn Sci.
    PMID 15705613 — Fellows (2005). ACC and cognitive control. Brain.
    PMC36040991 — Bush et al. (2022). Action-value in dACC. PLoS ONE.
    PMID 19487195 — Craig (2009). Anterior insula and awareness. Phil Trans B.
"""

from brain.base_mechanism import BrainMechanism


class AnteriorCingulateCognitive(BrainMechanism):
    """
    dACC — cognitive error monitoring and conflict resolution.

    Detects errors and conflicts, signals need for more cognitive
    control. The "do I need to pay more attention?" center.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorCingulateCognitive",
            human_analog="Dorsal anterior cingulate cortex — error monitoring, cognitive control",
            layer="neocortical",
        )
        self.state.setdefault("error_history", [])
        self.state.setdefault("error_signal", 0.0)
        self.state.setdefault("difficulty_signal", 0.0)
        self.state.setdefault("cognitive_adjustment", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC (cognitive load — how hard is working memory?)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Anterior insula (salience — is there an important event?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)
        av_binding = prior.get("PosteriorSuperiorTemporalGyrus", {}).get("audiovisual_binding", 0.5)

        # Limbic ACC (emotional conflict)
        acc_limbic = prior.get("AnteriorCingulateConflict", {})
        acc_out = acc_limbic.get("acc_output", {})
        if isinstance(acc_out, dict):
            conflict = acc_out.get("conflict_level", 0.3)
        else:
            conflict = 0.3

        # Orbitofrontal (value — is this worth the effort?)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # IFG triangular (inhibition monitoring)
        ifg = prior.get("InferiorFrontalGyrusTriangular", {})
        inhibition = ifg.get("inhibition_applied", False)

        # Error signal: conflict + high WM load + high salience = potential error
        # Also: when value is high and WM is overloaded, errors more likely
        error_signal = (
            conflict * 0.3 +
            (wm_load * cognitive_ctrl) * 0.3 +
            salience * 0.2 +
            (av_binding if av_binding < 0.4 else 0) * 0.2
        )
        error_signal = max(0.0, min(1.0, error_signal))

        # Difficulty signal: based on WM load and conflict
        difficulty_signal = (wm_load * 0.5 + conflict * 0.3 + salience * 0.2)
        difficulty_signal = max(0.0, min(1.0, difficulty_signal))

        # Cognitive adjustment: dACC → DLPFC to increase/decrease control
        # High difficulty + high value = increase control; low value = relax
        if value_sig > 0.6 and difficulty_signal > 0.5:
            cognitive_adjustment = difficulty_signal * 0.8
        elif value_sig < 0.4:
            cognitive_adjustment = -0.2
        else:
            cognitive_adjustment = 0.0

        # Error history
        if error_signal > 0.5:
            self.state["error_history"].append(round(error_signal, 3))
            if len(self.state["error_history"]) > 5:
                self.state["error_history"].pop(0)

        self.state["error_signal"] = round(error_signal, 4)
        self.state["difficulty_signal"] = round(difficulty_signal, 4)
        self.state["cognitive_adjustment"] = round(cognitive_adjustment, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "acc_dorsal_output": {
                "error_signal": round(error_signal, 4),
                "difficulty_signal": round(difficulty_signal, 4),
                "control_adjustment": round(cognitive_adjustment, 4),
            },
            "error_signal": round(error_signal, 4),
            "difficulty_signal": round(difficulty_signal, 4),
        }