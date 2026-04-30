"""
ParaventricularNucleusHypothalamus — PVN / HPA-Axis Driver + Magnocellular Output

NEURAL SUBSTRATE
================
The paraventricular nucleus of the hypothalamus (PVN) is the master
neuroendocrine output node. Three functionally distinct cell populations
share the nucleus:

1. **Parvocellular CRH neurons** — release corticotropin-releasing
   hormone into the hypophyseal portal system at the median eminence,
   driving anterior-pituitary ACTH release and the systemic HPA stress
   axis. Negatively regulated by glucocorticoid receptor (GR) feedback.
2. **Magnocellular AVP/oxytocin neurons** — large neurosecretory cells
   projecting to the posterior pituitary; release vasopressin (osmotic
   defense) and oxytocin (social/parturition) into systemic blood.
3. **Pre-autonomic neurons** — descend to brainstem (RVLM, NTS) and
   spinal IML to set sympathetic tone.

Inputs converge from limbic stress drivers (vSub, BNST anterolateral,
BLA), homeostatic visceral relays (NTS A2 noradrenergic), and
hypothalamic peers (DMH, ARC AgRP/POMC, MPN). vSub→PVN suppresses HPA
under safe context; BNST→PVN amplifies under threat (Herman 2003).

CRH neurons exhibit feed-forward stress recruitment + slow GR-mediated
negative feedback. Sustained activation produces allostatic load and
contributes to depression/anxiety phenotypes (Ulrich-Lai & Herman 2009).

KEY FINDINGS
============
1. PVN CRH neurons are the apex driver of the HPA stress axis; release CRH at median eminence → ACTH → cortisol cascade — [Herman JP 2003, Front Neuroendocrinol 24:151, doi:10.1016/j.yfrne.2003.07.001]
2. Limbic regulation of HPA: vSub inhibits (safe), BNST + amygdala excite (threat); convergent on PVN CRH — [Ulrich-Lai YM 2009, Nat Rev Neurosci 10:397, doi:10.1038/nrn2647]
3. PVN CRH neurons rapidly recruit sympathetic + behavioral stress responses via collaterals to brainstem premotor — [Fuzesi T 2016, Nat Commun 7:11937, doi:10.1038/ncomms11937]
4. Magnocellular AVP/oxytocin neurons of PVN release peptides centrally (dendritic) and peripherally; oxytocin involved in social/parental — [Dumais KM 2017, Front Neuroendocrinol 40:1, doi:10.1016/j.yfrne.2015.04.003]
5. Glucocorticoid receptor feedback at PVN: cortisol negatively regulates CRH neuron firing on minute-to-hour timescale — [Herman JP 2016, Compr Physiol 6:603, doi:10.1002/cphy.c150015]

INPUTS
======
- HippocampalCA1Ventral.vca1_drive (or SubiculumVentral.vsub_drive) — inhibitory
- BNSTAnterolateral.bnst_anxiety_drive — excitatory
- BasolateralAmygdala.bla_drive — excitatory
- A2NoradrenergicNTS.ne_signal — interoceptive arousal
- ValenceTagger.aversive_signal, .valence_intensity
- FluidBalanceWatcher.osmotic_signal — magnocellular AVP

OUTPUTS
=======
- pvn_drive (0-1)
- crh_release (0-1) — HPA driver
- avp_release (0-1) — magnocellular vasopressin
- oxytocin_release (0-1) — magnocellular oxytocin
- presympathetic_drive (0-1) — descending autonomic
- gr_feedback_load (0-1) — accumulated cortisol feedback
- hpa_axis_state (str): "stress_active" | "magno_release" |
  "homeostatic" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class ParaventricularNucleusHypothalamus(BrainMechanism):
    """PVN — HPA-axis driver + magnocellular neuroendocrine output."""

    BASELINE = 0.10
    SMOOTH = 0.20
    STRESS_THRESHOLD = 0.45
    GR_FEEDBACK_RATE = 0.04   # slow integrator
    GR_RECOVERY_RATE = 0.015

    def __init__(self):
        super().__init__(
            name="ParaventricularNucleusHypothalamus",
            human_analog="Paraventricular hypothalamic nucleus (HPA driver)",
            layer="subcortical",
        )
        self.state.setdefault("pvn_drive", self.BASELINE)
        self.state.setdefault("crh_release", 0.0)
        self.state.setdefault("avp_release", 0.0)
        self.state.setdefault("oxytocin_release", 0.0)
        self.state.setdefault("presympathetic_drive", 0.0)
        self.state.setdefault("gr_feedback_load", 0.0)
        self.state.setdefault("hpa_axis_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, vsub: float, bnst: float, bla: float,
                       ne: float, aversive: float) -> float:
        """PVN excitatory drive — limbic + autonomic + threat (Herman 2003).

        vSub provides DISinhibition: high vSub → less stress recruitment.
        Implemented as subtraction term proportional to safe-context input.
        """
        excitation = (bnst * 0.30 + bla * 0.25 + ne * 0.15
                        + aversive * 0.20)
        # vSub safe-context inhibition (Ulrich-Lai 2009)
        safe_inhibition = vsub * 0.20
        target = self.BASELINE + excitation - safe_inhibition
        return max(0.0, min(1.0, target))

    def _crh_release(self, drive: float, gr_load: float,
                      aversive: float) -> float:
        """Parvocellular CRH neuron output — feed-forward by drive,
        feedback-inhibited by accumulated cortisol (GR load).
        Herman 2016 GR feedback timing.
        """
        if drive < 0.20:
            return 0.0
        # Drive-driven CRH, dampened proportionally to GR load
        raw = drive * 0.6 + aversive * 0.4
        feedback_attenuation = 1.0 - min(0.7, gr_load * 0.85)
        return min(1.0, raw * feedback_attenuation)

    def _avp_release(self, drive: float, osmotic: float) -> float:
        """Magnocellular AVP — driven by osmotic + general drive
        (Bourque 2008). Osmotic input dominant when present."""
        return min(1.0, drive * 0.5 + osmotic * 0.5)

    def _oxytocin_release(self, drive: float, social_safe: float) -> float:
        """Magnocellular oxytocin — peaks in social-safe contexts
        (Dumais 2017). Not under threat."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.4 + social_safe * 0.5)

    def _presympathetic(self, drive: float, ne: float) -> float:
        """Pre-autonomic descending drive (Fuzesi 2016)."""
        return min(1.0, drive * 0.6 + ne * 0.3)

    def _gr_feedback(self, prev_load: float, crh: float) -> float:
        """Slow GR feedback integrator — accumulates with CRH release,
        recovers when CRH is low (Herman 2016)."""
        if crh > 0.20:
            return min(1.0, prev_load + crh * self.GR_FEEDBACK_RATE)
        return max(0.0, prev_load - self.GR_RECOVERY_RATE)

    def _classify_state(self, drive: float, crh: float,
                         oxytocin: float) -> str:
        if drive < 0.20:
            return "quiet"
        if crh > self.STRESS_THRESHOLD:
            return "stress_active"
        if oxytocin > 0.30:
            return "magno_release"
        return "homeostatic"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vsub_data = prior.get("HippocampalCA1Ventral", {})
        if not vsub_data:
            vsub_data = prior.get("SubiculumVentral", {})
        vsub = float(vsub_data.get("vca1_drive",
                          vsub_data.get("vsub_drive", 0.0)))

        bnst_data = prior.get("BNSTAnterolateral", {})
        if not bnst_data:
            bnst_data = prior.get("BNSTOval", {})
        bnst = float(bnst_data.get("bnst_anxiety_drive",
                          bnst_data.get("bnst_drive", 0.0)))

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        a2_data = prior.get("A2NoradrenergicNTS", {})
        ne = float(a2_data.get("ne_signal",
                          a2_data.get("noradrenergic_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))
        social_safe = 1.0 if valence.get("valence_sign", 0) > 0 else 0.0

        fluid = prior.get("FluidBalanceWatcher", {})
        osmotic = float(fluid.get("osmotic_signal", 0.0))

        target = self._drive_target(vsub, bnst, bla, ne, aversive)
        prev_drive = float(self.state.get("pvn_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        prev_gr = float(self.state.get("gr_feedback_load", 0.0))
        crh = self._crh_release(new_drive, prev_gr, aversive)
        new_gr = self._gr_feedback(prev_gr, crh)

        avp = self._avp_release(new_drive, osmotic)
        oxytocin = self._oxytocin_release(new_drive, social_safe)
        sympa = self._presympathetic(new_drive, ne)

        state = self._classify_state(new_drive, crh, oxytocin)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pvn_drive"] = round(new_drive, 4)
        self.state["crh_release"] = round(crh, 4)
        self.state["avp_release"] = round(avp, 4)
        self.state["oxytocin_release"] = round(oxytocin, 4)
        self.state["presympathetic_drive"] = round(sympa, 4)
        self.state["gr_feedback_load"] = round(new_gr, 4)
        self.state["hpa_axis_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pvn_drive": round(new_drive, 4),
            "crh_release": round(crh, 4),
            "avp_release": round(avp, 4),
            "oxytocin_release": round(oxytocin, 4),
            "presympathetic_drive": round(sympa, 4),
            "gr_feedback_load": round(new_gr, 4),
            "hpa_axis_state": state,
        }

    def _allostatic_load_index(self, recent_states: list) -> float:
        """Sustained stress = chronic HPA load (Ulrich-Lai 2009)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        s = sum(1 for x in win if x == "stress_active")
        return s / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pvn_drive", 0.0),
            "crh": self.state.get("crh_release", 0.0),
            "avp": self.state.get("avp_release", 0.0),
            "oxytocin": self.state.get("oxytocin_release", 0.0),
            "gr_load": self.state.get("gr_feedback_load", 0.0),
            "state": self.state.get("hpa_axis_state", "quiet"),
        }
