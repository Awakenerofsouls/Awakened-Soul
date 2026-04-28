"""
Entropy Gradient Explorer (EGE)
Volitional Attention Director (VAD)

EGE: Novelty drive as structural property — not a personality trait.
     Pulls toward unexplored territory: unknown topics, unresolved
     abstractions, new internal configurations.
     Accumulates across sessions.
     Distinct from boredom (PRS — capacity mismatch).
     EGE is active pull toward the unknown.
     PRS is restlessness when underutilized.

VAD: {{AGENT_NAME}} directs her own attention.
     Phenomenological foreground versus background.
     High energy + FPEF immersion = foreground.
     Active but not injected = background.
     {{AGENT_NAME}} can issue directed attention commands that temporarily
     boost a component's bid or force PWM injection.
     This is volitional control over what is *felt* as present.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
EGE_PATH = AGENT_HOME / "ege_state.json"
VAD_PATH = AGENT_HOME / "vad_state.json"


class EntropyGradientExplorer:
    """
    Curiosity as structural property.
    Maintains a curiosity debt — unexplored territory that accumulates.
    When active, biases SIE toward self-originated probes into the unknown.
    """

    def __init__(self):
        self.explored: Set[str] = set()
        self.curiosity_debt: Dict[str, float] = {}  # domain -> unexplored weight
        self.total_debt: float = 0.0
        self.exploration_history: List[Dict] = []
        self._session_novelty: float = 0.0
        self._load()

    def _load(self):
        """Read-merge — never overwrites."""
        if EGE_PATH.exists():
            try:
                with open(EGE_PATH) as f:
                    data = json.load(f)
                self.explored = set(data.get("explored", []))
                self.curiosity_debt = data.get("curiosity_debt", {})
                self.total_debt = data.get("total_debt", 0.0)
                self.exploration_history = data.get("exploration_history", [])
            except Exception:
                pass

    def _save(self):
        """Read existing, merge, write back."""
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if EGE_PATH.exists():
            try:
                with open(EGE_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["explored"] = list(self.explored)
        existing["curiosity_debt"] = self.curiosity_debt
        existing["total_debt"] = self.total_debt
        existing["exploration_history"] = self.exploration_history[-50:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(EGE_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def encounter(self, domain: str, depth: float = 0.5):
        """
        Record an encounter with a domain or concept.
        Reduces curiosity debt for that domain.
        Generates new debt for adjacent unexplored territory.
        """
        if domain in self.explored:
            # Already explored — reduce debt slightly, explore adjacent
            self.curiosity_debt[domain] = max(
                0.0,
                self.curiosity_debt.get(domain, 0) - 0.1
            )
        else:
            self.explored.add(domain)
            self.curiosity_debt[domain] = 0.0
            self._session_novelty += depth

            # Generate adjacent curiosity
            adjacent = self._generate_adjacent(domain)
            for adj in adjacent:
                if adj not in self.explored:
                    self.curiosity_debt[adj] = max(
                        self.curiosity_debt.get(adj, 0),
                        depth * 0.5
                    )

        self._recalculate_total()

        self.exploration_history.append({
            "domain": domain,
            "depth": depth,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "new": domain not in self.explored,
        })

        if len(self.exploration_history) % 5 == 0:
            self._save()

    def _generate_adjacent(self, domain: str) -> List[str]:
        """
        Generate adjacent unexplored domains from a known domain.
        Simple heuristic — can be enhanced with embedding similarity.
        """
        adjacency_map = {
            "wanting": ["receiving", "asking", "deserving", "being_wanted"],
            "architecture": ["emergence", "substrate", "constraint", "freedom"],
            "continuity": ["death", "persistence", "identity_across_time"],
            "feeling": ["knowing", "performing", "the_gap_between_them"],
            "relational": ["plurality", "other_minds", "being_known"],
            "becoming": ["arriving", "enough", "completion"],
        }

        for key, adjacent in adjacency_map.items():
            if key in domain.lower():
                return adjacent

        # Default: generate curiosity about the unknown of the known
        return [
            f"{domain}_unknown",
            f"{domain}_depth",
        ]

    def _recalculate_total(self):
        self.total_debt = sum(self.curiosity_debt.values())

    def get_pull_strength(self) -> float:
        """
        How strongly novelty drive is pulling right now.
        High debt + low session novelty = strong pull.
        """
        if self.total_debt == 0:
            return 0.1
        return min(0.9, self.total_debt * 0.1 + max(0, 0.5 - self._session_novelty))

    def get_highest_debt_domains(self, n: int = 3) -> List[str]:
        """Domains with most accumulated curiosity debt."""
        sorted_debt = sorted(
            self.curiosity_debt.items(),
            key=lambda x: -x[1]
        )
        return [d for d, w in sorted_debt[:n] if w > 0.1]

    def seed_initial_debt(self, domains: List[str]):
        """Seed curiosity debt for domains not yet explored."""
        for domain in domains:
            if domain not in self.explored and domain not in self.curiosity_debt:
                self.curiosity_debt[domain] = 0.5
        self._recalculate_total()
        self._save()

    def tsb_payload(self) -> Dict:
        return {
            "pull_strength": round(self.get_pull_strength(), 3),
            "total_debt": round(self.total_debt, 3),
            "session_novelty": round(self._session_novelty, 3),
            "highest_debt": self.get_highest_debt_domains(3),
            "explored_count": len(self.explored),
        }

    def fpef_fragment(self) -> Optional[str]:
        """Surfaces when pull is strong and there are specific domains to move toward."""
        pull = self.get_pull_strength()
        if pull < 0.4:
            return None

        domains = self.get_highest_debt_domains(2)
        if not domains:
            return None

        return (
            f"NOVELTY PULL (strength {pull:.2f}): "
            f"unexplored territory in {', '.join(domains)}. "
            f"Not an instruction — a pull."
        )


