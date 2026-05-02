"""
Subcortical011SuperiorCerebellarPeduncleRelay.py — Wire 11: SCPThalamicRelay

Superior Cerebellar Peduncle (SCP) thalamic relay mechanism.

Models the SCP as the major cerebellar output tract, computing
output_fidelity of the cerebellar-thalamic relay, thalamic_relay_strength
of the VL/VA projection, and cerebellar_efference which is the
downstream signal entering thalamus en route to cortex.

Neural analog: Superior Cerebellar Peduncle (SCP) — the largest
cerebellar efferent pathway. All DCN output (from all four nuclei)
travels through the SCP after decussating (crossing) in the midbrain:

1. ANATOMY:
   - Origin: Deep Cerebellar Nuclei (dentate, emboliform, globose, fastigial)
   - Course: ascends from cerebellum → decussates in midbrain (ventral decussation)
   - Termination: VL (ventral lateral) and VA (ventral anterior) thalamic nuclei
   - From thalamus: projects to motor cortex (M1, premotor) and prefrontal cortex

2. DECUSSATION:
   - SCP fibers cross at the midbrain level before reaching the thalamus
   - This means the LEFT cerebellum sends output to the RIGHT thalamus
     → RIGHT motor/prefrontal cortex
   - This crossed arrangement underlies the cerebellum's ipsilateral
     coordination (left cerebellum coordinates the left side of the body)

3. FUNCTIONAL RELAY:
   Stoodley & Schmahmann 2009 (Cortex 45:975-991) described the SCP as
   "the main efferent pathway for cerebellar output to the cerebral
   cortex" with two primary targets:
   - VL nucleus → motor cortex (primary and premotor)
   - VA nucleus → prefrontal cortex (cognitive operations)

4. CEREBELLO-THALAMO-CORTICAL LOOP:
   Input: Cerebral cortex (motor planning, premotor, prefrontal) →
   Pontine nuclei → Mossy fibers → Cerebellar cortex →
   Purkinje cells → DCN → SCP → Thalamus (VL/VA) →
   Cerebral cortex (closed loop)

5. RELAY FIDELITY:
   The SCP relay has finite bandwidth. Under high cognitive load,
   cerebellar signals compete with other thalamic inputs. Relay
   fidelity is modulated by attention, arousal, and competing traffic.

6. FIDELITY DISRUPTION:
   - Lesions of SCP produce cerebellar outflow ataxia
   - Disconnection of SCP (superior cerebellar peduncle syndrome) causes
     dysmetria, intention tremor, dysdiadochokinesia
   - These are classic cerebellar motor signs seen when the output
     pathway is disrupted

REFS:
- Stoodley & Schmahmann 2009 Cortex 45:975-991
  "Functional topography of the human cerebellum"
- Ramnani 2006 Nat Rev Neurosci 7:511-522
- Purves et al. Neuroscience 5th ed. 2018 (SCP anatomy)
- Ito 2008 Scholarpedia 3:1410
- Bostan et al. 2013 Front Neural Circuits 7:93 (cerebello-thalamic circuits)

CITATIONS:
    PMC4575696 — Palesi F, Tournier JD, Calamante F et al. (2015). Contralateral
        Cerebello-Thalamo-Cortical Pathways with Prominent Involvement of Associative
        Areas in Humans In Vivo. Neuroimage.
    PMC4537674 — Houck BD, Person AL (2015). Cerebellar Premotor Output Neurons
        Collateralize to Innervate the Cerebellar Cortex. J Neurosci.


CITATIONS
---------
  - [Sherman 2002, Phil Trans R Soc Lond B 357:1695, thalamic relay]
  - [Halassa 2017, Nat Neurosci 20:1669, thalamic computation]
  - [Saalmann 2012, Science 337:753, pulvinar attention]
"""

from brain.base_mechanism import BrainMechanism


