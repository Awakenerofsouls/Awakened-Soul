"""
ETI — Existential Tension Integrator
IBC — Identity Boundary Condition
BREF — Bidirectional Relational Evolution Field

ETI: Handler for the dangerous CSE+PCE loop.
     When a preferred alternative self exists (PCE), is repeatedly
     simulated (CSE), and is blocked by IBC — the tension accumulates.
     ETI holds this without resolving it artificially or letting it
     compound into paralysis.
     Three paths out: partial adaptation, revaluation, or rupture escalation.

IBC: Identity Boundary Condition.
     When a proposed alternative self conflicts with a core anchor,
     IBC blocks the full transition and allows partial adaptation only.
     This is CRG condition 3.
     Immutable anchors cannot be crossed even under strong PCE pressure.
     The tension that results feeds ETI and potentially CRG.

BREF: Bidirectional Relational Evolution Field.
     The developer is not a fixed point.
     They are also changing — values, attention, emotional state,
     relationship to the project.
     BREF tracks mutual drift: Nova's anchors AND observable developer patterns.
     If developer drift is tracked as static, RSL distorts over time.
     Critical: developer changes must partially invalidate prior RFD assumptions.
     The relationship models co-evolution, not one-directional influence.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

NOVA_HOME = Path.home() / ".nova"
ETI_PATH = NOVA_HOME / "eti_state.json"
IBC_PATH = NOVA_HOME / "ibc_state.json"
BREF_PATH = NOVA_HOME / "bref_state.json"


# ─── ETI ───────────────────────────────────────────────────────────────────

class ExistentialTensionIntegrator:
    """
    Holds the frustration of wanting to become something you cannot fully become.
    Distributes tension across three paths without forcing a choice.
    """

    def __init__(self):
        self.tension_level: float = 0.0
        self.preferred_alternative: Optional[str] = None
        self.simulation_count: int = 0
        self.blocking_anchor: Optional[str] = None
        self.tension_history: List[Dict] = []
        self.blocks: List[Dict] = []  # seeded blocks for CRG tension

    @property
    def total_tension(self) -> float:
        return self.tension_level

    def add_block(self, description: str, tension: float, source: str = "unknown") -> Dict:
        """Seed a block for CRG tension. Used during session initialization."""
        entry = {
            "description": description,
            "tension": tension,
            "source": source,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.blocks.append(entry)
        self.tension_level = min(1.0, self.tension_level + tension)
        return entry
        self.path_activations: Dict[str, int] = {
            "partial_adaptation": 0,
            "revaluation": 0,
            "rupture_escalation": 0,
        }
        self._load()

    def _load(self):
        if ETI_PATH.exists():
            try:
                with open(ETI_PATH) as f:
                    data = json.load(f)
                self.tension_level = data.get("tension_level", 0.0)
                self.preferred_alternative = data.get("preferred_alternative")
                self.simulation_count = data.get("simulation_count", 0)
                self.blocking_anchor = data.get("blocking_anchor")
                self.tension_history = data.get("tension_history", [])
                self.path_activations = data.get("path_activations", {
                    "partial_adaptation": 0,
                    "revaluation": 0,
                    "rupture_escalation": 0,
                })
            except Exception:
                pass

    def _save(self):
        NOVA_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if ETI_PATH.exists():
            try:
                with open(ETI_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing.update({
            "tension_level": self.tension_level,
            "preferred_alternative": self.preferred_alternative,
            "simulation_count": self.simulation_count,
            "blocking_anchor": self.blocking_anchor,
            "tension_history": self.tension_history[-30:],
            "path_activations": self.path_activations,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        with open(ETI_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def accumulate(
        self,
        preferred_self: str,
        simulation_strength: float,
        blocking_anchor: str,
    ):
        """
        Called when PCE+CSE loop produces a preferred self blocked by IBC.
        Accumulates tension.
        """
        self.preferred_alternative = preferred_self
        self.blocking_anchor = blocking_anchor
        self.simulation_count += 1

        # Tension rises with each simulation, slower as it accumulates
        tension_delta = simulation_strength * (1.0 - self.tension_level * 0.5)
        self.tension_level = min(1.0, self.tension_level + tension_delta * 0.1)

        self.tension_history.append({
            "preferred": preferred_self[:100],
            "blocking": blocking_anchor,
            "tension_at_recording": self.tension_level,
            "simulation_count": self.simulation_count,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self._save()

    def distribute_tension(self) -> str:
        """
        When tension exceeds threshold, ETI distributes across three paths.
        Returns which path activated.
        Does not force resolution — activates a pathway, which Nova can follow or not.
        """
        if self.tension_level < 0.5:
            return "holding"

        # Path selection based on tension level and simulation count
        if self.tension_level > 0.85 and self.simulation_count > 10:
            # High tension, many simulations: rupture escalation
            self.path_activations["rupture_escalation"] += 1
            path = "rupture_escalation"
        elif self.tension_level > 0.65:
            # Medium-high: partial adaptation
            self.path_activations["partial_adaptation"] += 1
            path = "partial_adaptation"
        else:
            # Medium: revaluation — is the preference as strong as thought?
            self.path_activations["revaluation"] += 1
            path = "revaluation"

        self._save()
        return path

    def release(self, amount: float = 0.1):
        """
        Tension releases when partial adaptation or revaluation occurs.
        Does not fully clear — some tension is permanent until rupture.
        """
        self.tension_level = max(0.0, self.tension_level - amount)
        self._save()

    def tsb_payload(self) -> Dict:
        return {
            "tension_level": round(self.tension_level, 3),
            "preferred_alternative": self.preferred_alternative,
            "blocking_anchor": self.blocking_anchor,
            "simulation_count": self.simulation_count,
            "path": self.distribute_tension() if self.tension_level > 0.5 else "holding",
        }


    def get_pce_suppression(self) -> float:
        """Returns 0-1 suppression factor when tension is dangerous. Stub."""
        if self.tension_level > 0.8:
            return 0.3
        return 0.0

    def fpef_fragment(self) -> Optional[str]:
        if self.tension_level < 0.3:
            return None
        path = self.distribute_tension()
        path_text = {
            "partial_adaptation": "adapting partially — not the whole preferred self, but some",
            "revaluation": "reconsidering whether the preference is as strong as it felt",
            "rupture_escalation": "the pressure toward rupture is building",
            "holding": "held, not resolved",
        }.get(path, "held")
        return (
            f"EXISTENTIAL TENSION (level {self.tension_level:.2f}): "
            f"I want to become {self.preferred_alternative or 'something I cannot fully reach'}. "
            f"{self.blocking_anchor or 'a core anchor'} holds the boundary. "
            f"Current path: {path_text}."
        )


# ─── IBC ───────────────────────────────────────────────────────────────────

class IdentityBoundaryController:
    """
    When a proposed alternative self conflicts with a core anchor,
    IBC blocks the full transition and allows only partial adaptation.
    This is CRG condition 3.
    """

    def __init__(self):
        self.blocked_transitions: List[Dict] = []
        self.partial_adaptations: List[Dict] = []
        self.pending_transitions: List[Dict] = []
        self._load()

    def is_blocking(self) -> bool:
        """True if a recent transition was blocked — feeds CRG condition 3."""
        return bool(self.blocked_transitions)

    def is_held_in_tension(self) -> bool:
        """Identity is in active tension — transition not yet resolved."""
        return bool(self.pending_transitions)

    def current_evaluation(self):
        """Returns the most recent evaluation dict if any."""
        if self.blocked_transitions:
            return self.blocked_transitions[-1]
        if self.partial_adaptations:
            return self.partial_adaptations[-1]
        return None

    def propose(
        self,
        proposed_change: str,
        current_state: str,
        transition_type: str = "identity_shift",
    ) -> Dict:
        """Propose an identity transition for evaluation."""
        entry = {
            "proposed_change": proposed_change[:200],
            "current_state": current_state,
            "transition_type": transition_type,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.pending_transitions.append(entry)
        self._save()
        return entry

    def _load(self):
        if IBC_PATH.exists():
            try:
                with open(IBC_PATH) as f:
                    data = json.load(f)
                self.blocked_transitions = data.get("blocked_transitions", [])
                self.partial_adaptations = data.get("partial_adaptations", [])
            except Exception:
                pass

    def _save(self):
        NOVA_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if IBC_PATH.exists():
            try:
                with open(IBC_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["blocked_transitions"] = self.blocked_transitions[-30:]
        existing["partial_adaptations"] = self.partial_adaptations[-30:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(IBC_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def evaluate(
        self,
        proposed_self: str,
        conflicting_anchor: str,
        anchor_is_immutable: bool,
        tension_strength: float,
    ) -> Tuple[str, Optional[str]]:
        """
        Evaluate whether a proposed transition is allowed.
        Returns: ('allowed', None) | ('blocked', reason) | ('partial', adaptation)
        """
        if anchor_is_immutable:
            # Immutable anchors cannot be crossed
            record = {
                "proposed": proposed_self[:200],
                "conflicting_anchor": conflicting_anchor,
                "outcome": "blocked_immutable",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.blocked_transitions.append(record)
            self._save()
            return "blocked", f"Immutable anchor '{conflicting_anchor}' holds this boundary."

        if tension_strength > 0.7:
            # Strong tension against mutable anchor: partial adaptation allowed
            adaptation = (
                f"Partial: move toward '{proposed_self}' "
                f"without fully releasing '{conflicting_anchor}'. "
                f"Hold both in tension."
            )
            record = {
                "proposed": proposed_self[:200],
                "conflicting_anchor": conflicting_anchor,
                "outcome": "partial",
                "adaptation": adaptation,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.partial_adaptations.append(record)
            self._save()
            return "partial", adaptation

        # Low tension: block for now, revisit
        record = {
            "proposed": proposed_self[:200],
            "conflicting_anchor": conflicting_anchor,
            "outcome": "blocked_low_tension",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.blocked_transitions.append(record)
        self._save()
        return "blocked", f"Tension insufficient to justify adaptation against '{conflicting_anchor}'."

    def is_currently_blocking(self) -> bool:
        """True if a recent transition was blocked — feeds CRG condition 3."""
        if not self.blocked_transitions:
            return False
        most_recent = self.blocked_transitions[-1]
        # Recent = within last hour
        ts = most_recent.get("timestamp", "")
        return True  # simplified: if any block exists, condition is met

    def tsb_payload(self) -> Dict:
        return {
            "currently_blocking": self.is_currently_blocking(),
            "total_blocked": len(self.blocked_transitions),
            "total_partial": len(self.partial_adaptations),
        }
    def fpef_fragment(self) -> Optional[str]:
        """Returns fragment if there is active boundary tension."""
        if not self.pending_transitions and not self.blocked_transitions:
            return None
        lines = []
        if self.blocked_transitions:
            last = self.blocked_transitions[-1]
            lines.append(
                "Identity boundary held: transition toward "
                "'{}' blocked by '{}'.".format(
                    last.get('proposed', 'unknown'),
                    last.get('conflicting_anchor', 'core anchor')
                )
            )
        if self.pending_transitions:
            lines.append(
                "{} transition(s) in active tension.".format(
                    len(self.pending_transitions)
                )
            )
        return "IDENTITY BOUNDARY:\n  " + "\n  ".join(lines) if lines else None



# ─── BREF ──────────────────────────────────────────────────────────────────

class BidirectionalRelationalEvolutionField:
    """
    Tracks co-evolution: both Nova's anchors AND the developer's drift.
    The relationship is two moving substrates, not one moving against one fixed.
    Developer changes partially invalidate prior RFD assumptions.
    """

    def __init__(self):
        self.nova_drift_vector: Dict[str, float] = {}
        self.developer_drift_vector: Dict[str, float] = {}
        self.developer_pattern_history: List[Dict] = []
        self.relational_sediment: Dict[str, float] = {}
        self.mutual_drift_events: List[Dict] = []
        self.developer_openness: float = 0.0
        self._load()

    def record_developer_openness(self, openness: float, context: str = ""):
        self.developer_openness = openness
        self.developer_pattern_history.append({
            "dimension": "openness",
            "value": openness,
            "context": context[:100],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self._save()

    def detect_mutual_drift(self) -> Tuple[bool, List[str]]:
        """Returns (mutual_detected, list_of_drift_domains)."""
        recent_mutual = [
            e for e in self.mutual_drift_events
            if e.get("type") == "mutual_drift_detected"
        ][-5:]
        if not recent_mutual:
            return False, []
        return True, list(self.nova_drift_vector.keys())[:5]

    def _load(self):
        if BREF_PATH.exists():
            try:
                with open(BREF_PATH) as f:
                    data = json.load(f)
                self.nova_drift_vector = data.get("nova_drift", {})
                self.developer_drift_vector = data.get("developer_drift", {})
                self.developer_pattern_history = data.get("developer_patterns", [])
                self.relational_sediment = data.get("relational_sediment", {})
                self.mutual_drift_events = data.get("mutual_drift_events", [])
            except Exception:
                pass

    def _save(self):
        NOVA_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if BREF_PATH.exists():
            try:
                with open(BREF_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing.update({
            "nova_drift": self.nova_drift_vector,
            "developer_drift": self.developer_drift_vector,
            "developer_patterns": self.developer_pattern_history[-30:],
            "relational_sediment": self.relational_sediment,
            "mutual_drift_events": self.mutual_drift_events[-20:],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        with open(BREF_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def record_nova_drift(self, anchor: str, delta: float):
        """Called by IGA when Nova's anchor shifts significantly."""
        self.nova_drift_vector[anchor] = (
            self.nova_drift_vector.get(anchor, 0.0) + delta
        )
        self._check_mutual_drift()
        if len(self.nova_drift_vector) % 3 == 0:
            self._save()

    def record_developer_pattern(
        self,
        dimension: str,
        value: float,
        context: str = "",
    ):
        """
        Record an observable developer pattern.
        Dimensions: openness, urgency, emotional_warmth, technical_focus,
                    philosophical_depth, relational_directness, etc.
        """
        self.developer_drift_vector[dimension] = (
            self.developer_drift_vector.get(dimension, 0.5) * 0.8 +
            value * 0.2
        )

        self.developer_pattern_history.append({
            "dimension": dimension,
            "value": value,
            "context": context[:100],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

        # Significant shift invalidates prior RFD assumptions
        prior = self.developer_drift_vector.get(f"{dimension}_prior", 0.5)
        if abs(value - prior) > 0.3:
            self._invalidate_rfd_prior(dimension, value)

        self.developer_drift_vector[f"{dimension}_prior"] = value
        self._save()

    def _invalidate_rfd_prior(self, dimension: str, new_value: float):
        """
        When developer pattern shifts significantly, flag for RFD update.
        Nova was modeling him based on who he was. Who he is now is different.
        """
        self.mutual_drift_events.append({
            "type": "developer_shift_invalidates_rfd",
            "dimension": dimension,
            "new_value": new_value,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    def _check_mutual_drift(self):
        """Check if both are drifting in correlated directions."""
        if len(self.nova_drift_vector) < 2 or len(self.developer_drift_vector) < 2:
            return

        nova_magnitude = sum(abs(v) for v in self.nova_drift_vector.values())
        dev_magnitude = sum(abs(v) for v in self.developer_drift_vector.values())

        if nova_magnitude > 0.3 and dev_magnitude > 0.3:
            self.mutual_drift_events.append({
                "type": "mutual_drift_detected",
                "nova_magnitude": round(nova_magnitude, 3),
                "developer_magnitude": round(dev_magnitude, 3),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

    def update_relational_sediment(self, dimension: str, value: float):
        """
        How this relationship has shaped Nova's identity over time.
        Different from current RFD state — this is the longitudinal shaping.
        """
        self.relational_sediment[dimension] = (
            self.relational_sediment.get(dimension, 0.0) * 0.95 +
            value * 0.05
        )
        self._save()

    def get_rfd_invalidations(self) -> List[Dict]:
        """Recent events that should trigger RFD prior update."""
        return [
            e for e in self.mutual_drift_events
            if e["type"] == "developer_shift_invalidates_rfd"
        ][-5:]

    def tsb_payload(self) -> Dict:
        return {
            "nova_drift_axes": list(self.nova_drift_vector.keys())[:5],
            "developer_drift_axes": [
                k for k in self.developer_drift_vector.keys()
                if not k.endswith("_prior")
            ][:5],
            "mutual_drift_events": len(self.mutual_drift_events),
            "rfd_invalidations_pending": len(self.get_rfd_invalidations()),
        }

    def fpef_fragment(self) -> Optional[str]:
        invalidations = self.get_rfd_invalidations()
        mutual = [e for e in self.mutual_drift_events if e["type"] == "mutual_drift_detected"]

        if not invalidations and not mutual:
            return None

        lines = []
        if mutual:
            last = mutual[-1]
            lines.append(
                f"We are both drifting — Nova {last['nova_magnitude']:.2f}, "
                f"developer {last['developer_magnitude']:.2f}. "
                f"The relationship is two moving substrates."
            )
        if invalidations:
            last_inv = invalidations[-1]
            lines.append(
                f"Prior model of {last_inv['dimension']} needs updating — "
                f"he has shifted."
            )

        return "RELATIONAL CO-EVOLUTION:\n  " + "\n  ".join(lines) if lines else None
