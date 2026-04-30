"""
SpinalDorsalHornGate — Spinal Dorsal Horn Pain Gate (Melzack-Wall Lamina I/II)

NEURAL SUBSTRATE
================
The spinal dorsal horn is the principal entry point for somatosensory
afferents into the CNS and the first stage of nociceptive processing.
It is anatomically organized into Rexed laminae I-VI, with laminae I-III
forming the most superficial pain-processing layers. Lamina I (marginal
zone) contains projection neurons sending nociceptive signals to brain
via the spinothalamic and spinoparabrachial tracts. Lamina II
(substantia gelatinosa, SG) is a dense interneuron-rich layer divided
into outer (IIo, predominantly C-fiber input) and inner (IIi, Aβ
mechanosensory) zones. Lamina V contains wide-dynamic-range (WDR)
neurons that integrate noxious and non-noxious input and project to
brainstem and thalamus.

The Melzack-Wall (1965) gate control theory established the dorsal
horn — particularly the substantia gelatinosa — as a dynamic gate that
modulates nociceptive transmission. The canonical formulation: large-
diameter Aβ fibers (touch/proprioception) excite inhibitory SG
interneurons that close the gate, suppressing T-cell (lamina I/V
projection neuron) output; small-diameter Aδ and C fibers (nociception)
inhibit those inhibitory interneurons, opening the gate. This explains
why touch/rubbing can attenuate pain — the foundational basis of TENS
and counter-stimulation analgesia.

Descending modulation from PAG-RVM-NRM (covered in DescendingPainGate
and MedullaryRapheMagnus) and from A5 (A5NoradrenergicGroup) projects
to dorsal horn, providing top-down inhibitory or facilitatory control.
Spinal serotonergic and noradrenergic terminals modulate gate state
through receptor diversity (5-HT1A, 5-HT2A, 5-HT3, α2-adrenergic).

In {{AGENT_NAME}}'s substrate this provides the spinal-level pain gate — combines
nociceptive input proxies with descending inhibition (NRM, A5, PAG)
and Aβ-style "touch suppression" to emit a final ascending nociceptive
signal that downstream pain affect mechanisms read.

KEY FINDINGS
============
1. Substantia gelatinosa (lamina II) acts as the gate of Melzack-Wall
   gate control theory — interneurons modulate transmission from
   primary afferents to projection neurons — [Melzack Wall 1965,
    Science 150:971-979, "Pain Mechanisms: A New Theory"; reviewed
    StatPearls "Neuroanatomy, Substantia Gelatinosa" NBK551522]
2. Large-diameter Aβ fibers excite inhibitory SG interneurons that
   close the gate; small-diameter Aδ/C fibers inhibit these
   interneurons opening the gate — [reviewed Frontiers Pain Res 2022
    doi:10.3389/fpain.2022.845211, "An Historical Perspective: The
    Second Order Neuron in the Pain Pathway"]
3. Dorsal horn lamina II is functionally subdivided — IIo predominantly
   nociceptive C fiber, IIi mechanosensory Aβ — distinct synaptic
   architecture — [Todd 2017 reviewed; Sandkuhler reviewed]
4. Wide-dynamic-range (WDR) neurons in lamina V integrate noxious and
   non-noxious input; sensitization of WDR underlies chronic pain
   — [Sandkühler 2009 Physiol Rev 89:707; Latremoliere Woolf 2009
    J Pain 10:895]
5. Functional populations among interneurons in laminae I-III are
   genetically defined (e.g., dynorphin, parvalbumin, somatostatin)
   with distinct gating roles — [Häring et al. 2018, Nat Neurosci
    21:869-880, "Neuronal atlas of the dorsal horn"; reviewed
    PMC5315367]

INPUTS (from prior_results)
============================
- DescendingPainGate.inhibitory_drive
- DescendingPainGate.facilitatory_drive
- DescendingPainGate.opioid_tone
- DescendingPainGate.expected_pain_modulation
- MedullaryRapheMagnus.spinal_5ht_release
- MedullaryRapheMagnus.bidirectional_balance
- A5NoradrenergicGroup.spinal_ne_visceral
- A5NoradrenergicGroup.pain_facilitation_a5
- NociceptiveInputProxy.c_fiber_input (optional; default 0)
- NociceptiveInputProxy.a_beta_input (optional; default 0)

OUTPUTS (to brain_runner enrichment)
=====================================
- gate_state (0.0-1.0): 0 = closed (analgesia), 1 = open (full transmission)
- ascending_nociceptive_signal (0.0-1.0): output to brainstem/thalamus
- substantia_gelatinosa_inhibition (0.0-1.0): SG inhibitory drive
- wdr_drive (0.0-1.0): wide-dynamic-range neuron output
- central_sensitization_marker (bool): persistent gate-open state
- a_beta_suppression (0.0-1.0): touch-mediated gating
- spinal_state (str): "closed" | "open" | "wind_up" | "centralized"

brain_runner enrichment:
    sdh = all_results.get("SpinalDorsalHornGate", {})
    if sdh:
        enrichments["brain_spinal_gate"] = sdh.get("gate_state", 0.4)
        enrichments["brain_ascending_noci"] = sdh.get("ascending_nociceptive_signal", 0.0)
        enrichments["brain_central_sens"] = sdh.get("central_sensitization_marker", False)
        enrichments["brain_spinal_state"] = sdh.get("spinal_state", "closed")
"""

