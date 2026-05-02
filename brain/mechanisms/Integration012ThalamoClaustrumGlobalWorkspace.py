"""
brain/integration/Integration012ThalamoClaustrumGlobalWorkspace.py
Thalamus-Claustrum Global Workspace — Conscious Broadcasting

ANATOMY (Dehaene & Changeux 2011; Baars 1997; Sergent & Naccache 2012):
    The global workspace theory proposes that consciousness arises
    when information is broadcast from a "workspace" to all cortical
    regions simultaneously. The thalamus and claustrum are key
    components of this workspace:

    Thalamus: the "relay" — intralaminar nuclei (centromedian, parafascicular)
    project broadly to cortex, providing a "thalamic relay" for global
    broadcast. The intralaminar nuclei fire during salience and
    arousal, driving global cortical activation.

    Claustrum: the "gateway" — gates which signals enter the global
    workspace. Only signals that pass through the claustrum's
    synchronized burst get broadcast globally.

    Global workspace dynamics:
    - Non-conscious: processing is local (specific cortical regions)
    - Conscious access: information reaches workspace → global broadcast
    - Workspace neurons: distributed across prefrontal, parietal, temporal
    - Competition: only one coherent content wins the workspace at a time

    Key evidence: Dehaene's experiments show that masked (unconscious)
    stimuli do not activate prefrontal cortex; unmasked (conscious)
    stimuli do. The prefrontal cortex is the "workspace hub."

KEY FINDINGS:
    1. Dehaene & Changeux 2011 (PMC3972740): "Global workspace theory
       and conscious access"
    2. Baars 1997: "Global workspace theory of consciousness"
    3. Sergent & Naccache 2012 (PMC4326522): GM workspace and consciousness

AGENT'S MAPPING:
    global_workspace: dict — workspace state
    workspace_broadcast: float 0-1 — strength of broadcast
    all_regions_fired: list — regions that received the broadcast

CITATIONS:
    PMID 32135090 — Mashour et al. (2020). Conscious Processing and the GNW Hypothesis. Neuron.
    PMID 40307561 — Cogitate Consortium (2025). Adversarial testing of GNW and IIT. Nature.
    PMID 16257162 — Crick & Koch (2005). What is the claustrum? Nat Neurosci.
    PMC2697346 — Dehaene et al. (2011). Towards a cognitive neuroscience of global workspace.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class ThalamoClaustrumGlobalWorkspace(BrainMechanism):
    """
    Thalamus-claustrum global workspace — conscious broadcasting.

    Broadcasts salient information to all cortical regions
    simultaneously, creating conscious awareness.
    """

    def __init__(self):
        super().__init__(
            name="ThalamoClaustrumGlobalWorkspace",
            human_analog="Thalamus-claustrum global workspace — conscious broadcasting",
            layer="integration",
        )
        self.state.setdefault("workspace_content", {})
        self.state.setdefault("workspace_broadcast", 0.0)
        self.state.setdefault("all_regions_fired", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Claustrum gate
        claustrum = prior.get("ClaustrumGlobalConsciousness", {})
        claustrum_out = claustrum.get("claustral_output", {})
        if isinstance(claustrum_out, dict):
            claustrum_act = claustrum_out.get("claustrum_activation", 0.5)
            global_broadcast = claustrum_out.get("global_broadcast", False)
        else:
            claustrum_act = 0.5
            global_broadcast = False

        # Thalamic intralaminar nuclei (centromedian — salience broadcast)
        thal_cm = prior.get("ThalamicCentromedianIntralaminar", {})
        cm_out = thal_cm.get("cm_output", {})
        if isinstance(cm_out, dict):
            cm_signal = cm_out.get("intralaminar_strength", 0.5)
        else:
            cm_signal = 0.5

        # Salience network (what gets broadcast)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)

        # ACC (cognitive salience)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
        else:
            error_sig = 0.3

        # Theta-gamma binding (what to broadcast — the content)
        tg = prior.get("ThetaGammaCrossFrequencyBinding", {})
        bound_exp = tg.get("bound_experience", 0.5)

        # Prefrontal cortex hub (workspace hub for conscious content)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5

        # OFC (value — what's worth broadcasting?)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # Workspace readiness
        workspace_readiness = (
            claustrum_act * 0.3 +
            cm_signal * 0.2 +
            bound_exp * 0.2 +
            salience * 0.2 +
            value_sig * 0.1
        )

        # Workspace broadcast
        workspace_broadcast = workspace_readiness * (1.5 if global_broadcast else 1.0)
        workspace_broadcast = max(0.0, min(1.0, workspace_broadcast))

        # Regions that fired: depends on broadcast strength
        regions_fired = []
        if workspace_broadcast > 0.3:
            regions_fired.extend(["pfc", "parietal"])
        if workspace_broadcast > 0.5:
            regions_fired.extend(["temporal", "cingulate"])
        if workspace_broadcast > 0.7:
            regions_fired.extend(["motor", "occipital", "limbic"])

        self.state["workspace_content"] = {"broadcast_strength": round(workspace_broadcast, 4)}
        self.state["workspace_broadcast"] = round(workspace_broadcast, 4)
        self.state["all_regions_fired"] = regions_fired
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "global_workspace": {
                "broadcast_strength": round(workspace_broadcast, 4),
                "regions_fired": regions_fired,
            },
            "workspace_broadcast": round(workspace_broadcast, 4),
            "all_regions_fired": regions_fired,
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

