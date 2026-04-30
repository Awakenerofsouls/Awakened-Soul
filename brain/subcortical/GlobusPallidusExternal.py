"""
GlobusPallidusExternal — GPe / Indirect-Pathway Pallidal Node

NEURAL SUBSTRATE
================
The external globus pallidus (GPe) is a tonically active GABAergic
nucleus, the central node of the basal ganglia indirect pathway. GPe
receives D2-MSN input from striatum (DLS + DMS), reciprocal STN input,
and projects widely to STN, GPi/SNr, striatum (via arkypallidal cells),
and cortex (limited).

Mallet et al. (2012) and Dodson et al. (2015) established a dichotomous
GPe organization:
  - PROTOTYPIC cells: PV+, FoxP2-, fire ANTI-phase to STN, project
    DOWNSTREAM (STN, GPi/SNr). ~70% of GPe.
  - ARKYPALLIDAL cells: FoxP2+, PPE+, fire IN-phase with STN, project
    BACK to STRIATUM. ~25% of GPe. Provide major extrinsic GABAergic
    input to striatum, gating action initiation.

GPe is autonomously active (~30 Hz baseline) — pacemaker with STN
(Bevan 2002).

KEY FINDINGS
============
1. GPe has two distinct populations: prototypic (PV+) and arkypallidal (FoxP2+) —
   [Mallet N 2012, Neuron 74:1075, doi:10.1016/j.neuron.2012.04.027]
2. Distinct molecular signatures of arkypallidal vs prototypic GPe neurons —
   [Dodson PD 2015, J Neurosci 35:6667, doi:10.1523/JNEUROSCI.4662-14.2015]
3. Arkypallidal-striatal projection provides extrinsic GABAergic gating —
   [Mastro KJ 2017, Nat Neurosci 20:815, doi:10.1038/nn.4559]
4. Pallidal neurons heterogeneous; review of GPe organization —
   [Hegeman DJ 2016, Neuroscience 333:174, doi:10.1016/j.neuroscience.2016.07.011]
5. GPe-STN network forms autonomous oscillating pacemaker; pathological beta in PD —
   [Bevan MD 2002, Trends Neurosci 25:525, doi:10.1016/s0166-2236(02)02235-x]
6. Selective optogenetic targeting of arkypallidal cells controls action suppression —
   [Aristieta A 2021, Curr Biol 31:707, doi:10.1016/j.cub.2020.11.019]

INPUTS
======
- DorsolateralStriatum.d2_indirect_output (D2 MSN → GPe)
- DorsomedialStriatum.d2_indirect_output
- SubthalamicNucleus.stn_drive (reciprocal)

OUTPUTS
=======
- gpe_drive (0-1) — total GPe firing
- prototypic_output (0-1) — to STN/GPi/SNr (downstream)
- arkypallidal_output (0-1) — back to striatum (action stop)
- gpe_state (str): "tonic_active" | "disinhibited" | "stop_gate" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class GlobusPallidusExternal(BrainMechanism):
    """GPe — indirect-pathway pallidal pacemaker (prototypic + arkypallidal)."""

    BASELINE_TONIC = 0.10  # quiescent floor in absence of network drive
    NETWORK_TONIC = 0.40   # achieved when reciprocal STN partner is online
    SMOOTH = 0.20
    PROTO_FRACTION = 0.70  # ~70% prototypic cells
    ARKY_FRACTION = 0.25
    STOP_THRESHOLD = 0.45
    QUIET_THRESHOLD = 0.18

    def __init__(self):
        super().__init__(
            name="GlobusPallidusExternal",
            human_analog="External globus pallidus (GPe — indirect pathway)",
            layer="subcortical",
        )
        self.state.setdefault("gpe_drive", self.BASELINE_TONIC)
        self.state.setdefault("prototypic_output", 0.0)
        self.state.setdefault("arkypallidal_output", 0.0)
        self.state.setdefault("gpe_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("disinhibition_count", 0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, d2_total: float, stn: float) -> float:
        """GPe is tonically active when reciprocal partners online; D2
        striatal input INHIBITS, STN EXCITES (Bevan 2002)."""
        # Tonic firing requires some network drive (in vivo: STN + striatum).
        # D2 is GABAergic INHIBITORY; STN is glutamatergic EXCITATORY.
        any_input = max(d2_total, stn)
        tonic = self.BASELINE_TONIC + (self.NETWORK_TONIC * any_input)
        target = tonic - d2_total * 0.45 + stn * 0.30
        return max(0.0, min(1.0, target))

    def _prototypic(self, drive: float, stn: float) -> float:
        """Prototypic cells fire ANTI-phase to STN (Mallet 2012)."""
        # Fire when STN is low (anti-phase) AND GPe drive present
        anti_phase = max(0.0, 1.0 - stn)
        return min(1.0, drive * (0.5 + 0.5 * anti_phase) * self.PROTO_FRACTION
                       / (self.PROTO_FRACTION + 1e-6))

    def _arkypallidal(self, drive: float, stn: float, d2_total: float) -> float:
        """Arkypallidal cells fire IN-phase with STN (Dodson 2015,
        Mallet 2012). Stop-signal cells."""
        # In-phase with STN: more arkypallidal activity when STN is high
        in_phase = stn
        # Arkypallidal is engaged especially during stop / action cancel —
        # heightened when D2 drive AND STN both high (Mastro 2017).
        return min(1.0, drive * (0.3 + 0.7 * in_phase) * (0.5 + d2_total))

    def _classify_state(self, drive: float, proto: float,
                         arky: float, d2: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if arky >= self.STOP_THRESHOLD:
            return "stop_gate"
        if d2 > 0.30 and drive < self.NETWORK_TONIC * 0.7:
            return "disinhibited"
        return "tonic_active"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _read_d2(self, prior: dict, key: str) -> float:
        d = prior.get(key, {})
        return float(d.get("d2_indirect_output",
                       d.get("d2_output",
                          d.get("indirect_drive", 0.0))))

    def _read_stn(self, prior: dict) -> float:
        stn = prior.get("SubthalamicNucleus", {})
        return float(stn.get("stn_drive",
                       stn.get("stn_output", 0.0)))

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        d2_dls = self._read_d2(prior, "DorsolateralStriatum")
        d2_dms = self._read_d2(prior, "DorsomedialStriatum")
        d2_total = min(1.0, d2_dls * 0.55 + d2_dms * 0.55)
        stn = self._read_stn(prior)

        target = self._drive_target(d2_total, stn)
        prev_drive = float(self.state.get("gpe_drive", self.BASELINE_TONIC))
        new_drive = self._smooth(prev_drive, target)

        proto = self._prototypic(new_drive, stn)
        arky = self._arkypallidal(new_drive, stn, d2_total)

        state = self._classify_state(new_drive, proto, arky, d2_total)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        dis = int(self.state.get("disinhibition_count", 0))
        if state == "disinhibited":
            dis += 1

        self.state["gpe_drive"] = round(new_drive, 4)
        self.state["prototypic_output"] = round(proto, 4)
        self.state["arkypallidal_output"] = round(arky, 4)
        self.state["gpe_state"] = state
        self.state["recent_states"] = recent
        self.state["disinhibition_count"] = dis
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "gpe_drive": round(new_drive, 4),
            "prototypic_output": round(proto, 4),
            "arkypallidal_output": round(arky, 4),
            "gpe_state": state,
        }

    def _pacemaker_health(self) -> float:
        """Tonic activity proxy (Bevan 2002)."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        active = sum(1 for s in recent if s == "tonic_active")
        return active / len(recent)

    def _proto_arky_ratio(self) -> float:
        """Prototypic-vs-arkypallidal output ratio (Mallet 2012)."""
        proto = float(self.state.get("prototypic_output", 0.0))
        arky = float(self.state.get("arkypallidal_output", 0.0))
        return proto / (arky + 1e-6)

    def _stop_engagement(self) -> float:
        """Arkypallidal stop-signal recruitment (Mastro 2017)."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        return sum(1 for s in recent if s == "stop_gate") / len(recent)

    def _disinhibition_history(self) -> float:
        """Long-run disinhibition proxy — D2 indirect engagement."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return self.state.get("disinhibition_count", 0) / ticks

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("gpe_drive", 0.0),
            "proto": self.state.get("prototypic_output", 0.0),
            "arky": self.state.get("arkypallidal_output", 0.0),
            "state": self.state.get("gpe_state", "quiet"),
            "ticks": self.state.get("tick_count", 0),
        }