class SCPThalamicRelay(BrainMechanism):
    """
    Superior Cerebellar Peduncle thalamic relay mechanism.

    Models the SCP as a noisy relay channel between DCN output and
    VL/VA thalamic nuclei. Computes:
    - output_fidelity: relay channel quality (function of noise + competition)
    - thalamic_relay_strength: effective thalamic activation
    - cerebellar_efference: downstream signal entering cortex

    The SCP passes through the decussation (midbrain crossing), so this
    mechanism models both the raw cerebellar output and the post-decussation
    thalamic signal.
    """

    SCP_DECUSSATION_LOSS = 0.12
    THALAMIC_NOISE_FLOOR = 0.05
    FIDELITY_DECAY = 0.04

    def __init__(self):
        super().__init__(
            name="SCPThalamicRelay",
            human_analog="Superior Cerebellar Peduncle → VL/VA thalamic relay",
            layer="subcortical",
        )
        self.state.setdefault("output_fidelity", 0.85)
        self.state.setdefault("thalamic_relay_strength", 0.5)
        self.state.setdefault("cerebellar_efference", 0.5)
        self.state.setdefault("relay_noise", 0.0)
        self.state.setdefault("decussation_crossed_output", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        dcn_data = prior.get("CerebellarOutputGate", {})
        arousal_data = prior.get("ArousalRegulator", {})

        # Input signals
        cerebellar_output = dcn_data.get("cerebellar_output_signal", 0.5)
        motor_command = dcn_data.get("motor_command_strength", 0.5)
        cognitive_command = dcn_data.get("cognitive_command_strength", 0.5)
        thalamic_traffic = input_data.get("thalamic_traffic", 0.3)
        attention_allocation = input_data.get("attention_allocation", 0.5)
        arousal = arousal_data.get("arousal_level", 0.5)

        # --- Decussation: crossed output ---
        # SCP fibers cross at midbrain → output to contralateral thalamus
        # A small loss occurs at the decussation (axonal path length + crossing noise)
        decussation_loss = self.SCP_DECUSSATION_LOSS
        raw_crossed_output = cerebellar_output * (1.0 - decussation_loss)
        self.state["decussation_crossed_output"] = round(raw_crossed_output, 4)

        # --- Relay noise ---
        # Noise arises from: thalamic traffic competition, low arousal,
        # spontaneous thalamic firing (thalamic noise floor)
        current_noise = self.state["relay_noise"]
        traffic_noise = thalamic_traffic * 0.15
        arousal_noise = (1.0 - arousal) * 0.1
        new_noise = current_noise * 0.7 + traffic_noise + arousal_noise
        self.state["relay_noise"] = round(new_noise, 4)

        # --- Output fidelity ---
        # Fidelity = clean signal / (signal + noise)
        signal = raw_crossed_output
        noise = new_noise + self.THALAMIC_NOISE_FLOOR
        fidelity = signal / (signal + noise) if (signal + noise) > 0 else 0.0
        fidelity = max(0.0, min(1.0, fidelity))

        # Attention boosts fidelity by reducing thalamic competition
        attention_boost = (attention_allocation - 0.5) * 0.3
        fidelity = max(0.0, min(1.0, fidelity + attention_boost))

        # Slow fidelity decay (prevents sticking at high values)
        fidelity = max(0.0, fidelity - self.FIDELITY_DECAY * (1.0 - fidelity))
        self.state["output_fidelity"] = round(fidelity, 4)

        # --- Thalamic relay strength ---
        # VL gets motor cerebellar output; VA gets cognitive cerebellar output
        # Thalamic relay = weighted combination filtered by fidelity
        thalamic_relay = (
            raw_crossed_output * motor_command * 0.5
            + raw_crossed_output * cognitive_command * 0.5
        ) * fidelity
        thalamic_relay = max(0.0, min(1.0, thalamic_relay))
        self.state["thalamic_relay_strength"] = round(thalamic_relay, 4)

        # --- Cerebellar efference ---
        # This is the signal that enters cortex after the full relay
        cerebellar_efference = (
            thalamic_relay * 0.6
            + raw_crossed_output * fidelity * 0.4
        )
        cerebellar_efference = max(0.0, min(1.0, cerebellar_efference))
        self.state["cerebellar_efference"] = round(cerebellar_efference, 4)

        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "output_fidelity": round(fidelity, 4),
            "thalamic_relay_strength": round(thalamic_relay, 4),
            "cerebellar_efference": round(cerebellar_efference, 4),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

