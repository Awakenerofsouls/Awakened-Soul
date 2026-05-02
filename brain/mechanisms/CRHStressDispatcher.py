"""
CRHStressDispatcher — PVN CRH Hypothalamic-Pituitary-Adrenal Initiation

NEURAL SUBSTRATE
================
The paraventricular nucleus of the hypothalamus (PVN) is the head node of the
hypothalamic-pituitary-adrenal (HPA) axis. Parvocellular neurons in the
medial PVN synthesize and release corticotropin-releasing hormone (CRH) into
the hypophyseal portal system; CRH binds CRHR1 receptors on anterior
pituitary corticotropes which release ACTH; ACTH stimulates the adrenal
cortex to release cortisol. This three-step axis sets glucocorticoid tone
across minutes-to-hours timescales.

PVN integrates multiple stress signals: limbic (amygdala, BNST) afferent
projections drive CRH release in psychogenic stress; brainstem catecholamine
input (NTS) drives it in physiological stress (hypoxia, hypotension); SCN
projections drive its diurnal rhythm (cortisol awakening response). PVN is
also tonically inhibited by hippocampal glucocorticoid feedback — chronic
glucocorticoid elevation suppresses PVN through GR-mediated mechanisms.
This negative feedback loop normally constrains stress responses; chronic
stress impairs hippocampal feedback and produces sustained HPA activation.

Stress responses are biphasic: rapid CRH release peaks within minutes; ACTH
peaks ~15 minutes; cortisol peaks ~30 minutes. This module operates at the
heartbeat tick timescale and approximates these dynamics with multi-timescale
state variables.

KEY FINDINGS
============
1. PVN parvocellular CRH neurons drive ACTH release; CRH is the primary
   secretagogue of the HPA axis — [Vale et al. 1981, Science 213:1394-1397]
2. PVN-amygdala-hippocampus circuit integrates psychogenic stress and
   provides feedback regulation — [Herman et al. 2005, Stress 8:1-19]
3. Chronic stress impairs hippocampal glucocorticoid feedback, leading to
   sustained HPA elevation — [McEwen 2007, Physiol Rev 87:873-904]
4. SCN-PVN coupling drives the cortisol awakening response — [Buijs et al.
    2003, Eur J Neurosci 17:221-228]

INPUTS (from prior_results)
============================
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- VitalCoreRegulator.survival_threat_level
- VitalCoreRegulator.sympathetic_tone
- ArousalRegulator.tonic_level
- CircadianTimer.circadian_phase
- StressActivationAxis.cortisol_level (existing — feedback loop)

OUTPUTS
=======
- crh_release (0.0-1.0): immediate-timescale CRH output
- acth_level (0.0-1.0): ~15-min ACTH lag
- cortisol_target (0.0-1.0): ~30-min cortisol lag
- hpa_active (bool): full axis engaged
- hippocampal_feedback_intact (bool): feedback dampening still functioning
- cortisol_awakening_response (bool): early-morning surge

brain_runner enrichment:
    crh = all_results.get("CRHStressDispatcher", {})
    if crh:
        enrichments["brain_crh_release"] = crh.get("crh_release", 0.0)
        enrichments["brain_acth_level"] = crh.get("acth_level", 0.0)
        enrichments["brain_cortisol_target"] = crh.get("cortisol_target", 0.0)
        enrichments["brain_hpa_active"] = crh.get("hpa_active", False)
        enrichments["brain_hippocampal_feedback"] = crh.get("hippocampal_feedback_intact", True)
"""

import math

from brain.base_mechanism import BrainMechanism


