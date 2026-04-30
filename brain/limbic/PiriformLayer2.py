"""
PiriformLayer2 — Pir-II / Piriform Cortex Layer 2 Pyramidal Cells

NEURAL SUBSTRATE
================
Layer 2 of piriform cortex (Pir-II) contains the principal pyramidal
neurons of olfactory cortex — distributed across two sublayers
(superficial 2a, deep 2b). Pir-II pyramids receive lateral olfactory
tract (LOT) input from olfactory bulb mitral cells and integrate odor
features distributively. Pir-II is the canonical substrate of olfactory
"object recognition" — odor mixtures are encoded as combinatorial
patterns across Pir-II pyramidal ensembles.

KEY FINDINGS
============
1. Piriform layer 2 pyramidal cells receive direct LOT input from
   olfactory bulb mitral cells; principal targets of OB output —
   [Haberly 1985, Chem Senses 10:219, doi:10.1093/chemse/10.2.219]
2. Pir-II ensembles encode odor identity via distributed combinatorial
   patterns; not arranged in topographic maps —
   [Stettler 2009, Neuron 63:854, doi:10.1016/j.neuron.2009.09.005]
3. Pir-II superficial (2a) and deep (2b) sublayers differ in
   excitability + projection targets —
   [Suzuki 2011, J Neurosci 31:3033, doi:10.1523/JNEUROSCI.5125-10.2011]
4. Pir-II encoding of odor mixtures supports figure-ground odor
   segmentation; cocktail-party effect for olfaction —
   [Howard 2009, Curr Biol 19:1124, doi:10.1016/j.cub.2009.05.029]
5. Pir-II sparse pyramidal-cell coding scheme is essential for
   distinguishing similar odors —
   [Poo 2009, Neuron 62:850, doi:10.1016/j.neuron.2009.05.022]
"""

from brain.base_mechanism import BrainMechanism


class PiriformLayer2(BrainMechanism):
    """Pir-II — primary piriform pyramidal cell layer."""

    BASELINE = 0.10
    SMOOTH = 0.20
    OBJECT_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="PiriformLayer2",
            human_analog="Piriform cortex layer 2",
            layer="limbic",
        )
        self.state.setdefault("pir2_drive", self.BASELINE)
        self.state.setdefault("odor_object_signal", 0.0)
        self.state.setdefault("ensemble_sparseness", 0.5)
        self.state.setdefault("layer3_drive_signal", 0.0)
        self.state.setdefault("en_drive_signal", 0.0)
        self.state.setdefault("pir2_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ob: float, lot: float, ach: float) -> float:
        """Pir-II drive (Haberly 1985)."""
        # LOT (=ob_drive proxy) is the primary input
        target = (self.BASELINE
                  + ob * 0.45
                  + lot * 0.25
                  + ach * 0.15)
        return min(1.0, target)

    def _odor_object(self, drive: float, sparseness: float) -> float:
        """Distributed odor object representation (Stettler 2009; Howard 2009)."""
        if drive < 0.15:
            return 0.0
        # Higher sparseness = better object discrimination
        return min(1.0, drive * (0.5 + sparseness * 0.5))

    def _sparseness(self, drive: float, ach: float) -> float:
        """Population sparseness modulated by ACh (Poo 2009)."""
        # ACh increases sparseness (sharpens code)
        base_sparse = 1.0 - drive * 0.4  # higher drive = denser code
        return min(1.0, max(0.0, base_sparse + ach * 0.3))

    def _layer3_drive(self, drive: float, object_signal: float) -> float:
        """Pir-II → Pir-III feedforward (Suzuki 2011)."""
        return min(1.0, drive * 0.55 + object_signal * 0.35)

    def _en_drive(self, drive: float) -> float:
        """Pir-II → endopiriform nucleus (deep target)."""
        return min(1.0, drive * 0.7)

    def _classify_state(self, drive: float, object_signal: float) -> str:
        if drive < 0.20:
            return "quiet"
        if object_signal > self.OBJECT_THRESHOLD:
            return "object_recognized"
        return "active_olfactory"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ob_data = prior.get("OlfactoryBulb", {})
        ob = float(ob_data.get("ob_drive",
                          ob_data.get("ob_output", 0.0)))

        # LOT signal proxy: take from AnteriorOlfactoryNucleus or OB
        aon_data = prior.get("AnteriorOlfactoryNucleus", {})
        lot = float(aon_data.get("aon_drive", 0.0))

        ach_data = prior.get("NucleusOfDiagonalBandHorizontal", {})
        if not ach_data:
            ach_data = prior.get("DiagonalBandBroca", {})
        ach = float(ach_data.get("piriform_ach_signal",
                          ach_data.get("ach_modulation", 0.0)))

        target = self._drive_target(ob, lot, ach)
        prev_drive = float(self.state.get("pir2_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        sparseness = self._sparseness(new_drive, ach)
        object_sig = self._odor_object(new_drive, sparseness)
        l3_drive = self._layer3_drive(new_drive, object_sig)
        en_drive = self._en_drive(new_drive)

        state = self._classify_state(new_drive, object_sig)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pir2_drive"] = round(new_drive, 4)
        self.state["odor_object_signal"] = round(object_sig, 4)
        self.state["ensemble_sparseness"] = round(sparseness, 4)
        self.state["layer3_drive_signal"] = round(l3_drive, 4)
        self.state["en_drive_signal"] = round(en_drive, 4)
        self.state["pir2_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pir2_drive": round(new_drive, 4),
            "pir_drive": round(new_drive, 4),  # alias
            "odor_object_signal": round(object_sig, 4),
            "ensemble_sparseness": round(sparseness, 4),
            "layer3_drive_signal": round(l3_drive, 4),
            "en_drive_signal": round(en_drive, 4),
            "pir2_state": state,
        }

    def _discrimination_capacity(self) -> float:
        """Capacity to distinguish similar odors (Poo 2009)."""
        return float(self.state.get("ensemble_sparseness", 0.5))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pir2_drive", 0.0),
            "object": self.state.get("odor_object_signal", 0.0),
            "sparseness": self.state.get("ensemble_sparseness", 0.5),
            "state": self.state.get("pir2_state", "quiet"),
        }
