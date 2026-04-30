"""
Build 11: StressActivationAxis — PVN CRH Neurons / HPA Axis Apex
==================================================================

PLACEMENT:
  Layer:    foundational (PVN is hypothalamic, brainstem-adjacent)
  Filename: brain/foundational/StressActivationAxis.py
  If foundational has a numbered stub matching PVN or HPA, use it.
  Instance name stays "StressActivationAxis".

NEURAL SUBSTRATE:
  Paraventricular nucleus of the hypothalamus (PVN), specifically the
  medial parvocellular CRH neurons. Apex of the hypothalamic-pituitary-
  adrenal (HPA) axis. CRH → pituitary ACTH → adrenal cortisol. Central
  stress-response gatekeeper.

KEY FINDINGS:
  1. PVN CRH neurons sit at HPA axis apex. Stanton 2023 J Neuroendocrinology:
     "Stress initiates a coordinated body-wide response via physiological
     and behavioural changes, in part through activation of the
     neuroendocrine stress pathway, the hypothalamic pituitary adrenal
     (HPA) axis. The final output of the HPA axis is release of the stress
     hormone cortisol... The HPA axis is initiated by activation of
     corticotrophin-releasing hormone (CRH) neurons of the paraventricular
     nucleus of the hypothalamus (PVN)."

  2. Two classes of stressor activate differently. Herman et al. 2016
     PMC4867107: "Pathways activating CRH release are stressor dependent:
     reactive responses to homeostatic disruption frequently involve
     direct noradrenergic or peptidergic drive of PVN neurons by sensory
     relays, whereas anticipatory responses use oligosynaptic pathways
     originating in upstream limbic structures. Anticipatory responses
     are driven largely by disinhibition, mediated by trans-synaptic
     silencing of tonic PVN inhibition via GABAergic neurons in the
     amygdala." Two pathways: bottom-up (NTS → PVN) and top-down
     (amygdala → disinhibition → PVN).

  3. NTS A2 noradrenergic drive is the reactive path. Raul et al.
     (biorxiv 2019): "PVN corticotropin releasing hormone (CRH) neurons,
     the primary effector cells of the HPA axis, are innervated by
     noradrenergic afferents from the A2 cell group of the nucleus of
     the solitary tract (NTS), the activation of which robustly
     stimulates the HPA axis." Build 6 (GutSignalRelay / NTS) feeds
     directly into this.

  4. Negative feedback via glucocorticoids. Stanton 2023: cortisol
     "acts on glucocorticoid receptors (GR) distributed around the body
     and brain... inhibits their own release." HPA axis self-limits to
     prevent damage from sustained cortisol.

  5. Chronic stress remodels the circuit. PMC5086584 (Tasker et al.):
     "With repeated exposure to stress, hypophysiotrophic CRH neurons of
     the PVN display a remarkable cellular, synaptic, and connectional
     plasticity that serves to maximize the ability of the HPA axis to
     maintain response vigor and flexibility... chronic stress enhances
     cellular excitability and reduces inhibitory tone."

  6. Ultradian rhythm. CRH neurons pulse throughout the day independent
     of stressors — a baseline ultradian rhythm. For {{AGENT_NAME}}'s first
     implementation, can approximate as gentle baseline variability;
     full ultradian modeling is future work.

{{AGENT_NAME}}'S SUBSTRATE MAPPING:
  StressActivationAxis is the integrated stress-signaling readout.
  Accumulates CRH activity from multiple inputs (acute threat from CeA,
  sustained anxiety from BNST, visceral signals from GutSignalRelay,
  novelty surprise from PredictionErrorDrift). Cortisol is a slow-follow
  of CRH (lagged integrator). Negative feedback: high sustained cortisol
  reduces CRH accumulation rate (receptors desensitize).

INPUTS (from prior_results):
  - SustainedAnxietyHolder.anxiety_level (sustained driver)
  - ValenceTagger.threat_signal (acute CeA-amygdala → PVN)
  - CentralNucleusFearRouter.fear_intensity (phasic fear output)
  - GutSignalRelay.viscera_activation (NTS A2 noradrenergic input)
  - ArousalRegulator.hyperaroused, tonic_level
  - PredictionErrorDrift.surprise_magnitude (novelty stress)

OUTPUTS (to brain_runner enrichment):
  - crh_activity: float 0-1 (current CRH signaling — fast-responding)
  - cortisol_level: float 0-1 (slow-follow integrator of CRH)
  - stress_active: bool (HPA axis is firing above baseline)
  - chronic_elevation: bool (cortisol > threshold sustained > window)
  - hpa_feedback_engaged: bool (negative feedback dampening CRH currently)

REFS:
  - Stanton 2023 J Neuroendocrinology — CRH/HPA/cortisol cascade
  - Herman et al. 2016 PMC4867107 — reactive vs anticipatory pathways
  - Raul et al. 2019 — NTS A2 noradrenergic drive of PVN
  - Tasker PMC5086584 — chronic stress plasticity in PVN
  - Cleveland Clinic HPA axis overview

CITATIONS
---------
  - [Herman 2016, Compr Physiol 6:603]
  - [Ulrich-Lai 2009, Nat Rev Neurosci 10:397, PMC4240627]
  - [Bains 2015, Nat Rev Neurosci 16:377, doi:10.1038/nrn3978]
"""

