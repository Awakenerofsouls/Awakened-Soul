"""
PulvinarAttentionVisual — Pulvinar Higher-Order Visual Thalamus / Attention

NEURAL SUBSTRATE
================
The pulvinar is the largest thalamic nucleus in primates and a higher-
order visual thalamic structure that participates extensively in
selective visual attention. Unlike the LGN (a "first-order" thalamic
relay between retina and V1), pulvinar is a "higher-order" thalamic
nucleus that primarily relays cortico-thalamo-cortical traffic between
visual cortical areas. Pulvinar is divided into anterior, lateral,
inferior, and medial subdivisions, with the inferior and lateral pulvinar
most heavily linked to visual function.

The Saalmann/Kastner work has established pulvinar as a critical
"attention amplifier" — pulvinar synchronizes activity across cortical
visual areas at alpha (~10 Hz) frequency in line with attentional
demands, enabling selective routing of information through attended
processing channels (Saalmann et al. 2012, Science). Pulvinar lesions
produce attentional deficits including extinction and unilateral neglect
in humans.

Pulvinar receives direct retinal input via the koniocellular pathway
(small subset) and major input from superior colliculus, in addition
to its dominant cortical inputs. SC→pulvinar→cortex is a "second visual
pathway" that bypasses LGN and is implicated in residual visual
function after V1 lesion (blindsight) and in rapid orienting to threat
stimuli (Soares et al. 2017; Le et al. 2013).

Pulvinar contains both relay neurons (like classical thalamic relays)
and intrathalamic interneurons. Its multimodal subdivisions integrate
visual with auditory and somatosensory signals.

In Nova's substrate this provides the visual-attention amplifier and
salience-routing layer — converts cortical "attention focus proxy"
signals plus SC/threat input into a synchronized routing signal
to higher visual cortical areas.

KEY FINDINGS
============
1. Pulvinar synchronizes cortical visual areas at alpha frequency in
   line with attention demands — attention amplifier — [Saalmann et al.
    2012, Science 337:753-756, "The pulvinar regulates information
    transmission between cortical areas based on attention demands"]
2. Pulvinar lesions produce attentional deficits including unilateral
   neglect and visual extinction — clinical evidence — [Karnath et al.
    2002, Brain 125:350-360; reviewed Snow et al. 2009 J Neurophysiol]
3. SC→pulvinar→amygdala/cortex pathway mediates rapid threat detection
   ("blindsight" pathway) — bypasses V1 — [Soares et al. 2017,
    Curr Biol 27:1812-1820, "Midbrain-driven retinal stimulation"
    pulvinar; Le et al. 2013 Cogn Neurosci]
4. Pulvinar is functionally heterogeneous — inferior pulvinar most
   visual, medial pulvinar limbic — [reviewed Bridge et al. 2016,
    Cortex 79:65-82]
5. Pulvinar gates visual cortical processing during selective attention —
   relay-mediated routing depends on alpha phase coherence — [Zhou
    Schafer Desimone 2016, Neuron 89:209-220, "Pulvinar-Cortex
    Interactions in Vision and Attention"]

INPUTS (from prior_results)
============================
- LateralGeniculateNucleus.v1_relay
- LateralGeniculateNucleus.lgn_state
- SuperiorColliculusOrient.sc_visual_drive
- SuperiorColliculusOrient.sc_orienting_command
- ThalamicReticularNucleus.attention_gating_strength
- AttentionTopDownProxy.attention_focus
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity

OUTPUTS (to brain_runner enrichment)
=====================================
- pulvinar_drive (0.0-1.0): overall pulvinar activity
- alpha_synchrony (0.0-1.0): cortico-cortical alpha synchronization
- attention_amplification (0.0-1.0): selective attention gain
- sc_pulvinar_threat_route (0.0-1.0): blindsight / rapid-threat pathway
- cortical_routing_strength (0.0-1.0): visual cortical routing gate
- pulvinar_state (str): "quiet" | "attending" | "synchronized" | "threat_routing"

brain_runner enrichment:
    pul = all_results.get("PulvinarAttentionVisual", {})
    if pul:
        enrichments["brain_pulvinar_drive"] = pul.get("pulvinar_drive", 0.2)
        enrichments["brain_alpha_synchrony"] = pul.get("alpha_synchrony", 0.0)
        enrichments["brain_attention_amp"] = pul.get("attention_amplification", 0.0)
        enrichments["brain_sc_pulvinar_threat"] = pul.get("sc_pulvinar_threat_route", 0.0)
        enrichments["brain_pulvinar_state"] = pul.get("pulvinar_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class PulvinarAttentionVisual(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="PulvinarAttentionVisual",
            human_analog="Pulvinar higher-order visual thalamus / attention amplifier",
            layer="foundational",
        )
        self.state.setdefault("pulvinar_drive", self.BASELINE)
        self.state.setdefault("alpha_synchrony", 0.0)
        self.state.setdefault("attention_amplification", 0.0)
        self.state.setdefault("sc_pulvinar_threat_route", 0.0)
        self.state.setdefault("cortical_routing_strength", 0.30)
        self.state.setdefault("pulvinar_state", "quiet")
        self.state.setdefault("cortical_standby_suppression", 0.0)
        self.state.setdefault("threat_salience_boost", 0.0)
        self.state.setdefault("recent_attention", [])
        self.state.setdefault("tick_count", 0)

    def _pulvinar_drive_target(self, v1_relay: float, sc_visual: float,
                                attention: float, trn_att: float) -> float:
        """Overall pulvinar drive — V1 + SC + cortico-cortical attention input."""
        target = self.BASELINE + v1_relay * 0.3 + sc_visual * 0.3
        target += attention * 0.3 + trn_att * 0.2
        return min(1.0, target)

    def _alpha_synchrony(self, attention: float, pulvinar: float) -> float:
        """Cortico-cortical alpha synchronization (Saalmann 2012)."""
        return min(1.0, attention * 0.6 + pulvinar * 0.3)

    def _attention_amplification(self, alpha: float, attention: float) -> float:
        """Selective attention gain — Saalmann mechanism."""
        if attention < 0.40:
            return 0.0
        return min(1.0, alpha * 0.6 + attention * 0.4)

    def _sc_pulvinar_threat(self, sc_orient: float, threat: bool, valence: float) -> float:
        """SC→pulvinar→amygdala blindsight / rapid threat pathway (Soares 2017)."""
        if not threat:
            return 0.0
        return min(1.0, sc_orient * 0.5 + valence * 0.5)

    def _cortical_routing(self, alpha: float, amplification: float) -> float:
        """Routing strength to higher visual cortices."""
        return min(1.0, alpha * 0.5 + amplification * 0.5)

    def _classify_state(self, alpha: float, threat_route: float,
                         amplification: float, pulvinar: float) -> str:
        if threat_route > 0.40:
            return "threat_routing"
        if alpha > 0.55:
            return "synchronized"
        if amplification > 0.40:
            return "attending"
        if pulvinar < 0.25:
            return "quiet"
        return "quiet"

    def _compute_attention_bias(self, recent: list, current: float) -> float:
        """Alpha-phase attention bias — attended items bias future routing."""
        if len(recent) < 5:
            return current
        recent_avg = sum(recent[-5:]) / min(len(recent[-5:]), 5)
        # Attended items create mild sticky bias for 1-2 ticks
        bias = current * 0.85 + recent_avg * 0.15
        return min(1.0, bias)


    def _threat_salience_boost(self, pulvinar: float, attention: float,
                               threat_route: float) -> float:
        """Threat-related salience boost — pulvinar amplifies attended
        threat signals above and beyond standard attention routing.
        """
        if threat_route < 0.20:
            return 0.0
        return min(1.0, pulvinar * 0.4 + attention * 0.3 + threat_route * 0.3)


    def _cortical_standby_suppression(self, pulvinar: float, routing: float) -> float:
        """Cortical standby suppression — when pulvinar routing is weak,
        visual cortices enter a suppressed standby mode (gamma reduced,
        alpha dominance). This reflects the pulvinar's role in controlling
        which cortical area is actively processing at any moment.
        """
        if routing > 0.50:
            return 0.0  # no suppression when routing is active
        suppression = (0.50 - routing) * 2.0
        return min(1.0, suppression)

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        lgn = prior.get("LateralGeniculateNucleus", {})
        v1_relay = float(lgn.get("v1_relay", 0.0))

        sc = prior.get("SuperiorColliculusOrient", {})
        sc_visual = float(sc.get("sc_visual_drive", 0.20))
        sc_orient = float(sc.get("sc_orienting_command", 0.0))

        trn = prior.get("ThalamicReticularNucleus", {})
        trn_att = float(trn.get("attention_gating_strength", 0.40))

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        # --- Pulvinar drive ---
        pulv_target = self._pulvinar_drive_target(v1_relay, sc_visual, attention, trn_att)
        prev_pulv = float(self.state.get("pulvinar_drive", self.BASELINE))
        new_pulv = self._smooth(prev_pulv, pulv_target)

        # --- Alpha synchrony ---
        alpha_target = self._alpha_synchrony(attention, new_pulv)
        prev_alpha = float(self.state.get("alpha_synchrony", 0.0))
        new_alpha = self._smooth(prev_alpha, alpha_target)

        # --- Attention amplification ---
        amp = self._attention_amplification(new_alpha, attention)

        # --- SC threat pathway ---
        threat_route = self._sc_pulvinar_threat(sc_orient, threat, valence_intensity)

        # --- Cortical routing ---
        routing = self._cortical_routing(new_alpha, amp)

        # --- State ---
        state = self._classify_state(new_alpha, threat_route, amp, new_pulv)

        recent = list(self.state.get("recent_attention", []))
        recent.append(round(amp, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        # Apply attention bias for sticky routing
        biased_amp = self._compute_attention_bias(recent, amp)

        # --- Threat salience boost ---
        salience_boost = self._threat_salience_boost(new_pulv, attention, threat_route)

        # --- Cortical standby suppression ---
        standby = self._cortical_standby_suppression(new_pulv, routing)

        self.state["pulvinar_drive"] = round(new_pulv, 4)
        self.state["alpha_synchrony"] = round(new_alpha, 4)
        self.state["attention_amplification"] = round(biased_amp, 4)
        self.state["sc_pulvinar_threat_route"] = round(threat_route, 4)
        self.state["cortical_routing_strength"] = round(routing, 4)
        self.state["threat_salience_boost"] = round(salience_boost, 4)
        self.state["cortical_standby_suppression"] = round(standby, 4)
        self.state["pulvinar_state"] = state
        self.state["recent_attention"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pulvinar_drive": round(new_pulv, 4),
            "alpha_synchrony": round(new_alpha, 4),
            "attention_amplification": round(amp, 4),
            "sc_pulvinar_threat_route": round(threat_route, 4),
            "cortical_routing_strength": round(routing, 4),
            "pulvinar_state": state,
            "threat_salience_boost": round(salience_boost, 4),
            "cortical_standby_suppression": round(standby, 4),
        }
