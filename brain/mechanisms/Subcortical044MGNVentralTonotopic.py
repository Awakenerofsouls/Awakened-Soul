"""
Subcortical044MGNVentralTonotopic.py — Wire 44: TonotopicAuditoryRelay
======================================================================

Medial Geniculate Nucleus (MGN), ventral division. Primary thalamic
auditory relay with precise tonotopic organization.

Neural substrate: MGN ventral division (mMGNv) is the main conduit
between inferior colliculus (IC) and primary auditory cortex (AI/A1).
It is anatomically laminated (layers I-VI), receives the bulk of
inferior colliculus input via the brachium of the inferior colliculus
(BIC), and projects topographically to thalamocortical layers IV and VIB
of auditory cortex. The tonotopic map is its defining organizational
principle: low-frequency tuned neurons are located rostrolaterally,
high-frequency tuned neurons are located caudomedially. This frequency
axis is preserved from IC → MGN → auditory cortex.

Click-train and temporal processing: The ventral MGN contains neurons
classified as "onset," "sustained," "pauser," and "chopper" types
(Aitkin & Webster 1962, Aitkin 1986). Onset neurons respond only to
the onset of a sound; sustained neurons maintain firing during the
stimulus; pauser neurons show an initial burst followed by a pause
then resumed firing; chopper neurons fire in a regular, clock-like
pattern independent of stimulus phase. Click trains at 10-50 Hz produce
distinct temporal patterns, with best modulation frequencies (BMF)
typically in the 10-20 Hz range for most ventral MGN neurons.

Frequency coding: Characteristic frequency (CF) is the frequency at
which a neuron responds at its lowest threshold. Q-factor (filter
sharpness) varies across the tonotopic map — some neurons are broadly
tuned (low Q), others are sharply tuned (high Q, narrow bandwidth).
This gradient is not uniform: the 4-8 kHz region in many mammals has
the largest representational area (the "auditory fovea"), reflecting
evolutionary significance of frequencies used in vocal communication.

Refs:
- Aitkin 1986 "The Auditory Midbrain" — foundational MGN organization
- Aitkin & Webster 1962 J Neurophysiol 25 — MGN single-unit tuning
- Winer 2005 Prog Brain Res — comprehensive thalamic auditory review
- Escabi & Schreiner 2002 J Neurosci — spectrotemporal tuning in MGN
- Miller et al. 2001 J Neurophysiol — temporal modulation transfer
- Redies et al. 1989 J Comp Neurol — MGN lamination and IC inputs
- Rouiller et al. 1979 J Comp Neurol — BIC termination patterns

CITATIONS:
    PMC9504316 — Meng Q, Schneider KA (2022). A Specialized Channel for Encoding
        Auditory Transients in the Magnocellular Division of the Human Medial
        Geniculate Nucleus. J Neurosci.
    PMC2949681 — Weinberger NM (2011). The Medial Geniculate, Not the Amygdala, as
        the Root of Auditory Fear Conditioning. Hear Res.


CITATIONS
---------
  - [Hickok 2007, Nat Rev Neurosci 8:393, dual-stream auditory]
  - [Recanzone 2008, Hear Res 229:115, auditory cortex]
  - [King 2009, Curr Opin Neurobiol 19:402, auditory plasticity]
"""

from brain.base_mechanism import BrainMechanism