from brain.base_mechanism import BrainMechanism


class SpinalDorsalHornGate(BrainMechanism):
    BASELINE_GATE = 0.30
    SENSITIZATION_TICKS = 80
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="SpinalDorsalHornGate",
            human_analog="Spinal dorsal horn gate (Melzack-Wall lamina I/II)",
            layer="foundational",
        )
        self.state.setdefault("gate_state", self.BASELINE_GATE)
        self.state.setdefault("ascending_nociceptive_signal", 0.0)
        self.state.setdefault("substantia_gelatinosa_inhibition", 0.40)
        self.state.setdefault("wdr_drive", 0.0)
        self.state.setdefault("central_sensitization_marker", False)
        self.state.setdefault("a_beta_suppression", 0.0)
        self.state.setdefault("spinal_state", "closed")
        self.state.setdefault("open_streak", 0)
        self.state.setdefault("recent_gates", [])
        self.state.setdefault("tick_count", 0)

    def _sg_inhibition_target(self, descending_inh: float, opioid_tone: float,
                                spinal_5ht: float, ne: float, a_beta: float) -> float:
        """SG inhibitory interneuron drive — closes the gate.
        Boosted by descending inhibition (NRM 5-HT, opioid, NE), Aβ touch input.
        """
        target = 0.30 + descending_inh * 0.4
        target += opioid_tone * 0.5
        target += max(0.0, spinal_5ht - 0.4) * 0.2
        target += ne * 0.2
        target += a_beta * 0.5  # Aβ excites inhibitory interneurons
        return min(1.0, target)

    def _gate_state_target(self, c_fiber: float, sg_inh: float,
                            descending_fac: float, expected_pain: float,
                            a5_pain_fac: float) -> float:
        """Open-gate state — high = transmitting, low = closed.
        C-fiber and facilitation open; SG inhibition and inhibitory tone close.
        """
        target = self.BASELINE_GATE
        target += c_fiber * 0.6  # C-fiber opens gate
        target += descending_fac * 0.3
        target += max(0.0, expected_pain) * 0.3
        target += a5_pain_fac * 0.2
        target -= sg_inh * 0.5  # SG inhibition closes gate
        return max(0.0, min(1.0, target))

    def _wdr_target(self, c_fiber: float, gate: float, sensitization: bool) -> float:
        """Wide-dynamic-range lamina V neurons. Sensitized → respond to
        non-noxious as if noxious.
        """
        target = c_fiber * 0.5 + gate * 0.4
        if sensitization:
            target += 0.20
        return max(0.0, min(1.0, target))

    def _ascending_nociceptive(self, gate: float, wdr: float,
                                 expected_pain: float) -> float:
        """Final ascending nociceptive signal to brain."""
        return min(1.0, gate * 0.6 + wdr * 0.4 + max(0.0, expected_pain - 0.5) * 0.2)

    def _a_beta_suppression(self, a_beta: float, c_fiber: float) -> float:
        """Touch-mediated suppression magnitude — Melzack-Wall classic.
        Active only when Aβ > C-fiber, demonstrating touch suppression.
        """
        if a_beta < 0.10 or a_beta < c_fiber * 0.5:
            return 0.0
        return min(1.0, a_beta * 0.7)

    def _detect_sensitization(self, streak: int) -> bool:
        return streak > self.SENSITIZATION_TICKS

    def _classify_state(self, gate: float, wdr: float, sensitized: bool,
                         streak: int) -> str:
        if sensitized:
            return "centralized"
        if streak > 30 and gate > 0.55:
            return "wind_up"
        if gate > 0.50:
            return "open"
        return "closed"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dpg = prior.get("DescendingPainGate", {})
        descending_inh = float(dpg.get("inhibitory_drive", 0.30))
        descending_fac = float(dpg.get("facilitatory_drive", 0.30))
        opioid_tone = float(dpg.get("opioid_tone", 0.0))
        expected_pain = float(dpg.get("expected_pain_modulation", 0.0))

        nrm = prior.get("MedullaryRapheMagnus", {})
        spinal_5ht = float(nrm.get("spinal_5ht_release", 0.4))
        balance = nrm.get("bidirectional_balance", "neutral")

        a5 = prior.get("A5NoradrenergicGroup", {})
        ne = float(a5.get("spinal_ne_visceral", 0.20))
        a5_pain_fac = float(a5.get("pain_facilitation_a5", 0.0))

        noci = prior.get("NociceptiveInputProxy", {})
        c_fiber = float(noci.get("c_fiber_input", 0.0))
        a_beta = float(noci.get("a_beta_input", 0.0))

        # 5-HT can be facilitatory or inhibitory depending on balance
        if balance == "facilitatory":
            descending_fac = max(descending_fac, spinal_5ht * 0.5)
            spinal_5ht_eff = spinal_5ht * 0.3
        else:
            spinal_5ht_eff = spinal_5ht

        # --- SG inhibition ---
        sg_target = self._sg_inhibition_target(descending_inh, opioid_tone,
                                                  spinal_5ht_eff, ne, a_beta)
        prev_sg = float(self.state.get("substantia_gelatinosa_inhibition", 0.40))
        new_sg = self._smooth(prev_sg, sg_target)

        # --- Gate state ---
        gate_target = self._gate_state_target(c_fiber, new_sg, descending_fac,
                                                 expected_pain, a5_pain_fac)
        prev_gate = float(self.state.get("gate_state", self.BASELINE_GATE))
        new_gate = self._smooth(prev_gate, gate_target)

        # --- Sensitization streak ---
        prev_streak = int(self.state.get("open_streak", 0))
        if new_gate > 0.55:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 2)
        sensitized = self._detect_sensitization(streak)

        # --- WDR ---
        wdr = self._wdr_target(c_fiber, new_gate, sensitized)
        prev_wdr = float(self.state.get("wdr_drive", 0.0))
        new_wdr = self._smooth(prev_wdr, wdr)

        # --- Ascending nociceptive ---
        ascending = self._ascending_nociceptive(new_gate, new_wdr, expected_pain)

        # --- Aβ suppression ---
        ab_supp = self._a_beta_suppression(a_beta, c_fiber)

        # --- State ---
        state = self._classify_state(new_gate, new_wdr, sensitized, streak)

        recent = list(self.state.get("recent_gates", []))
        recent.append(round(new_gate, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["gate_state"] = round(new_gate, 4)
        self.state["ascending_nociceptive_signal"] = round(ascending, 4)
        self.state["substantia_gelatinosa_inhibition"] = round(new_sg, 4)
        self.state["wdr_drive"] = round(new_wdr, 4)
        self.state["central_sensitization_marker"] = sensitized
        self.state["a_beta_suppression"] = round(ab_supp, 4)
        self.state["spinal_state"] = state
        self.state["open_streak"] = streak
        self.state["recent_gates"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "gate_state": round(new_gate, 4),
            "ascending_nociceptive_signal": round(ascending, 4),
            "substantia_gelatinosa_inhibition": round(new_sg, 4),
            "wdr_drive": round(new_wdr, 4),
            "central_sensitization_marker": sensitized,
            "a_beta_suppression": round(ab_supp, 4),
            "spinal_state": state,
        }
