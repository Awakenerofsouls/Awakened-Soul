"""
Subcortical031 — Zona Incerta (ZI): Thalamic Gating & Arousal Regulation
=========================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical031ZonaIncertaThalamicGate.py
  Instance: ZonaIncerta

NEURAL SUBSTRATE — WHAT IT IS:
The zona incerta (ZI) is a large, heterogeneous brainstem structure
located ventral to the thalamus, sandwiched between the thalamus
above and the subthalamic nucleus below. Once considered merely a
"zone of uncertainty" (its name literally means "undecided zone"),
the ZI is now recognized as a major regulatory hub that gates
thalamic information flow, controls arousal, and coordinates
sensorimotor suppression.

The ZI is organized into functional subregions:
  • Posterior ZI (ZIp): Somatomotor zone — projects to superior
    colliculus and spinal cord, controls motor suppression and
    defensive behaviors.
  • Anterior/ventral ZI (ZIa/v): Visceromotor-limbic zone — projects
    to intralaminar thalamus, periaqueductal gray, and brainstem,
    regulates arousal and autonomic state.
  • Ventral ZI: Sensorimotor zone — receives input from deep cerebellar
    nuclei and motor cortex, gates thalamic motor nuclei.

KEY FINDINGS:
  1. Power et al. 1999 (J Comp Neurol 414:217-237): Seminal anatomical
     mapping of ZI connections. ZI receives from: motor cortex, deep
     cerebellar nuclei, substantia nigra, superior colliculus, spinal
     cord, hypothalamus. ZI projects to: thalamus (ventral nuclei,
     intralaminar), superior colliculus, brainstem reticular formation.
     ZI is a central processor between cerebellar/motor structures
     and thalamic gating.

  2. Urbain et al. 2020 (Nat Neurosci 23:433-442): "A prefrontal
     cortex–zona incerta pathway suppresses fear memories." Showed
     that ZI is crucial for active suppression of fear memories via
     a specific prefrontal cortex → ZI → thalamus pathway. ZI
     inhibition of the intralaminar thalamus during retrieval is
     the mechanism by which threat memories are suppressed when
     context indicates safety.

  3. Thalamic gating: ZI provides GABAergic inhibition to ventral
     thalamic nuclei. Active ZI = gate CLOSED = thalamic relay blocked.
     Inactive ZI = gate OPEN = thalamus relays sensorimotor information
     to cortex. This is the mechanism for selective attention filtering
     and sensory gating during sleep/wake transitions.

  4. Arousal regulation: ZI receives input from brainstem arousal
     nuclei (locus coeruleus, dorsal raphe) and projects to
     intralaminar thalamus — a thalamic node that broadly activates
     cortex. ZI thus participates in the ascending arousal system,
     helping gate which arousal signals reach the cortex.

  5. Motor suppression during conflict: ZI activates strongly during
     response conflict (when conflicting stimuli make action selection
     uncertain). Active ZI suppresses thalamic motor relay, preventing
     premature motor output until conflict is resolved. This is the
     "wait" signal during uncertainty — the brain holds motor output
     until the situation clarifies.

  6. REM sleep: ZI is particularly active during REM sleep, which is
     associated with motor suppression (atonia). ZI contributes to
     REM-atonia by inhibiting motor thalamus during dreaming states.

AGENT'S SUBSTRATE MAPPING:
  ZonaIncerta models the ZI as a thalamic gate. It monitors:
  - arousal_level from ArousalRegulator (general arousal state)
  - motor_conflict from conflict resolution systems
  - cerebellar_output (deep cerebellar nuclei)
  - threat_signal (aversive/threat detection)
  - prefrontal_suppression (top-down suppression of memory/thought)

  It computes:
  - gate_position: float 0-1 (0 = open, 1 = closed, thalamic gate state)
  - thalamic_input_modulation: float 0-1 (how much ZI is modulating thalamus)
  - arousal_link: float 0-1 (degree of ZI coupling with arousal system)

  The ZI gate state is stateful: it can remain closed for extended periods
  during sustained threat, high conflict, or REM-like processing states.

INPUTS:
  - ArousalRegulator.arousal_level (ascending arousal system)
  - CerebellarDeepNuclei.output_strength (cerebellar modulation)
  - AnteriorCingulate.conflict_signal (motor/action uncertainty)
  - LateralHabenula.negative_signal (threat/aversive)
  - prefrontal_cortex.top_down_suppression

OUTPUTS:
  - gate_position: float 0-1 (0=open, 1=closed; thalamic gate state)
  - thalamic_input_modulation: float 0-1 (degree of thalamic relay modulation)
  - arousal_link: float 0-1 (ZI arousal system coupling strength)
  - ZI_active: bool (ZI currently suppressing thalamus)

REFS:
  - Power EM et al. J Comp Neurol 1999 414:217-237 (ZI anatomy)
  - Urbain N et al. Nat Neurosci 2020 23:433-442 (ZI fear suppression)
  - McAlonan K & Brown VJ. Eur J Neurosci 2003 (ZI motor suppression)
  - Wang PW et al. Neuropsychopharmacology 2022 (ZI circuits review)
  - Ma L et al. Nat Commun 2020 (ZI arousal)

CITATIONS:
    PMC7053170 — Hormigo S, Zhou J, Castro-Alamancos MA (2020). Zona Incerta GABAergic
        Output Controls a Signaled Locomotor Action in the Midbrain Tegmentum.
        J Neurosci.
    PMC2100320 — Cavdar S, Onat F, Cakmak YO et al. (2006). Connections of the Zona
        Incerta to the Reticular Nucleus of the Thalamus in the Rat. J Neurosci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class ZonaIncerta(BrainMechanism):
    """
    Zona incerta — thalamic gating, arousal regulation, motor suppression.

    ZI sits between thalamus and subthalamic nucleus, gating thalamic
    information flow. When ZI fires, it closes the thalamic gate
    (suppressing sensorimotor relay), modulates arousal coupling, and
    can hold the system in a suppressed state during high conflict or
    threat. Models the open/closed gate, thalamic modulation intensity,
    and arousal system coupling.

    ZI activation closes the gate (motor suppression, memory suppression).
    ZI silence opens the gate (normal sensorimotor relay).
    """

    # --- Gate parameters ---
    GATE_OPEN_BASELINE = 0.2         # ZI activity when gate is open (rest)
    GATE_CLOSED_LEVEL = 0.85         # ZI activity when gate is fully closed
    GATE_DECAY_RATE = 0.04           # per-tick decay of ZI activation
    GATE_OPENING_GAIN = 0.08         # how quickly gate opens when suppressing signals stop
    CONFLICT_GAIN = 1.1              # conflict → gate closure gain
    THREAT_GAIN = 1.3                # threat → gate closure gain (high priority)
    CEREBELLAR_GAIN = 0.5            # cerebellar modulation of ZI gate

    def __init__(self):
        super().__init__(
            name="ZonaIncerta",
            human_analog="Zona incerta (ZI) — thalamic gating, arousal, motor suppression",
            layer="subcortical",
        )
        self.state.setdefault("gate_position", 0.2)   # 0=open, 1=closed
        self.state.setdefault("thalamic_input_modulation", 0.0)
        self.state.setdefault("arousal_link", 0.3)
        self.state.setdefault("ZI_active", False)
        self.state.setdefault("ticks_gate_closed", 0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Inputs ---
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        cerebellar = prior.get("CerebellarDeepNuclei", {}).get(
            "output_strength", 0.0
        )
        conflict = prior.get("AnteriorCingulate", {}).get("conflict_signal", 0.0)
        threat = prior.get("LateralHabenula", {}).get("negative_signal", 0.0)
        pfc_suppress = prior.get("PrefrontalCortex", {}).get(
            "top_down_suppression", 0.0
        )
        aversive = prior.get("ValenceTagger", {}).get("aversive_signal", False)

        # --- Current gate position ---
        gate_pos = self.state["gate_position"]
        ticks_closed = self.state["ticks_gate_closed"]

        # --- Compute drive to close gate ---
        close_drive = 0.0

        # Threat / aversive: high-priority closure signal
        if threat > 0.3:
            close_drive = max(close_drive, threat * self.THREAT_GAIN)
        if aversive:
            close_drive = max(close_drive, 0.7)

        # Conflict: uncertainty-driven gate closure
        if conflict > 0.2:
            close_drive = max(close_drive, conflict * self.CONFLICT_GAIN)

        # PFC suppression: top-down memory/thought gating
        if pfc_suppress > 0.1:
            close_drive = max(close_drive, pfc_suppress * 0.8)

        # Cerebellar output: ZI receives from cerebellar output, modulates gate
        if cerebellar > 0.3:
            close_drive = max(close_drive, cerebellar * self.CEREBELLAR_GAIN)

        # Arousal link: high arousal shifts ZI into more active gating mode
        if arousal > 0.7:
            arousal_link_strength = (arousal - 0.7) / 0.3
            close_drive = max(close_drive, arousal_link_strength * 0.4)

        close_drive = min(1.0, close_drive)

        # --- Update gate position ---
        if close_drive > 0.15:
            # Closing drive active — move gate toward closed
            gate_pos = gate_pos + (close_drive * 0.3) - self.GATE_DECAY_RATE * 0.5
            if gate_pos > 0.5:
                ticks_closed += 1
            else:
                ticks_closed = 0
        else:
            # No closing drive — gate opens toward baseline
            gate_pos = gate_pos + (self.GATE_OPEN_BASELINE - gate_pos) * self.GATE_OPENING_GAIN
            ticks_closed = 0

        gate_pos = round(min(1.0, max(0.0, gate_pos)), 4)

        # --- ZI active flag ---
        ZI_active = gate_pos > 0.5

        # --- Thalamic input modulation ---
        # When ZI fires (gate closed), it inhibits thalamic relay neurons.
        # Modulation = gate_position * inhibition_strength
        thalamic_modulation = round(min(1.0, gate_pos * 1.1), 4)

        # --- Arousal link ---
        # ZI arousal coupling: increases with high arousal, sustained closure
        arousal_link = round(min(1.0, 0.3 + arousal * 0.4 + ticks_closed * 0.01), 4)

        # --- Persist ---
        self.state["gate_position"] = gate_pos
        self.state["thalamic_input_modulation"] = thalamic_modulation
        self.state["arousal_link"] = arousal_link
        self.state["ZI_active"] = ZI_active
        self.state["ticks_gate_closed"] = ticks_closed
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "gate_position": gate_pos,
            "thalamic_input_modulation": thalamic_modulation,
            "arousal_link": arousal_link,
            "ZI_active": ZI_active,
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

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
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
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