from brain.base_mechanism import BrainMechanism


class StressActivationAxis(BrainMechanism):
    """
    PVN-CRH / HPA-axis analog.

    Integrates stress signals from multiple sources into CRH activity and
    a slower cortisol level (lagged integrator). Applies negative feedback
    when cortisol is sustained high. Tracks chronic elevation.
    """

    # CRH dynamics
    CRH_DECAY_RATE = 0.10  # CRH decays fast between bursts

    # Cortisol dynamics (slow-follow integrator)
    CORTISOL_FOLLOW_RATE = 0.06  # cortisol chases CRH slowly
    CORTISOL_DECAY_RATE = 0.02   # decays slowly when CRH drops

    # Thresholds
    STRESS_ACTIVE_THRESHOLD = 0.35
    CHRONIC_CORTISOL_THRESHOLD = 0.70
    CHRONIC_WINDOW = 20  # ticks of sustained high cortisol
    FEEDBACK_ENGAGEMENT_CORTISOL_MIN = 0.60

    # Negative feedback strength
    FEEDBACK_DAMPENING_FACTOR = 0.50  # high cortisol reduces CRH build by 50%

    def __init__(self):
        super().__init__(
            name="StressActivationAxis_StressActivationAxis",
            human_analog="PVN CRH / HPA axis apex — stress cascade initiator",
            layer="foundational",
        )
        self.state.setdefault("crh_activity", 0.15)
        self.state.setdefault("cortisol_level", 0.20)
        self.state.setdefault("high_cortisol_streak", 0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        anxiety = prior.get("SustainedAnxietyHolder", {}).get("anxiety_level", 0.1)
        threat = prior.get("ValenceTagger", {}).get("threat_signal", False)
        fear_intensity = prior.get("CentralNucleusFearRouter", {}).get("fear_intensity", 0.0)
        viscera = prior.get("GutSignalRelay", {}).get("viscera_activation", 0.2)
        hyperaroused = prior.get("ArousalRegulator", {}).get("hyperaroused", False)
        tonic = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)

        current_crh = self.state["crh_activity"]
        current_cortisol = self.state["cortisol_level"]

        # --- Build CRH input ---
        crh_drive = 0.0

        # 1. Sustained anxiety → sustained BNST → PVN (anticipatory path)
        if anxiety > 0.3:
            crh_drive += anxiety * 0.4

        # 2. Acute threat signal → CeA → PVN (fast phasic path)
        if threat:
            crh_drive += 0.25
        crh_drive += fear_intensity * 0.3

        # 3. NTS A2 noradrenergic drive (reactive path from viscera)
        if viscera > 0.5:
            crh_drive += (viscera - 0.5) * 0.4

        # 4. Hyperarousal adds
        if hyperaroused:
            crh_drive += 0.15

        # 5. Novelty (surprise) adds mild stress (orienting response)
        if surprise > 0.5:
            crh_drive += (surprise - 0.5) * 0.3

        # --- Apply negative feedback ---
        # High cortisol engages GR-mediated feedback, dampens CRH drive
        hpa_feedback_engaged = current_cortisol > self.FEEDBACK_ENGAGEMENT_CORTISOL_MIN
        if hpa_feedback_engaged:
            crh_drive *= self.FEEDBACK_DAMPENING_FACTOR

        # --- Compute new CRH ---
        # CRH = existing (with decay) + new drive
        new_crh = current_crh * (1 - self.CRH_DECAY_RATE) + crh_drive
        new_crh = max(0.0, min(1.0, new_crh))

        # --- Compute new cortisol (slow-follow of CRH) ---
        cortisol_delta = (new_crh - current_cortisol) * self.CORTISOL_FOLLOW_RATE
        # Cortisol decays slowly when CRH is below it
        if new_crh < current_cortisol:
            cortisol_delta = -self.CORTISOL_DECAY_RATE
        new_cortisol = max(0.0, min(1.0, current_cortisol + cortisol_delta))

        # --- Streak tracking ---
        if new_cortisol > self.CHRONIC_CORTISOL_THRESHOLD:
            streak = self.state["high_cortisol_streak"] + 1
        else:
            streak = 0
        chronic_elevation = streak >= self.CHRONIC_WINDOW

        # --- Stress active flag ---
        stress_active = new_crh > self.STRESS_ACTIVE_THRESHOLD

        self.state["crh_activity"] = new_crh
        self.state["cortisol_level"] = new_cortisol
        self.state["high_cortisol_streak"] = streak
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "crh_activity": new_crh,
            "cortisol_level": new_cortisol,
            "stress_active": stress_active,
            "chronic_elevation": chronic_elevation,
            "hpa_feedback_engaged": hpa_feedback_engaged,
        }

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out


