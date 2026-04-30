"""
ParabigeminalEscapeRelay — PBGN Cholinergic SC-Amygdala Looming Escape Pathway

NEURAL SUBSTRATE
================
The parabigeminal nucleus (PBGN, also called PBg) is a small cholinergic
nucleus in the lateral midbrain tegmentum, just below the inferior
colliculus and adjacent to the lateral lemniscus. PBGN is reciprocally
connected with the superior colliculus (SC) — receiving SC input
(especially from deeper layers PV+ neurons) and projecting cholinergic
fibers back to SC superficial layers. This SC-PBGN-SC loop forms a
"cholinergic shell" that amplifies SC visual responses.

The Shang et al. (2018, Nat Comm) work established PBGN as the
**principal output relay for the SC-driven escape pathway** in defensive
behaviors. SC PV+ neurons projecting to PBGN drive defensive escape
(flight) responses to looming stimuli, distinct from the SC PV+ → LPTN
pathway that drives freezing. PBGN then projects to amygdala,
recruiting defensive emotional response coupled to the escape motor
output.

PBGN cholinergic neurons co-release glutamate with ACh, providing
both fast excitatory transmission and slower nicotinic/muscarinic
modulation. The dual transmitter mode is implicated in the rapid-yet-
sustained quality of escape responses.

Beyond defensive looming, PBGN also contributes to attention-related
visual processing — its cholinergic output to SC modulates visual
salience and orienting.

In Nova's substrate this provides the SC-amygdala defensive escape
relay — converts SC escape drive into amygdala recruitment plus
SC cholinergic feedback amplification.

KEY FINDINGS
============
1. Parabigeminal nucleus (PBGN) is reciprocally connected with superior
   colliculus and contains cholinergic neurons that project back to
   SC superficial layers — "cholinergic shell" of SC — [Sefton Dreher Harvey Martin 2015, "The Rat Nervous System"
    Academic Press] [Hall Lee Mize 1989, J Comp Neurol 287:495]
2. SC PV+ → PBGN pathway drives defensive escape (flight) responses
   to looming stimuli; distinct from SC PV+ → LPTN freezing pathway —
   [Shang Liu Cao Wei Wang Cao 2018, Nat Comm 9:1232, "Divergent
    midbrain circuits orchestrate escape and freezing responses to
    looming stimuli in mice"]
3. PBGN cholinergic neurons co-release glutamate with ACh — dual
   transmitter mode — [Wang Klein 2018, Trends Neurosci 41:773] [Sefton
    et al. 2015]
4. PBGN projects to amygdala and contributes to defensive emotional
   recruitment coupled to escape motor output — [Wei Liu
    Cao 2015, Nat Neurosci 18:1641, "Processing of visually evoked
    innate fear by a non-canonical thalamic pathway"]
5. PBGN cholinergic feedback to SC modulates visual salience and
   orienting — [Cui Ma Hall 2003, J Comp Neurol 466:343]

INPUTS (from prior_results)
============================
- SuperiorColliculusOrient.sc_escape_drive
- SuperiorColliculusOrient.sc_visual_drive
- SuperiorColliculusOrient.sc_orienting_command
- SuperiorColliculusOrient.looming_response_active
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- PeriaqueductalDefenseRouter.threat_imminence
- ArousalRegulator.tonic_level
- AttentionTopDownProxy.attention_focus

OUTPUTS (to brain_runner enrichment)
=====================================
- pbgn_drive (0.0-1.0): PBGN cholinergic output
- escape_relay_amygdala (0.0-1.0): PBGN → amygdala defensive recruitment
- sc_feedback_drive (0.0-1.0): PBGN → SC cholinergic feedback
- glutamate_co_release (0.0-1.0): glutamate co-transmission proxy
- escape_pathway_active (bool)
- pbgn_state (str): "quiet" | "looming" | "escape_active" | "attention"

brain_runner enrichment:
    pbgn = all_results.get("ParabigeminalEscapeRelay", {})
    if pbgn:
        enrichments["brain_pbgn_drive"] = pbgn.get("pbgn_drive", 0.1)
        enrichments["brain_escape_amygdala"] = pbgn.get("escape_relay_amygdala", 0.0)
        enrichments["brain_pbgn_sc_feedback"] = pbgn.get("sc_feedback_drive", 0.0)
        enrichments["brain_escape_pathway"] = pbgn.get("escape_pathway_active", False)
        enrichments["brain_pbgn_state"] = pbgn.get("pbgn_state", "quiet")

EXTENDED CIRCUIT NOTES
======================
6. Parabigeminal nucleus (PBGN) is a small cholinergic midbrain nucleus
   reciprocally connected to superior colliculus — provides tectal
   acetylcholine for orienting/escape gain — [Sherk 1979, Brain Res 169:497]
7. PBGN cholinergic projections set the threshold for collicular escape
   triggers — lesions blunt loom-evoked freeze responses —
   [Shang 2018, Nat Commun 9:1232, doi:10.1038/s41467-018-03580-7]
8. Reciprocal SC↔PBGN loop provides closed-loop salience amplification
   for biologically relevant stimuli — [Casagrande 1975, Brain Res 96:367]
"""

from brain.base_mechanism import BrainMechanism


