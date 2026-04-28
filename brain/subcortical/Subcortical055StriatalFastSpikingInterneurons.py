"""
Subcortical055StriatalFastSpikingInterneurons.py — Wire 55: FSI

Neural substrate: Fast-spiking interneurons (FSI) in striatum.

Fast-spiking interneurons are a key local circuit element within the
striatum. They are GABAergic, receive input from cortical pyramidal
cells, and provide powerful feedforward inhibition onto striatal
projection neurons (MSNs). Koos & Tepper 1999 identified them as the
"parvalbumin-positive basket cells" of the striatum — distinct from
the cholinergic tonically active neurons (TANs).

Koos 2004 established FSI's role in shaping the temporal dynamics of
striatal output: they fire fast spikes (≤ 10 ms) in response to cortical
input, delivering rapid inhibition that sculpts which MSNs can fire.
Gittis 2010 showed FSI in Parkinson's are overactive, contributing to
the pathological firing patterns observed in PD.

KEY RESEARCH FINDINGS:
1. Anatomical identity. Koos & Tepper 1999: FSIs are PV+ (parvalbumin
   positive), axo-axonic or basket-type synapses onto MSN soma and
   proximal dendrites. They are distinct from: (a) cholinergic TANs
   (Chat+), (b) NPY/calbindin-negative low-threshold spiking interneurons.
   FSIs represent ~1% of striatal neurons in rodents; higher in primates.

2. Feedforward inhibition. FSIs receive direct excitatory input from
   cortical pyramidal cells (cortico-striatal glutamatergic). Their
   firing is feedforward: cortical input → FSI → MSN inhibition. This
   is a classic feedforward inhibitory circuit — identical in concept
   to cerebellar molecular layer interneurons (basket/stellate cells).

3. Gamma oscillations and synchrony. Fisahn 1998 (cortex) and
   Gittis 2010 (striatum): FSIs generate gamma-frequency (30-80 Hz)
   network oscillations in response to excitatory drive. In striatum,
   FSI synchrony coordinates MSN firing in gamma — important for
   temporal precision in action selection. Beta-band synchrony in
   PD (>13-30 Hz) is partly driven by FSI network dysfunction.

4. Gain control. FSIs implement a "division of labor" at the striatal
   microcircuit level: they prevent non-selected MSNs from firing,
   effectively sharpening the contrast between selected and non-selected
   motor programs. This is the "gain control" function. Bracci 2003:
   "Fast-spiking interneurons can dynamically control the gain of
   striatal output."

5. Pathological overactivity in PD. Gittis 2011: "FSIs are
   hyperactive in models of Parkinson's disease." In the 6-OHDA rat
   model, FSIs fire at higher rates and with excessive synchrony,
   contributing to the suppression of MSN firing and the beta
   synchrony seen in PD. This is a novel therapeutic target.

6. Feedforward inhibition timing. FSI spikes arrive at MSNs within
   1-3 ms of cortical EPSPs — extremely fast. This rapid inhibition
   can prevent MSN firing within the same cortical oscillation cycle —
   critical for timing-based selection in basal ganglia circuits.

7. Inhibitory surround. FSIs form lateral inhibitory networks among
   themselves — inter-FSI inhibition creates a lateral inhibition
   effect: an activated FSI suppresses neighboring FSIs, allowing
   more precise spatial focusing of the inhibition.

8. Computational modeling. Humphries 2009: FSI-mediated feedforward
   inhibition improves the signal-to-noise ratio of striatal selection
   by ~30% compared to a model without FSIs. This is a significant
   gain for action selection.

OUTPUTS:
  FSI_activity: float 0-1 — current FSI activation level
  synchrony_boost: float 0-1 — degree of FSI network synchrony
  feedforward_inhibition_strength: float 0-1 — effective inhibition onto MSNs

INPUTS:
  cortical_input: excitatory drive from cortex
  MSN_activity: feedback from projection neurons (recurrent)
  dopaminergic_state: DA level (modulates FSI excitability)
  PD_pathology: Parkinsonian factor (overactivates FSI)

CITATIONS:
    PMC2562631 — Tepper JM, Wilson CJ, Koós T (2008). Feedforward and Feedback
        Inhibition in Neostriatal GABAergic Spiny Neurons. Front Cell Neurosci.
    PMC3849346 — Rossignol E, Kruglikov I, van den Maagdenberg AM et al. (2013).
        CaV2.1 Ablation in Cortical Interneurons Selectively Impairs Fast-Spiking
        Basket Cells. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class StriatalFastSpikingInterneurons(BrainMechanism):
    """
    Striatal fast-spiking interneurons (PV+ basket cells).

    Provide feedforward inhibition onto MSNs, shape temporal precision
    of action selection, generate gamma oscillations, and implement
    gain control across the striatal microcircuit. Overactive in PD.
    """

    FSI_FIRING_RATE = 0.35
    FEEDFORWARD_GAIN = 1.20  # strong feedforward inhibition
    GAMMA_FREQ = 40.0  # Hz — FSI-driven gamma
    SYNC_DECAY = 0.04
    RECURRENT_INHIBITION = 0.20  # FSI-to-FSI lateral inhibition

    def __init__(self):
        super().__init__(
            name="StriatalFastSpikingInterneurons",
            human_analog="Striatal fast-spiking interneurons (PV+, basket cells)",
            layer="subcortical",
        )
        self.state.setdefault("FSI_activity", 0.0)
        self.state.setdefault("synchrony_boost", 0.3)
        self.state.setdefault("feedforward_inhibition_strength", 0.0)
        self.state.setdefault("gamma_phase", 0.0)
        self.state.setdefault("lateral_inhibition_strength", 0.0)
        self.state.setdefault("PD_overactivity", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        cortical_input = input_data.get("cortical_input", 0.4)
        MSN_activity = input_data.get("MSN_activity", 0.3)
        dopaminergic_state = input_data.get("dopaminergic_state", 0.5)
        PD_pathology = input_data.get("PD_pathology", 0.0)
        FSI_inhibition_input = input_data.get("FSI_inhibition_input", 0.1)

        # --- FSI activation ---
        # FSIs fire in response to cortical excitation — feedforward drive
        # D2-mediated dopaminergic modulation reduces FSI excitability
        # (DA acts presynaptically on cortical terminals to FSIs)
        DA_modulation = (0.5 - dopaminergic_state) * 0.15  # more DA = less cortical drive to FSI
        cortical_gain = 1.0 + DA_modulation

        # Feedforward activation
        feedforward_drive = cortical_input * cortical_gain * 0.6

        # Recurrent/lateral inhibition from neighboring FSIs
        lateral_inhib = FSI_inhibition_input * self.RECURRENT_INHIBITION
        feedforward_drive -= lateral_inhib

        # PD pathology: overactive in parkinsonian states (Gittis 2011)
        PD_boost = PD_pathology * 0.3
        raw_FSI = self.FSI_FIRING_RATE + feedforward_drive + PD_boost
        FSI_activity = max(0.0, min(1.0, raw_FSI))

        # --- Feedforward inhibition strength ---
        # FSIs powerfully inhibit MSNs — this is the primary output
        feedforward_inhibition_strength = min(1.0, FSI_activity * self.FEEDFORWARD_GAIN)
        # MSN activity provides feedback — reduces inhibition when MSNs are already firing
        MSN_feedback = MSN_activity * 0.1 * (1.0 - feedforward_inhibition_strength)
        effective_inhibition = feedforward_inhibition_strength - MSN_feedback
        self.state["feedforward_inhibition_strength"] = max(0.0, min(1.0, effective_inhibition))

        # --- Gamma oscillations ---
        # FSIs generate gamma (30-80 Hz) in the striatal network
        gamma_period = 60.0 / self.GAMMA_FREQ  # ms per cycle
        gamma_increment = (self.GAMMA_FREQ / 60.0) * 360.0  # degrees per tick at 60fps
        new_gamma_phase = (self.state["gamma_phase"] + gamma_increment) % 360.0
        self.state["gamma_phase"] = new_gamma_phase

        gamma_wave = 0.5 * (1.0 + (1.0 if new_gamma_phase < 180 else -1.0))
        # Gamma power increases with cortical drive
        gamma_power = gamma_wave * FSI_activity * 0.8 + 0.1
        self.state["gamma_power"] = max(0.0, min(1.0, gamma_power))

        # --- Synchrony boost ---
        # FSIs synchronize in gamma when receiving common drive
        # Synchrony in the FSI network enables coherent inhibition of MSNs
        common_drive = cortical_input * 0.5 + dopaminergic_state * 0.3
        sync_delta = 0.02 * common_drive * FSI_activity
        if PD_pathology > 0.3:
            sync_delta += 0.03 * PD_pathology  # PD increases synchrony

        new_sync = self.state["synchrony_boost"] + sync_delta
        new_sync -= self.SYNC_DECAY  # synchrony decays without reinforcement
        self.state["synchrony_boost"] = max(0.0, min(1.0, new_sync))
        synchrony_boost = self.state["synchrony_boost"]

        # --- Lateral inhibition ---
        # Inter-FSI lateral inhibition sharpens spatial focus
        lateral = self.RECURRENT_INHIBITION * FSI_activity * (1.0 - synchrony_boost)
        self.state["lateral_inhibition_strength"] = max(0.0, min(1.0, lateral))

        self.state["FSI_activity"] = FSI_activity
        self.state["PD_overactivity"] = PD_pathology
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "FSI_activity": round(FSI_activity, 4),
            "synchrony_boost": round(synchrony_boost, 4),
            "feedforward_inhibition_strength": round(effective_inhibition, 4),
            "gamma_phase_degrees": round(new_gamma_phase, 2),
            "gamma_power": round(self.state.get("gamma_power", 0.0), 4),
            "lateral_inhibition_strength": round(self.state["lateral_inhibition_strength"], 4),
        }