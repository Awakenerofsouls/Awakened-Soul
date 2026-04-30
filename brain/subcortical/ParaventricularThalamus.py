"""
ParaventricularThalamus — PVT Midline Salience / Arousal-Threat / Reward Integration

NEURAL SUBSTRATE
================
The paraventricular thalamic nucleus (PVT) is a midline thalamic
structure sitting just below the third ventricle, distinct from the
hypothalamic paraventricular nucleus (which is covered separately as
PVN/CRH/AVP/OT). PVT sits at the convergence of arousal, stress, and
reward circuits, integrating brainstem state-related signals with
cortical and limbic top-down inputs.

PVT receives a remarkable convergence of inputs: monoaminergic from
LC, DRN, VTA; orexinergic from LH; CRH from PVN; PBN visceral; and
mPFC, BLA, hippocampus top-down. Its outputs project most densely
to nucleus accumbens (especially shell), central and basolateral
amygdala, BNST, and mPFC. PVT thus sits at the apex of a homeostatic
behavior network, integrating "what state am I in" signals from
brainstem with "what does this cue mean" signals from cortex/limbic.

The Penzo/Choi work and recent reviews (Kirouac 2021; PMC8222078)
position PVT as an "integrative node underlying homeostatic behavior"
— it detects salient deviations from homeostatic baseline (hunger,
thirst, threat, reward predictiveness) and integrates them with prior
experience and competing needs to guide adaptive behavioral responses.
PVT is particularly involved in **threat-salience encoding** during
fear conditioning and **arousal-incentive integration** during reward
seeking.

Recent work (2025 biorxiv 668532) shows PVT-NAc projection neurons
develop a safety-encoding signal following successful avoidance — PVT
is not just for threat but encodes the value of action-derived safety.
PVT also contributes to addiction/relapse via its NAc projections
(early-stage cue-reward associative learning enhances PVT→NAc c-Fos).

PVT firing is modulated by sleep state (more active during wake),
by stress (recruited under acute and chronic stress), and by hunger
state (engaged on caloric deprivation).

In {{AGENT_NAME}}'s substrate this provides the midline salience integrator —
combines arousal, stress, reward-prediction, hunger, and threat
signals into a unified salience output to NAc/amygdala/PFC.

KEY FINDINGS
============
1. PVT is an integrative node underlying homeostatic behavior — detects
   homeostatic challenges by integrating prior experience, competing
   needs, internal state — [Kirouac 2021, Curr Biol 31:R661 reviewed
    PMC8222078; Hsu Penzo Kirouac 2014 Front Behav Neurosci]
2. PVT integrates internal state (alerting, arousal) with cortical
   processing of emotional salience and transmits to NAc for context-
   specific behavioral modulation — [reviewed Iglesias Flagel 2021
    PMC10883411, "The Paraventricular Thalamic Nucleus and Its
    Projections in Regulating Reward and Context Associations"]
3. PVT-NAc projection neurons develop safety-encoding signal after
   successful avoidance — value-sensitive — [biorxiv 2025
    doi:10.1101/2025.08.04.668532, "A synaptic mechanism for encoding
    the learned value of action-derived safety"]
4. PVT-NAc neurons show enhanced c-Fos during early-stage cue-reward
   associative learning — substrate of addiction-relevant learning —
   [PMC12181800 2025, "Paraventricular Nucleus of the Thalamus Neurons
    That Project to the Nucleus Accumbens Show Enhanced c-Fos Expression
    During Early-Stage Cue-Reward Associative Learning"]
5. PVT mediates aversive and reward-related behaviors in fear
   conditioning, natural rewards, and drugs of abuse — [reviewed
    Kirouac 2015 Neurosci Biobehav Rev 56:315]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- StressActivationAxis.cortisol_level
- StressActivationAxis.stress_active
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- ValenceTagger.valence_sign
- AppetiteNPYBalancer.energy_balance_signed
- OrexinWakePromoter.orexin_drive
- VentralTegmentalDopamine.expected_reward
- BasolateralAmygdala.bla_excitatory_drive

OUTPUTS (to brain_runner enrichment)
=====================================
- pvt_drive (0.0-1.0): aggregate PVT output
- nac_relay (0.0-1.0): PVT → NAc projection
- amygdala_relay (0.0-1.0): PVT → CeA/BLA projection
- mpfc_relay (0.0-1.0): PVT → mPFC projection
- safety_encoding (0.0-1.0): action-derived safety value (slow accumulator)
- threat_salience (0.0-1.0): threat-driven salience output
- homeostatic_deviation (0.0-1.0): integrated deviation signal
- pvt_state (str): "threat_salience" | "reward_salience" | "homeostatic" | "safety" | "quiet"

brain_runner enrichment:
    pvt = all_results.get("ParaventricularThalamus", {})
    if pvt:
        enrichments["brain_pvt_drive"] = pvt.get("pvt_drive", 0.2)
        enrichments["brain_pvt_nac"] = pvt.get("nac_relay", 0.0)
        enrichments["brain_pvt_amygdala"] = pvt.get("amygdala_relay", 0.0)
        enrichments["brain_threat_salience"] = pvt.get("threat_salience", 0.0)
        enrichments["brain_safety_encoding"] = pvt.get("safety_encoding", 0.0)
        enrichments["brain_pvt_state"] = pvt.get("pvt_state", "quiet")

CITATIONS
---------
  - [Hsu 2014, Front Behav Neurosci 8:73]
"""