class ParabigeminalEscapeRelay(BrainMechanism):
    BASELINE = 0.10
    ESCAPE_THRESHOLD = 0.50
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="ParabigeminalEscapeRelay",
            human_analog="Parabigeminal nucleus (cholinergic SC-amygdala escape relay)",
            layer="foundational",
        )
        self.state.setdefault("pbgn_drive", self.BASELINE)
        self.state.setdefault("escape_relay_amygdala", 0.0)
        self.state.setdefault("sc_feedback_drive", 0.0)
        self.state.setdefault("glutamate_co_release", 0.0)
        self.state.setdefault("escape_pathway_active", False)
        self.state.setdefault("pbgn_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _pbgn_drive_target(self, sc_escape: float, sc_visual: float, looming: bool,
                            threat: bool, valence: float, imminence: float,
                            attention: float) -> float:
        """PBGN drive — driven primarily by SC escape pathway (Shang 2018)."""
        target = self.BASELINE + sc_escape * 0.6
        target += sc_visual * 0.2
        if looming:
            target += 0.20
        if threat:
            target += valence * 0.2
        target += imminence * 0.2
        target += attention * 0.1
        return min(1.0, target)

    def _escape_relay_amygdala(self, pbgn: float, threat: bool, valence: float) -> float:
        """PBGN → amygdala defensive emotional recruitment."""
        if not threat:
            return pbgn * 0.2
        return min(1.0, pbgn * 0.7 + valence * 0.3)

    def _sc_feedback(self, pbgn: float, attention: float) -> float:
        """PBGN → SC cholinergic feedback (visual salience amplification)."""
        return min(1.0, pbgn * 0.5 + attention * 0.3)

    def _glutamate_co_release(self, pbgn: float) -> float:
        """Co-released glutamate proxy — proportional to PBGN firing."""
        return min(1.0, pbgn * 0.85)

    def _escape_active(self, pbgn: float, sc_escape: float) -> bool:
        """Escape pathway engagement."""
        return pbgn > self.ESCAPE_THRESHOLD and sc_escape > 0.40

    def _classify_state(self, pbgn: float, looming: bool, escape: bool,
                         attention: float) -> str:
        if escape:
            return "escape_active"
        if looming:
            return "looming"
        if attention > 0.55 and pbgn > 0.25:
            return "attention"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH
    def _compute_escape_readiness(self, looming: float, sc_drive: float,
                                    cholinergic: float, threat_history: list) -> float:
        """Escape-readiness signal — closed-loop SC↔PBGN gain.

        PBGN cholinergic projections set the threshold for collicular
        escape triggers; readiness combines current loom signal,
        SC orienting drive, ACh tone, and recent threat density.
        Lesion of PBGN blunts loom-evoked freeze response.
        """
        recent_threat = sum(threat_history[-10:]) / max(1, len(threat_history[-10:]))
        gain = 0.5 + cholinergic * 0.4
        readiness = (looming * 0.5 + sc_drive * 0.3 + recent_threat * 0.2) * gain
        return min(1.0, max(0.0, readiness))

    def _habituation_factor(self, repeated_stim_count: int) -> float:
        """Habituation — repeated benign loom stimuli reduce escape readiness.
        PBGN integrates stimulus history via cholinergic plasticity at
        SC reciprocal synapses (Casagrande 1975 reciprocal anatomy).
        """
        if repeated_stim_count < 3:
            return 1.0
        decay = 1.0 / (1.0 + 0.1 * (repeated_stim_count - 2))
        return max(0.30, decay)

    def _tick_summary(self) -> dict:
        """Compact state summary for downstream consumers."""
        return {
            "pbgn_drive": self.state.get("pbgn_drive", 0.0),
            "escape_ready": self.state.get("escape_readiness", 0.0),
            "habituated": self.state.get("habituation_factor", 1.0) < 0.6,
            "state": self.state.get("pbgn_state", "quiet"),
        }


    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        sc = prior.get("SuperiorColliculusOrient", {})
        sc_escape = float(sc.get("sc_escape_drive", 0.0))
        sc_visual = float(sc.get("sc_visual_drive", 0.20))
        sc_orient = float(sc.get("sc_orienting_command", 0.0))
        looming = bool(sc.get("looming_response_active", False))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        pdr = prior.get("PeriaqueductalDefenseRouter", {})
        imminence = float(pdr.get("threat_imminence", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        # --- PBGN drive ---
        pbgn_target = self._pbgn_drive_target(sc_escape, sc_visual, looming, threat,
                                                valence_intensity, imminence, attention)
        prev_pbgn = float(self.state.get("pbgn_drive", self.BASELINE))
        new_pbgn = self._smooth(prev_pbgn, pbgn_target)

        # --- Outputs ---
        amygdala_relay = self._escape_relay_amygdala(new_pbgn, threat, valence_intensity)
        sc_feedback = self._sc_feedback(new_pbgn, attention)
        glu = self._glutamate_co_release(new_pbgn)
        escape_active = self._escape_active(new_pbgn, sc_escape)

        state = self._classify_state(new_pbgn, looming, escape_active, attention)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pbgn_drive"] = round(new_pbgn, 4)
        self.state["escape_relay_amygdala"] = round(amygdala_relay, 4)
        self.state["sc_feedback_drive"] = round(sc_feedback, 4)
        self.state["glutamate_co_release"] = round(glu, 4)
        self.state["escape_pathway_active"] = escape_active
        self.state["pbgn_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pbgn_drive": round(new_pbgn, 4),
            "escape_relay_amygdala": round(amygdala_relay, 4),
            "sc_feedback_drive": round(sc_feedback, 4),
            "glutamate_co_release": round(glu, 4),
            "escape_pathway_active": escape_active,
            "pbgn_state": state,
        }