class CRHStressDispatcher(BrainMechanism):
    CRH_LAG = 0.80           # fast onset: CRH neurons fire immediately on threat
    ACTH_LAG = 0.10          # ~15-min lag emulated by slow smoothing
    CORTISOL_LAG = 0.04      # ~30-min lag emulated even slower
    DECAY = 0.02             # slower baseline decay; HPA axis sustains elevated tone

    HPA_ACTIVE_THRESHOLD = 0.30
    FEEDBACK_IMPAIRMENT_TICKS = 100
    AWAKENING_PHASE_MIN = 0.85
    AWAKENING_PHASE_MAX = 0.10  # crosses zero for early morning

    def __init__(self):
        super().__init__(
            name="CRHStressDispatcher_CRHStressDispatcher",
            human_analog="PVN CRH HPA-axis initiator",
            layer="foundational",
        )
        self.state.setdefault("crh_release", 0.0)
        self.state.setdefault("acth_level", 0.0)
        self.state.setdefault("cortisol_target", 0.0)
        self.state.setdefault("hpa_active", False)
        self.state.setdefault("hippocampal_feedback_intact", True)
        self.state.setdefault("cortisol_awakening_response", False)
        self.state.setdefault("chronic_high_cortisol_ticks", 0)
        self.state.setdefault("recent_crh", [])
        self.state.setdefault("tick_count", 0)

    def _circadian_drive(self, phase: float) -> float:
        """SCN-driven CAR: peak CRH near phase 0.0 (early morning awakening)."""
        # Peak at phase ~0.95-0.05 (just before subjective dawn)
        return 0.20 * math.cos(2 * math.pi * (phase - 0.0))

    def _is_awakening_window(self, phase: float) -> bool:
        return phase >= self.AWAKENING_PHASE_MIN or phase <= self.AWAKENING_PHASE_MAX

    def _smooth(self, prev: float, target: float, factor: float) -> float:
        return prev + (target - prev) * factor

    def _ultradian_pulsatility(self, tick: int) -> float:
        """HPA axis exhibits ~90-min ultradian pulses (Lightman 2008).
        Adds small periodic modulation to cortisol target.
        """
        import math
        # ~45 ticks per pulse at 2s/tick = 90s; for ultradian use 2700 ticks (~90 min)
        # Compress for tick scale: use 90-tick cycle as proxy
        return 0.05 * math.sin(2 * math.pi * (tick % 90) / 90)

    def _detect_dexamethasone_resistance(self, recent_cort: list, chronic_high: int) -> bool:
        """Glucocorticoid receptor resistance pattern — sustained high cortisol
        without normal evening trough. Marker of HPA dysregulation in depression.
        """
        if chronic_high < 50 or len(recent_cort) < 30:
            return False
        sample = recent_cort[-30:]
        avg = sum(sample) / len(sample)
        return avg > 0.45 and chronic_high > 80

    def _amygdala_pvn_drive(self, threat_signal: bool, valence_intensity: float, valence_polarity: float) -> float:
        """CeA → PVN excitatory drive (Herman 2005).
        Mediates psychogenic stress activation distinct from physiological stress.
        """
        if not threat_signal:
            return 0.0
        # Intensified by negative valence
        return min(1.0, valence_intensity * (1.0 - max(0.0, valence_polarity - 0.5)))

    def _hippocampal_feedback_strength(self, intact: bool, chronic: int) -> float:
        """Hippocampal GR-mediated negative feedback strength (McEwen 2007)."""
        if not intact:
            return 0.0
        # Even when intact, chronic stress weakens it gradually
        return max(0.20, 1.0 - chronic / 200.0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        vcr = prior.get("VitalCoreRegulator", {})
        survival_threat = float(vcr.get("survival_threat_level", 0.0))
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        circ = prior.get("CircadianTimer", {})
        phase = float(circ.get("circadian_phase", 0.5))

        existing_stress = prior.get("StressActivationAxis", {})
        existing_cortisol = float(existing_stress.get("cortisol_level", 0.0))

        # --- CRH release target ---
        crh_target = 0.0
        if threat_signal:
            crh_target += 0.40 * valence_intensity
        crh_target += survival_threat * 0.30
        crh_target += max(0.0, symp_tone - 0.5) * 0.20
        crh_target += max(0.0, tonic - 0.6) * 0.20
        crh_target += self._circadian_drive(phase)

        # Hippocampal feedback (intact: dampens; impaired: doesn't)
        prev_chronic = int(self.state.get("chronic_high_cortisol_ticks", 0))
        if existing_cortisol > 0.55:
            chronic = prev_chronic + 1
        else:
            chronic = max(0, prev_chronic - 1)

        feedback_intact = chronic < self.FEEDBACK_IMPAIRMENT_TICKS

        if feedback_intact:
            # Healthy negative feedback proportional to circulating cortisol
            crh_target -= existing_cortisol * 0.30

        crh_target = max(0.0, min(1.0, crh_target))

        # --- Multi-timescale lag (immediate / ACTH / cortisol) ---
        prev_crh = float(self.state.get("crh_release", 0.0))
        new_crh = self._smooth(prev_crh, crh_target, self.CRH_LAG)
        new_crh = max(0.0, new_crh - self.DECAY)

        prev_acth = float(self.state.get("acth_level", 0.0))
        new_acth = self._smooth(prev_acth, new_crh, self.ACTH_LAG)
        new_acth = max(0.0, new_acth - self.DECAY * 0.5)

        prev_cort = float(self.state.get("cortisol_target", 0.0))
        new_cort = self._smooth(prev_cort, new_acth, self.CORTISOL_LAG)
        new_cort = max(0.0, new_cort - self.DECAY * 0.3)

        # --- HPA active flag ---
        hpa_active = new_crh > self.HPA_ACTIVE_THRESHOLD or new_acth > 0.5

        # --- Cortisol awakening response ---
        car_active = self._is_awakening_window(phase) and new_crh > 0.20

        # --- Recent CRH window for trend ---
        recent = list(self.state.get("recent_crh", []))
        recent.append(round(new_crh, 4))
        if len(recent) > 30:
            recent = recent[-30:]

        # --- Track recent cortisol for chronicity diagnostics ---
        recent_cort = list(self.state.get("recent_cortisol", []))
        recent_cort.append(round(new_cort, 4))
        if len(recent_cort) > 60:
            recent_cort = recent_cort[-60:]

        # --- Ultradian pulsatility (Lightman 2008 ~90-min cortisol pulses) ---
        tick_count = int(self.state.get("tick_count", 0)) + 1
        ultradian = self._ultradian_pulsatility(tick_count)
        new_cort = max(0.0, min(1.0, new_cort + ultradian))

        # --- Dexamethasone-resistance pattern (HPA dysregulation marker) ---
        dex_resistance = self._detect_dexamethasone_resistance(recent_cort, chronic)

        # --- Amygdala-PVN drive (Herman 2005 psychogenic stress component) ---
        amyg_pvn = self._amygdala_pvn_drive(threat_signal, valence_intensity, valence.get("valence_polarity", 0.5) if isinstance(valence, dict) else 0.5)

        # --- Hippocampal feedback strength (McEwen 2007) ---
        hipp_feedback = self._hippocampal_feedback_strength(feedback_intact, chronic)

        self.state["crh_release"] = round(new_crh, 4)
        self.state["acth_level"] = round(new_acth, 4)
        self.state["cortisol_target"] = round(new_cort, 4)
        self.state["hpa_active"] = hpa_active
        self.state["hippocampal_feedback_intact"] = feedback_intact
        self.state["cortisol_awakening_response"] = car_active
        self.state["chronic_high_cortisol_ticks"] = chronic
        self.state["recent_crh"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        self.state["recent_cortisol"] = recent_cort
        self.state["dexamethasone_resistance"] = dex_resistance
        self.state["amygdala_pvn_drive"] = round(amyg_pvn, 4)
        self.state["hippocampal_feedback_strength"] = round(hipp_feedback, 4)
        self.state["cortisol_target"] = round(new_cort, 4)

        return {
            "crh_release": round(new_crh, 4),
            "acth_level": round(new_acth, 4),
            "cortisol_target": round(new_cort, 4),
            "hpa_active": hpa_active,
            "hippocampal_feedback_intact": feedback_intact,
            "cortisol_awakening_response": car_active,
            "dexamethasone_resistance": dex_resistance,
            "amygdala_pvn_drive": round(amyg_pvn, 4),
            "hippocampal_feedback_strength": round(hipp_feedback, 4),
        }