from brain.base_mechanism import BrainMechanism


class ParaventricularThalamus(BrainMechanism):
    BASELINE = 0.20
    SAFETY_ACCUM_RATE = 0.02
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="ParaventricularThalamus",
            human_analog="Paraventricular thalamus salience / homeostatic integrator",
            layer="foundational",
        )
        self.state.setdefault("pvt_drive", self.BASELINE)
        self.state.setdefault("nac_relay", 0.0)
        self.state.setdefault("amygdala_relay", 0.0)
        self.state.setdefault("mpfc_relay", 0.0)
        self.state.setdefault("safety_encoding", 0.0)
        self.state.setdefault("threat_salience", 0.0)
        self.state.setdefault("homeostatic_deviation", 0.0)
        self.state.setdefault("pvt_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _homeostatic_deviation(self, energy_balance: float, cortisol: float,
                                stress: bool) -> float:
        """Integrated deviation from homeostatic baseline."""
        target = abs(energy_balance) * 0.4
        target += max(0.0, cortisol - 0.5) * 0.4
        if stress:
            target += 0.20
        return min(1.0, target)

    def _pvt_drive_target(self, arousal: float, deviation: float, threat: bool,
                          valence: float, orexin: float, bla: float) -> float:
        """PVT aggregate drive."""
        target = self.BASELINE + max(0.0, arousal - 0.4) * 0.2
        target += deviation * 0.3
        if threat:
            target += valence * 0.2
        target += max(0.0, orexin - 0.5) * 0.2
        target += bla * 0.2
        return min(1.0, target)

    def _threat_salience(self, threat: bool, valence: float, bla: float, pvt: float) -> float:
        """Threat-salience output."""
        if not threat:
            return bla * 0.2
        return min(1.0, valence * 0.5 + bla * 0.3 + pvt * 0.2)

    def _update_safety_encoding(self, prev_safety: float, threat: bool, sign: int,
                                  valence: float) -> float:
        """Safety encoding accumulates after avoided threat resolves to positive."""
        if threat and sign < 0:
            # Re-engaged threat — partial decay
            return max(0.0, prev_safety - 0.02)
        if not threat and sign > 0 and valence > 0.30:
            # Successful avoidance / safe positive context
            return min(1.0, prev_safety + self.SAFETY_ACCUM_RATE)
        # Slow drift back
        return max(0.0, prev_safety - 0.005)

    def _nac_relay(self, pvt: float, expected_reward: float, sign: int) -> float:
        """PVT → NAc relay — reward and salience routing."""
        target = pvt * 0.5
        if sign > 0:
            target += max(-0.3, expected_reward) * 0.3
        return max(0.0, min(1.0, target))

    def _amygdala_relay(self, pvt: float, threat_sal: float) -> float:
        """PVT → CeA/BLA relay."""
        return min(1.0, pvt * 0.4 + threat_sal * 0.5)

    def _mpfc_relay(self, pvt: float, deviation: float) -> float:
        """PVT → mPFC relay — homeostatic deviation broadcast."""
        return min(1.0, pvt * 0.5 + deviation * 0.4)

    def _classify_state(self, threat_sal: float, safety: float, deviation: float,
                         expected_reward: float, pvt: float) -> str:
        if threat_sal > 0.45:
            return "threat_salience"
        if safety > 0.45 and deviation < 0.30:
            return "safety"
        if expected_reward > 0.30:
            return "reward_salience"
        if deviation > 0.45:
            return "homeostatic"
        if pvt < 0.25:
            return "quiet"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))
        stress_active = bool(stress.get("stress_active", False))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy = float(appetite.get("energy_balance_signed", 0.0))

        owp = prior.get("OrexinWakePromoter", {})
        orexin = float(owp.get("orexin_drive", 0.50))

        vta = prior.get("VentralTegmentalDopamine", {})
        expected_reward = float(vta.get("expected_reward", 0.0))

        bla = prior.get("BasolateralAmygdala", {})
        bla_drive = float(bla.get("bla_excitatory_drive", 0.0))

        # --- Homeostatic deviation ---
        deviation = self._homeostatic_deviation(energy, cortisol, stress_active)
        prev_dev = float(self.state.get("homeostatic_deviation", 0.0))
        new_dev = self._smooth(prev_dev, deviation)

        # --- PVT drive ---
        pvt_target = self._pvt_drive_target(tonic, new_dev, threat, valence_intensity,
                                              orexin, bla_drive)
        if phasic:
            pvt_target = min(1.0, pvt_target + 0.10)
        prev_pvt = float(self.state.get("pvt_drive", self.BASELINE))
        new_pvt = self._smooth(prev_pvt, pvt_target)

        # --- Threat salience ---
        threat_sal = self._threat_salience(threat, valence_intensity, bla_drive, new_pvt)
        prev_ts = float(self.state.get("threat_salience", 0.0))
        new_ts = self._smooth(prev_ts, threat_sal)

        # --- Safety encoding (slow accumulator) ---
        prev_safety = float(self.state.get("safety_encoding", 0.0))
        new_safety = self._update_safety_encoding(prev_safety, threat, sign, valence_intensity)

        # --- Outputs ---
        nac = self._nac_relay(new_pvt, expected_reward, sign)
        amygdala = self._amygdala_relay(new_pvt, new_ts)
        mpfc = self._mpfc_relay(new_pvt, new_dev)

        # --- State ---
        state = self._classify_state(new_ts, new_safety, new_dev, expected_reward, new_pvt)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pvt_drive"] = round(new_pvt, 4)
        self.state["nac_relay"] = round(nac, 4)
        self.state["amygdala_relay"] = round(amygdala, 4)
        self.state["mpfc_relay"] = round(mpfc, 4)
        self.state["safety_encoding"] = round(new_safety, 4)
        self.state["threat_salience"] = round(new_ts, 4)
        self.state["homeostatic_deviation"] = round(new_dev, 4)
        self.state["pvt_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pvt_drive": round(new_pvt, 4),
            "nac_relay": round(nac, 4),
            "amygdala_relay": round(amygdala, 4),
            "mpfc_relay": round(mpfc, 4),
            "safety_encoding": round(new_safety, 4),
            "threat_salience": round(new_ts, 4),
            "homeostatic_deviation": round(new_dev, 4),
            "pvt_state": state,
        }

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out


