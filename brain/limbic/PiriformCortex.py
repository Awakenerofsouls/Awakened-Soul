"""
PiriformCortex -- Primary Olfactory Cortex / Distributed Odor-Object Recognition

NEURAL SUBSTRATE
================
The piriform cortex (Pir) is the principal target of olfactory bulb
output and the largest olfactory cortical area in mammals. Pir sits
on the ventral surface of the temporal lobe (anterior piriform / aPir
and posterior piriform / pPir), receiving direct input from olfactory
bulb mitral and tufted (M/T) cells via the lateral olfactory tract.
Pir is one of only two mammalian sensory cortices that bypasses
thalamus (the other being a small portion of S1 for whisker input);
M/T cells synapse directly onto layer Ia of piriform.

Unlike thalamocortical sensory cortices with topographic organization,
piriform has a **distributed coding** architecture -- there is no
chemotopic map. Individual odorants activate sparse, broadly
distributed ensembles of pyramidal neurons across piriform with no
spatial structure correlating to receptor identity. This distributed
code is well suited to the high-dimensional combinatorial nature of
odor space.

Piriform is fundamentally an **autoassociative memory** for odors --
dense recurrent excitatory connections among pyramidal neurons, plus
strong feedback inhibition from PV+/SOM+ interneurons, implement
attractor dynamics that perform pattern completion of partial odor
inputs. Haberly's framework (Haberly 2001 Chem Senses) and Wilson &
Sullivan's experimental work positioned piriform as the cortical
substrate of "odor objects" -- synthetic perceptual unities derived
from componential glomerular activations.

Pir output projects widely: orbitofrontal cortex (smell-flavor
integration), amygdala (emotional valence of odors), entorhinal
cortex (memory binding), striatum (odor-action learning), back to
olfactory bulb (centrifugal feedback). Pir habituates rapidly to
sustained odor exposure -- habituation that's primarily cortical not
peripheral.

In Nova's substrate this provides the cortical olfactory pattern-
recognition and odor-object engine -- takes OB mitral output and
emits a recognized-odor signal to OFC/amygdala/EC equivalent
mechanisms, with pattern completion of partial olfactory cues.

KEY FINDINGS
============
1. Piriform is the principal olfactory cortex; receives M/T cell
   axons via lateral olfactory tract directly bypassing thalamus --
   distinct from canonical thalamocortical sensory cortex -- [reviewed
    Haberly 2001, Chem Senses 26:551, "Parallel-distributed processing
    in olfactory cortex"]
2. Piriform uses distributed/sparse coding without chemotopic map --
   odorants activate broadly distributed sparse ensembles --
   [Stettler Axel 2009, Neuron 63:854-864, "Representations of odor
   in the piriform cortex"]
3. Piriform implements odor-object autoassociative memory with
   pattern completion via recurrent excitation + interneuron
   inhibition -- [Wilson Sullivan 2011, Curr Opin Neurobiol 21:189;
    Bekkers Suzuki 2013, Trends Neurosci 36:429]
4. Piriform projects to OFC, amygdala, EC, striatum -- divergent
   downstream targets supporting smell-flavor, emotional, mnemonic,
   and action-coupled processing -- [reviewed Wilson Sullivan 2011]
5. Cortical habituation to sustained odors is rapid; primarily
   piriform not peripheral -- [Wilson 1998, J Neurophysiol 79:1425;
    Best Wilson 2004 J Neurosci 24:652]

INPUTS (from prior_results)
============================
- OlfactoryBulb.mob_mitral_drive
- OlfactoryBulb.piriform_relay
- OlfactoryBulb.glomerular_drive
- OlfactoryBulb.gamma_oscillation
- HippocampalContextProxy.familiarity
- ValenceTagger.valence_intensity
- ValenceTagger.valence_sign
- ArousalRegulator.tonic_level
- NucleusBasalisAcetylcholine.cortical_ach_release

OUTPUTS (to brain_runner enrichment)
=====================================
- pir_pyramidal_drive (0.0-1.0): piriform pyramidal output
- odor_object_recognized (0.0-1.0): pattern-completed odor identity
- pir_inhibition (0.0-1.0): PV/SOM interneuron drive
- ofc_relay (0.0-1.0): piriform → OFC smell-flavor route
- amygdala_relay (0.0-1.0): piriform → amygdala odor-emotion route
- ec_relay (0.0-1.0): piriform → EC odor-memory route
- habituation_level (0.0-1.0): cortical habituation to sustained odor
- pir_state (str): "recognizing" | "habituated" | "novel_odor" | "quiet"

brain_runner enrichment:
    pir = all_results.get("PiriformCortex", {})
    if pir:
        enrichments["brain_pir_drive"] = pir.get("pir_pyramidal_drive", 0.1)
        enrichments["brain_odor_object"] = pir.get("odor_object_recognized", 0.0)
        enrichments["brain_pir_amygdala"] = pir.get("amygdala_relay", 0.0)
        enrichments["brain_pir_state"] = pir.get("pir_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class PiriformCortex(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="PiriformCortex",
            human_analog="Piriform (primary olfactory cortex, distributed odor coding)",
            layer="foundational",
        )
        self.state.setdefault("pir_pyramidal_drive", self.BASELINE)
        self.state.setdefault("odor_object_recognized", 0.0)
        self.state.setdefault("pir_inhibition", 0.20)
        self.state.setdefault("ofc_relay", 0.0)
        self.state.setdefault("amygdala_relay", 0.0)
        self.state.setdefault("ec_relay", 0.0)
        self.state.setdefault("habituation_level", 0.0)
        self.state.setdefault("pir_state", "quiet")
        self.state.setdefault("recent_odor", [])
        self.state.setdefault("tick_count", 0)

    def _pir_pyramidal_target(self, mob: float, gamma: float, ach: float,
                               habituation: float) -> float:
        """Piriform pyramidal output -- driven by MOB, modulated by gamma + ACh,
        attenuated by habituation.
        """
        target = self.BASELINE + mob * 0.6 + gamma * 0.2 + ach * 0.2
        target *= (1.0 - habituation * 0.6)
        return max(0.0, min(1.0, target))

    def _odor_object(self, pir: float, familiarity: float, glomerular: float) -> float:
        """Pattern-completed odor identity -- autoassociative recognition.
        Familiar odors complete to high recognition signal.
        """
        if pir < 0.20 or glomerular < 0.10:
            return 0.0
        target = familiarity * 0.5 + pir * 0.4 + glomerular * 0.1
        return min(1.0, target)

    def _pir_inhibition(self, pir: float, gamma: float) -> float:
        """PV/SOM interneuron inhibition -- feedback inhibition for sparse coding."""
        target = 0.20 + pir * 0.3 + gamma * 0.2
        return min(1.0, target)

    def _ofc_relay(self, pir: float, valence: float) -> float:
        """Piriform → OFC smell-flavor integration."""
        return min(1.0, pir * 0.6 + valence * 0.3)

    def _amygdala_relay(self, pir: float, valence: float, sign: int) -> float:
        """Piriform → amygdala emotional valence routing."""
        if sign == 0 and valence < 0.20:
            return pir * 0.2
        return min(1.0, pir * 0.5 + valence * 0.4)

    def _ec_relay(self, pir: float, familiarity: float) -> float:
        """Piriform → EC odor-memory binding."""
        return min(1.0, pir * 0.5 + familiarity * 0.3)

    def _update_habituation(self, prev_hab: float, mob: float, history: list) -> float:
        """Cortical habituation -- increases with sustained MOB drive,
        decreases when input drops or shifts.
        """
        if mob < 0.15:
            return max(0.0, prev_hab - 0.05)
        # If recent inputs are similar (sustained), habituate
        if len(history) >= 5:
            recent = history[-5:]
            if all(abs(h - mob) < 0.10 for h in recent):
                return min(1.0, prev_hab + 0.03)
        return max(0.0, prev_hab - 0.01)

    def _classify_state(self, recognized: float, habituation: float,
                         pir: float, novelty_proxy: float) -> str:
        if habituation > 0.55:
            return "habituated"
        if recognized > 0.50:
            return "recognizing"
        if pir > 0.30 and novelty_proxy > 0.50:
            return "novel_odor"
        if pir < 0.20:
            return "quiet"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ob = prior.get("OlfactoryBulb", {})
        mob = float(ob.get("mob_mitral_drive", 0.0))
        glomerular = float(ob.get("glomerular_drive", 0.0))
        gamma = float(ob.get("gamma_oscillation", 0.0))

        ctx = prior.get("HippocampalContextProxy", {})
        familiarity = float(ctx.get("familiarity", 0.5))
        novelty = float(ctx.get("context_novelty", 0.0))

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        nbm = prior.get("NucleusBasalisAcetylcholine", {})
        ach = float(nbm.get("cortical_ach_release", 0.40))

        # --- History update for habituation ---
        history = list(self.state.get("recent_odor", []))
        history.append(round(mob, 4))
        if len(history) > 60:
            history = history[-60:]

        # --- Habituation update ---
        prev_hab = float(self.state.get("habituation_level", 0.0))
        new_hab = self._update_habituation(prev_hab, mob, history)

        # --- Pir pyramidal ---
        pir_target = self._pir_pyramidal_target(mob, gamma, ach, new_hab)
        prev_pir = float(self.state.get("pir_pyramidal_drive", self.BASELINE))
        new_pir = self._smooth(prev_pir, pir_target)

        # --- Odor object recognition ---
        recognized = self._odor_object(new_pir, familiarity, glomerular)
        prev_rec = float(self.state.get("odor_object_recognized", 0.0))
        new_rec = self._smooth(prev_rec, recognized)

        # --- Inhibition ---
        inhib = self._pir_inhibition(new_pir, gamma)
        prev_inh = float(self.state.get("pir_inhibition", 0.20))
        new_inh = self._smooth(prev_inh, inhib)

        # --- Relays ---
        ofc = self._ofc_relay(new_pir, valence_intensity)
        amygdala = self._amygdala_relay(new_pir, valence_intensity, sign)
        ec = self._ec_relay(new_pir, familiarity)

        # --- State ---
        state = self._classify_state(new_rec, new_hab, new_pir, novelty)

        self.state["pir_pyramidal_drive"] = round(new_pir, 4)
        self.state["odor_object_recognized"] = round(new_rec, 4)
        self.state["pir_inhibition"] = round(new_inh, 4)
        self.state["ofc_relay"] = round(ofc, 4)
        self.state["amygdala_relay"] = round(amygdala, 4)
        self.state["ec_relay"] = round(ec, 4)
        self.state["habituation_level"] = round(new_hab, 4)
        self.state["pir_state"] = state
        self.state["recent_odor"] = history
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pir_pyramidal_drive": round(new_pir, 4),
            "odor_object_recognized": round(new_rec, 4),
            "pir_inhibition": round(new_inh, 4),
            "ofc_relay": round(ofc, 4),
            "amygdala_relay": round(amygdala, 4),
            "ec_relay": round(ec, 4),
            "habituation_level": round(new_hab, 4),
            "pir_state": state,
        }