class TonotopicAuditoryRelay(BrainMechanism):
    """
    MGN ventral division — tonotopic auditory relay.

    Models the primary thalamocortical auditory pathway: receives
    inferior colliculus frequency-band signals, maintains a rolling
    tonotopic activation map across frequency bands (low→high axis),
    classifies neuron types (onset/sustained/pauser/chopper), computes
    temporal modulation transfer for click trains, and passes a
    frequency-coded signal to auditory cortex.

    The tonotopic_signal output reflects the activated frequency band
    index (0=low, 9=high). auditory_relay_strength reflects relay
    fidelity (how well IC input was preserved/transmitted). frequency_
    coding reflects the precision/sharpness of the current frequency
    representation.
    """

    N_BANDS = 10          # 10 frequency bands across the tonotopic axis
    MODULATION_BMF = 15   # best modulation frequency for click trains (Hz)
    RELAY_DECAY = 0.08    # decay of relay strength per tick (forgets stale input)

    def __init__(self):
        super().__init__(
            name="TonotopicAuditoryRelay",
            human_analog="MGN ventral division — primary thalamic auditory relay",
            layer="subcortical",
        )
        # Tonotopic map: band activations (0=low freq, 9=high freq)
        self.state.setdefault("tonotopic_map", [0.0] * self.N_BANDS)
        self.state.setdefault("last_active_band", 4)
        self.state.setdefault("relay_strength", 0.0)
        self.state.setdefault("frequency_sharpness", 0.5)
        self.state.setdefault("click_train_phase", 0.0)
        self.state.setdefault("temporal_modulation_strength", 0.0)
        self.state.setdefault("dominant_frequency_cf", 0.5)
        self.state.setdefault("neuron_type_state", "sustained")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Sources of auditory input:
        # - Inferior colliculus (IC) from subcortical auditory chain
        # - Direct auditory brainstem nuclei (SOC -> inferior colliculus)
        # Fallback: use arousal level as a proxy for ambient auditory activity
        ic_signal = prior.get("InferiorColliculusAuditory", {}).get("ic_activity", 0.5)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)

        # Use IC signal if available, else arousal proxy
        raw_activity = ic_signal if ic_signal is not None else arousal

        # --- Compute dominant frequency band ---
        # Simulate spectral analysis: map overall activity to a frequency band
        # Low activity → low frequency band (natural quiet scenes)
        # High activity + arousal → higher frequency bands
        activity_norm = max(0.0, min(1.0, raw_activity))

        if activity_norm > 0.7:
            # High activity → mid-to-high frequency bands (3-9)
            band_idx = int(3 + (activity_norm - 0.7) / 0.3 * 6)
        elif activity_norm > 0.4:
            # Mid activity → mid bands (2-5)
            band_idx = int(2 + (activity_norm - 0.4) / 0.3 * 3)
        else:
            # Low activity → low bands (0-2)
            band_idx = int(activity_norm / 0.4 * 2)

        band_idx = max(0, min(self.N_BANDS - 1, band_idx))

        # --- Update tonotopic map (spatial spreading of activation) ---
        current_map = list(self.state["tonotopic_map"])
        activated_band = band_idx

        # Spread activation to adjacent bands (tonotopic continuity)
        spread_width = 2
        for i in range(max(0, activated_band - spread_width),
                       min(self.N_BANDS, activated_band + spread_width + 1)):
            distance = abs(i - activated_band)
            spread = 1.0 - (distance / (spread_width + 1)) * 0.7
            new_val = activity_norm * spread
            current_map[i] = max(current_map[i] * 0.85, new_val)

        # Decay all bands slightly
        current_map = [max(0.0, v - self.RELAY_DECAY) for v in current_map]

        # --- Relay strength ---
        # Increases when IC input is strong and tonotopic activation is coherent
        map_peak = max(current_map) if current_map else 0.0
        target_strength = map_peak
        current_strength = self.state["relay_strength"]
        relay_strength = current_strength * 0.85 + target_strength * 0.15
        relay_strength = max(0.0, min(1.0, relay_strength))

        # --- Frequency coding / characteristic frequency ---
        # Weighted center-of-mass of the tonotopic map
        if sum(current_map) > 0.001:
            cf_weighted = sum(
                (i / (self.N_BANDS - 1)) * v
                for i, v in enumerate(current_map)
            ) / sum(current_map)
        else:
            cf_weighted = self.state["dominant_frequency_cf"] * 0.9

        # --- Frequency sharpness (Q-factor analogue) ---
        # Sharp when one band dominates; broad when many bands active
        peak = max(current_map)
        total = sum(current_map) + 0.001
        sharpness = peak / total  # 0.1 = broad, 0.9 = very sharp
        frequency_sharpness = 0.1 + sharpness * 0.8

        # --- Click-train / temporal modulation ---
        # Simulate phase-locking to periodic input (like click trains)
        prev_phase = self.state["click_train_phase"]
        bmf = self.MODULATION_BMF
        # Phase advances proportional to normalized activity
        phase_delta = (activity_norm * 0.3) + 0.02
        new_phase = (prev_phase + phase_delta) % (2 * 3.14159)
        # Modulation strength peaks when phase is near zero (reset cycle)
        phase_near_reset = 1.0 - abs(new_phase - 3.14159) / 3.14159
        modulation_strength = relay_strength * phase_near_reset * 0.8

        # --- Determine dominant neuron type ---
        # onset: sharp burst then silence; sustained: maintained response;
        # pauser: burst-pause-burst; chopper: regular clock-like
        if relay_strength > 0.6 and frequency_sharpness > 0.65:
            neuron_type = "chopper"
        elif relay_strength > 0.5 and map_peak < 0.4:
            neuron_type = "pauser"
        elif relay_strength > 0.3 and frequency_sharpness < 0.4:
            neuron_type = "sustained"
        else:
            neuron_type = "onset"

        # --- Assemble tonotopic signal ---
        # Which band is most activated right now (primary output)
        dominant_band = current_map.index(peak) if peak > 0.05 else self.state["last_active_band"]
        tonotopic_signal = dominant_band / (self.N_BANDS - 1)  # normalized 0-1

        # --- Persist ---
        self.state["tonotopic_map"] = current_map
        self.state["last_active_band"] = dominant_band
        self.state["relay_strength"] = relay_strength
        self.state["frequency_sharpness"] = frequency_sharpness
        self.state["click_train_phase"] = new_phase
        self.state["temporal_modulation_strength"] = modulation_strength
        self.state["dominant_frequency_cf"] = cf_weighted
        self.state["neuron_type_state"] = neuron_type
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "tonotopic_signal": round(tonotopic_signal, 4),
            "auditory_relay_strength": round(relay_strength, 4),
            "frequency_coding": {
                "characteristic_frequency": round(cf_weighted, 4),
                "sharpness": round(frequency_sharpness, 4),
                "dominant_band": dominant_band,
                "band_map": [round(v, 4) for v in current_map],
            },
            "temporal_modulation": {
                "click_phase": round(new_phase, 4),
                "modulation_strength": round(modulation_strength, 4),
                "bmf_sim": bmf,
            },
            "neuron_type": neuron_type,
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

