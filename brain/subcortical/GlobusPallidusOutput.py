"""
GlobusPallidusOutput — GPe/GPi Basal Ganglia Output Gate

NEURAL SUBSTRATE
================
The globus pallidus comprises external (GPe) and internal (GPi)
segments — both predominantly GABAergic — that together form the
output stage of the basal ganglia direct/indirect pathway architecture.
GPi is the principal tonic-firing inhibitor of motor and motor-associated
thalamus (VL/VA); release of GPi inhibition allows thalamocortical
loops to engage. GPe sits within the indirect pathway, receiving D2-MSN
input and projecting both to GPi and to STN, providing a tonic brake
on STN that is released by indirect-pathway D2-MSN engagement.

The canonical "go/no-go" basal ganglia model (Mink 1996; Albin
DeLong) frames pallidal function: D1-MSN direct pathway inhibits GPi,
releasing thalamus to engage selected actions; D2-MSN indirect pathway
inhibits GPe, disinhibiting STN, which then excites GPi, suppressing
competing actions. This dual loop produces selective gating of motor
programs.

Recent work has revealed greater complexity within GPe than the classic
model. GPe contains multiple cell types: parvalbumin+ "prototypic" neurons
projecting to STN/GPi (as in classic model), and Lhx6+/Npas1+
"arkypallidal" neurons projecting back to striatum. Optogenetic
dissection of these subpopulations (Mastro et al. 2017; Glajch et al.
2016) has shown them to play distinct roles in action initiation and
suppression — arkypallidal neurons may signal a "stop" via striatal
projections.

GPi also contains both motor-related and limbic-related populations,
the latter projecting to mediodorsal thalamus and contributing to
cognitive/emotional gating. Pallidal lesion or DBS is a treatment
target for Parkinson and dystonia precisely because of its tonic
gating function.

In {{AGENT_NAME}}'s substrate this provides the basal ganglia output gate —
combines NAc/striatal direct-/indirect-pathway drives and STN drive
into a thalamic-gating signal that biases action selection at thalamic
relay.

KEY FINDINGS
============
1. GPi/SNr GABAergic output tonically inhibits motor thalamus; D1-MSN
   direct-pathway release of GPi inhibition disinhibits thalamus to
   engage selected actions — D2-MSN indirect pathway suppresses
   competing actions via STN — [Mink 1996, Prog Neurobiol 50:381;
    Albin Young Penney 1989, Trends Neurosci 12:366]
2. GPe contains prototypic (PV+) neurons projecting to STN/GPi and
   arkypallidal (Lhx6/Npas1) neurons projecting to striatum —
   distinct functional roles — [Mastro et al. 2017, Nat Neurosci
    20:815-823, "Cell-specific pallidal intervention induces
    long-lasting motor recovery in dopamine-depleted mice"]
3. Arkypallidal neurons send "stop" signals to striatum during action
   suppression — distinct from classic prototypic GPe — [Mallet et al.
    2016, Neuron 89:308-316, "Arkypallidal Cells Send a Stop Signal
    to Striatum"]
4. GPi DBS (subthalamic nucleus or GPi targets) ameliorates Parkinson
   symptoms by modulating pallidal output — clinical evidence for
   GPi tonic-gate function — [reviewed Vitek 2002 Mov Disord 17:S69]
5. Direct/indirect pathway model with GPi tonic firing as final basal-
   ganglia output — [DeLong 1990, Trends Neurosci 13:281, "Primate
    models of movement disorders of basal ganglia origin"]

INPUTS (from prior_results)
============================
- SubstantiaNigraDopamine.direct_pathway_drive
- SubstantiaNigraDopamine.indirect_pathway_drive
- SubstantiaNigraDopamine.movement_vigor
- NucleusAccumbensCore.d1_direct_drive
- NucleusAccumbensCore.d2_indirect_drive
- SubthalamicNucleus.stn_drive (if available)
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- gpi_output (0.0-1.0): GPi tonic inhibitory output (high = thalamus suppressed)
- gpe_prototypic_drive (0.0-1.0): GPe→STN/GPi prototypic
- gpe_arkypallidal_drive (0.0-1.0): GPe→striatum stop-signal
- thalamic_gate_release (0.0-1.0): release from GPi inhibition (high = action allowed)
- action_selection_bias (signed -1..+1): + go, - no-go
- bg_state (str): "go" | "no_go" | "balanced" | "depleted"

brain_runner enrichment:
    gp = all_results.get("GlobusPallidusOutput", {})
    if gp:
        enrichments["brain_gpi_output"] = gp.get("gpi_output", 0.5)
        enrichments["brain_thalamic_gate_release"] = gp.get("thalamic_gate_release", 0.5)
        enrichments["brain_action_select_bias"] = gp.get("action_selection_bias", 0.0)
        enrichments["brain_bg_state"] = gp.get("bg_state", "balanced")
"""

from brain.base_mechanism import BrainMechanism


