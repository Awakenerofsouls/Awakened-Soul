"""
KollikerFusePostInspiratory — KF Post-Inspiratory / Upper-Airway / Vocalization

NEURAL SUBSTRATE
================
The Kölliker-Fuse nucleus (KF) is a small subnucleus of the dorsolateral
parabrachial complex sitting in the rostral pons, anatomically adjacent
to the medial parabrachial nucleus. KF is a critical node of the
respiratory pontine network and the principal central source of
**post-inspiratory inhibition** that terminates inspiration and
shapes the post-I phase of the respiratory cycle.

KF neurons fire predominantly during the post-inspiratory and late
inspiratory phases. Their projections target the ventral respiratory
column (BötC, preBötC, rVRG) — they directly drive the inspiratory-to-
expiratory phase transition. Selective KF lesion or silencing produces
apneustic breathing — sustained inspiratory plateau with delayed
termination — establishing KF as the obligate "off-switch" for
inspiration.

KF also controls upper-airway muscles via projections to laryngeal
motoneurons in nucleus ambiguus and to hypoglossal premotor neurons,
coordinating airway patency with respiratory phase. Glottal narrowing
during expiration (post-inspiratory laryngeal adduction) helps slow
expiratory airflow and is mediated through KF.

Beyond breathing, KF is essential for **vocalization**. Voluntary
phonation requires precise coupling of respiratory pattern, laryngeal
adduction, and supralaryngeal articulation — KF coordinates respiratory
pattern with vocalization motor patterns through its convergent control
of respiratory rhythm and laryngeal muscles. Disturbed KF function
contributes to vocal fold dysfunction and dysphonia.

KF receives input from PAG (especially vlPAG for vocalization),
nucleus tractus solitarius (chemoreceptor and vagal afferents), and
amygdala (emotional vocal modulation), and provides convergent control
of respiratory pattern with emotional and chemoreceptor input.

In the agent's substrate this provides post-inspiratory phase control and
vocalization-respiration coupling — converts preBötC inspiratory drive
into post-I termination signal, modulates upper-airway tone, and
emits vocalization-readiness signal during emotional / threat states.

KEY FINDINGS
============
1. Kölliker-Fuse is the principal source of post-inspiratory inhibition
   that terminates inspiration; KF lesion produces apneustic breathing —
   [Dutschmann Herbert 2006, Eur J Neurosci 24:1071, "The Kolliker-Fuse
    nucleus gates the postinspiratory phase of the respiratory cycle"]
2. KF projects to ventral respiratory column and controls upper-airway
   muscles via NA laryngeal motoneurons and hypoglossal premotor —
   [Dutschmann Dick 2012, Compr Physiol 2:2443, "Pontine mechanisms
    of respiratory control"]
3. KF integrates respiratory and laryngeal/airway control for
   vocalization — coordinates phonation with breathing pattern —
   [Hage Jürgens 2006, Eur J Neurosci 23:840-844; reviewed Hartmann
    Brecht 2020]
4. KF receives convergent input from PAG, NTS, and amygdala for
   emotional vocal modulation and chemoreceptor integration — [Saper
    Loewy 1980, Brain Res 197:291; reviewed Saper Stornetta 2015,
    "Central autonomic system" in The Rat Nervous System]
5. KF dysfunction contributes to apnea and vocal fold dysfunction —
   clinical relevance — [reviewed Stettner et al. 2008 Eur Respir J;
    Damasceno et al. 2014 Anaesthesiology]

INPUTS (from prior_results)
============------------
- PreBotzingerInspiration.inspiratory_rhythm
- PreBotzingerInspiration.inspiration_burst_active
- BotzingerExpiratory.post_i_drive
- BotzingerExpiratory.botc_drive
- PeriaqueductalDefenseRouter.vlPAG_drive
- ParabrachialTasteVisceral.lpbn_visceral_relay
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- CentralAmygdala.cem_output_drive
- CarotidBodyChemosensor.hypercapnia_response

OUTPUTS (to brain_runner enrichment)
=====================================
- kf_drive (0.0-1.0): KF overall output
- post_i_inhibition (0.0-1.0): post-inspiratory off-switch strength
- airway_patency_command (0.0-1.0): upper-airway muscle drive
- glottal_adduction (0.0-1.0): laryngeal closure during expiration
- vocalization_readiness (0.0-1.0): respiratory-vocal coupling
- apneustic_marker (bool): chronic loss of post-I termination
- kf_state (str): "post_inspiratory_active" | "vocalization_ready" | "apneustic" | "quiet"

brain_runner enrichment:
    kf = all_results.get("KollikerFusePostInspiratory", {})
    if kf:
        enrichments["brain_kf_drive"] = kf.get("kf_drive", 0.2)
        enrichments["brain_post_i_inhibition"] = kf.get("post_i_inhibition", 0.0)
        enrichments["brain_airway_patency"] = kf.get("airway_patency_command", 0.5)
        enrichments["brain_vocalization_ready"] = kf.get("vocalization_readiness", 0.0)
        enrichments["brain_kf_state"] = kf.get("kf_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class KollikerFusePostInspiratory(BrainMechanism):
    BASELINE = 0.20
    APNEUSTIC_THRESHOLD = 30  # 30 ticks of low KF drive = apneustic; reset rate of 2/tick
    SMOOTH = 0.30

    def __init__(self):
        super().__init__(
            name="KollikerFusePostInspiratory",
            human_analog="Kölliker-Fuse post-inspiratory / upper-airway / vocalization",
            layer="foundational",
        )
        self.state.setdefault("kf_drive", self.BASELINE)
        self.state.setdefault("post_i_inhibition", 0.0)
        self.state.setdefault("airway_patency_command", 0.50)
        self.state.setdefault("glottal_adduction", 0.0)
        self.state.setdefault("vocalization_readiness", 0.0)
        self.state.setdefault("apneustic_marker", False)
        self.state.setdefault("kf_state", "quiet")
        self.state.setdefault("low_kf_streak", 0)
        self.state.setdefault("apneustic_accumulator", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _kf_drive_target(self, inspiration: bool, rhythm: float, post_i: float,
                          vlpag: float, hypercapnia: float) -> float:
        """KF drive — peaks at I→E transition, modulated by vlPAG / chemoreceptors."""
        target = self.BASELINE
        # KF rises during late inspiration & early expiration
        if inspiration and rhythm > 0.5:
            target += 0.40
        if not inspiration and rhythm < 0.20:
            target += 0.50  # peak post-I
        target += post_i * 0.3
        target += vlpag * 0.2
        target += hypercapnia * 0.1
        return min(1.0, target)

    def _post_i_inhibition(self, kf: float, post_i: float) -> float:
        """Post-inspiratory inhibitory output — combined with BötC post-I."""
        return min(1.0, kf * 0.6 + post_i * 0.4)

    def _airway_patency(self, kf: float, threat: bool) -> float:
        """Upper-airway muscle drive — keeps airway open."""
        target = 0.40 + kf * 0.4
        if threat:
            target += 0.10
        return min(1.0, target)

    def _glottal_adduction(self, kf: float, inspiration: bool) -> float:
        """Glottal closure during expiration — slows airflow."""
        if inspiration:
            return kf * 0.2  # mostly relaxed during inspiration
        return min(1.0, kf * 0.7)

    def _vocalization_readiness(self, kf: float, vlpag: float, valence: float,
                                  cea_out: float) -> float:
        """Vocalization respiratory-laryngeal coupling.
        Engaged in emotional/threat contexts via vlPAG and CeA recruitment.
        """
        target = kf * 0.3 + vlpag * 0.4
        target += valence * 0.2 + cea_out * 0.2
        return min(1.0, target)

    def _detect_apneustic(self, streak: int, acc: float) -> bool:
        return acc > 30.0 or streak > self.APNEUSTIC_THRESHOLD

    def _classify_state(self, post_i_inh: float, voc_ready: float, apneustic: bool,
                         kf: float) -> str:
        if apneustic:
            return "apneustic"
        if voc_ready > 0.50:
            return "vocalization_ready"
        if post_i_inh > 0.40:
            return "post_inspiratory_active"
        if kf < 0.15:
            return "quiet"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        prebotc = prior.get("PreBotzingerInspiration", {})
        rhythm = float(prebotc.get("inspiratory_rhythm", 0.0))
        inspiration = bool(prebotc.get("inspiration_burst_active", False))

        botc = prior.get("BotzingerExpiratory", {})
        post_i = float(botc.get("post_i_drive", 0.20))
        botc_drive = float(botc.get("botc_drive", 0.30))

        pdr = prior.get("PeriaqueductalDefenseRouter", {})
        vlpag = float(pdr.get("vlPAG_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        cea = prior.get("CentralAmygdala", {})
        cea_out = float(cea.get("cem_output_drive", 0.0))

        cb = prior.get("CarotidBodyChemosensor", {})
        hypercapnia = float(cb.get("hypercapnia_response", 0.0))

        # --- KF drive ---
        kf_target = self._kf_drive_target(inspiration, rhythm, post_i, vlpag, hypercapnia)
        prev_kf = float(self.state.get("kf_drive", self.BASELINE))
        new_kf = self._smooth(prev_kf, kf_target)

        # --- Post-I inhibition ---
        post_i_inh = self._post_i_inhibition(new_kf, post_i)

        # --- Airway patency ---
        airway = self._airway_patency(new_kf, threat)
        prev_airway = float(self.state.get("airway_patency_command", 0.50))
        new_airway = self._smooth(prev_airway, airway)

        # --- Glottal ---
        glottal = self._glottal_adduction(new_kf, inspiration)

        # --- Vocalization readiness ---
        voc = self._vocalization_readiness(new_kf, vlpag, valence_intensity, cea_out)
        prev_voc = float(self.state.get("vocalization_readiness", 0.0))
        new_voc = self._smooth(prev_voc, voc)

        # --- Apneustic detection: accumulate deficit from absent post-I drive ---
        prev_streak = int(self.state.get("low_kf_streak", 0))
        prev_acc = float(self.state.get("apneustic_accumulator", 0.0))
        if new_kf < 0.25 and not inspiration and post_i < 0.05 and botc_drive < 0.05:
            # Post-I drive is absent — accumulate toward apneustic
            acc = prev_acc + 1.0
            streak = prev_streak + 1
        else:
            # Some post-I activity — decay accumulator and streak
            acc = max(0.0, prev_acc - 2.0)
            streak = max(0, prev_streak - 2)
        apneustic = self._detect_apneustic(streak, acc)

        # --- State ---
        state = self._classify_state(post_i_inh, new_voc, apneustic, new_kf)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["kf_drive"] = round(new_kf, 4)
        self.state["post_i_inhibition"] = round(post_i_inh, 4)
        self.state["airway_patency_command"] = round(new_airway, 4)
        self.state["glottal_adduction"] = round(glottal, 4)
        self.state["vocalization_readiness"] = round(new_voc, 4)
        self.state["apneustic_marker"] = apneustic
        self.state["kf_state"] = state
        self.state["low_kf_streak"] = streak
        self.state["apneustic_accumulator"] = acc
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "kf_drive": round(new_kf, 4),
            "post_i_inhibition": round(post_i_inh, 4),
            "airway_patency_command": round(new_airway, 4),
            "glottal_adduction": round(glottal, 4),
            "vocalization_readiness": round(new_voc, 4),
            "apneustic_marker": apneustic,
            "kf_state": state,
        }