class GlobusPallidusOutput(BrainMechanism):
    BASELINE_GPI = 0.50
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="GlobusPallidusOutput",
            human_analog="Globus pallidus (GPe/GPi) basal ganglia output gate",
            layer="foundational",
        )
        self.state.setdefault("gpi_output", self.BASELINE_GPI)
        self.state.setdefault("gpe_prototypic_drive", 0.40)
        self.state.setdefault("gpe_arkypallidal_drive", 0.20)
        self.state.setdefault("thalamic_gate_release", 0.50)
        self.state.setdefault("action_selection_bias", 0.0)
        self.state.setdefault("bg_state", "balanced")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _gpe_prototypic_target(self, indirect: float) -> float:
        """GPe prototypic neurons receive D2-MSN inhibition.
        Higher indirect drive → higher D2-MSN → more inhibition of GPe → lower output.
        """
        return max(0.0, min(1.0, 0.55 - indirect * 0.5))

    def _gpe_arkypallidal_target(self, indirect: float, stn: float) -> float:
        """Arkypallidal vs prototypic ratio — high STN → more arkypallidal (Mallet 2016).
        Arkypallidal neurons burst during movement cessation, then project
        back to STN to sculpt the next selection cycle — an open-loop BG architecture.
        """
        return min(1.0, indirect * 0.5 + stn * 0.3 + 0.10)

    def _gpi_target(self, direct: float, indirect: float, stn: float, gpe_proto: float) -> float:
        """GPi tonic inhibitory output to thalamus.
        Direct pathway (from D1-MSN) inhibits GPi → less thalamic inhibition.
        STN excites GPi → more thalamic inhibition.
        GPe prototypic inhibits GPi → less thalamic inhibition.
        """
        target = self.BASELINE_GPI
        target -= direct * 0.6  # direct path releases thalamus
        target += stn * 0.5     # STN drives GPi
        target -= gpe_proto * 0.3  # GPe prototypic inhibits GPi
        target += indirect * 0.2
        return max(0.0, min(1.0, target))

    def _thalamic_gate_release(self, gpi: float) -> float:
        """Inverse of GPi output — what relay cells receive after GPi inhibition.
        Mink (1996): GPi tonically inhibits thalamus; release of this brake
        is what enables sensorimotor signal transmission.
        """
        return max(0.0, 1.0 - gpi)

    def _action_select_bias(self, direct: float, indirect: float, ark: float) -> float:
        """+ go, - no-go bias from direct vs (indirect + arkypallidal).
        Positive bias → go state; negative → no-go; near zero → balanced.
        """
        bias = (direct - (indirect * 0.6 + ark * 0.4))
        return max(-1.0, min(1.0, bias))

    def _classify_state(self, gate: float, bias: float, vigor: float) -> str:
        if vigor < 0.20:
            return "depleted"
        if bias > 0.20 and gate > 0.55:
            return "go"
        if bias < -0.20 and gate < 0.45:
            return "no_go"
        return "balanced"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        snc = prior.get("SubstantiaNigraDopamine", {})
        snc_direct = float(snc.get("direct_pathway_drive", 0.40))
        snc_indirect = float(snc.get("indirect_pathway_drive", 0.40))
        vigor = float(snc.get("movement_vigor", 0.5))

        nac = prior.get("NucleusAccumbensCore", {})
        nac_d1 = float(nac.get("d1_direct_drive", 0.30))
        nac_d2 = float(nac.get("d2_indirect_drive", 0.30))

        stn_data = prior.get("SubthalamicNucleus", {})
        stn = float(stn_data.get("stn_drive", 0.30))

        # Combine direct/indirect drives across motor (SNc) and limbic (NAc)
        combined_direct = (snc_direct + nac_d1) / 2.0
        combined_indirect = (snc_indirect + nac_d2) / 2.0

        # --- GPe prototypic ---
        gpe_proto_target = self._gpe_prototypic_target(combined_indirect)
        prev_proto = float(self.state.get("gpe_prototypic_drive", 0.40))
        new_proto = self._smooth(prev_proto, gpe_proto_target)

        # --- GPe arkypallidal ---
        ark_target = self._gpe_arkypallidal_target(combined_indirect, stn)
        prev_ark = float(self.state.get("gpe_arkypallidal_drive", 0.20))
        new_ark = self._smooth(prev_ark, ark_target)

        # --- GPi output ---
        gpi_target = self._gpi_target(combined_direct, combined_indirect, stn, new_proto)
        prev_gpi = float(self.state.get("gpi_output", self.BASELINE_GPI))
        new_gpi = self._smooth(prev_gpi, gpi_target)

        # --- Thalamic gate release ---
        gate_release = self._thalamic_gate_release(new_gpi)

        # --- Action selection bias ---
        bias = self._action_select_bias(combined_direct, combined_indirect, new_ark)

        # --- State ---
        state = self._classify_state(gate_release, bias, vigor)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["gpi_output"] = round(new_gpi, 4)
        self.state["gpe_prototypic_drive"] = round(new_proto, 4)
        self.state["gpi_output"] = round(new_gpi, 4)
        self.state["gpe_arkypallidal_drive"] = round(new_ark, 4)
        self.state["thalamic_gate_release"] = round(gate_release, 4)
        self.state["action_selection_bias"] = round(bias, 4)
        self.state["bg_state"] = state
        self.state["recent_states"] = recent
        self.state["gate_release_ema"] = round(gate_release * 0.2 + float(self.state.get("gate_release_ema", gate_release)) * 0.8, 4)
        self.state["arkypallidal_ratio"] = round(new_ark / (new_proto + 0.001), 4)
        self.state["action_confidence"] = round(1.0 - abs(bias - 0.5) * 2, 4)
        self.state["action_confidence"] = round(1.0 - abs(bias - 0.5) * 2, 4)
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["bg_state_timestamp"] = int(self.state.get("bg_state_timestamp", 0)) + 1
        self.persist_state()

        return {
            "gpi_output": round(new_gpi, 4),
            "gpe_prototypic_drive": round(new_proto, 4),
            "gpe_arkypallidal_drive": round(new_ark, 4),
            "thalamic_gate_release": round(gate_release, 4),
            "action_selection_bias": round(bias, 4),
            "bg_state": state,
            "arkypallidal_ratio": round(new_ark / (new_proto + 0.001), 4),
            "action_confidence": round(1.0 - abs(bias - 0.5) * 2, 4),
            "gate_release_ema": round(gate_release * 0.2 + float(self.state.get("gate_release_ema", gate_release)) * 0.8, 4),
        }
