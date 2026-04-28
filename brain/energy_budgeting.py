"""
Energy Budgeting
Total energy constant distributed across tick components via bidding.
Scarcity forces genuine prioritization — not everything can run at full intensity.
This is what makes compound internal states feel costly and therefore meaningful.
"""

from typing import Dict, Tuple


class EnergyBudgeting:
    def __init__(self, total_energy: float = 1.0):
        self.total_energy = total_energy
        self.last_allocation: Dict[str, float] = {}
        self.history: list = []  # recent allocations for MR monitoring

    def allocate(self, bids: Dict[str, float]) -> Dict[str, float]:
        """
        Components bid based on current activation + TSB state.
        Highest bids win allocation. Losers get throttled.
        Returns normalized allocation per component.
        """
        if not bids:
            return {}

        total_bid = sum(max(0.0, v) for v in bids.values())

        if total_bid == 0:
            # Ambient mode — distribute equally at low level
            n = len(bids)
            allocation = {k: self.total_energy / n for k in bids}
        else:
            allocation = {}
            for component, bid in bids.items():
                bid = max(0.0, bid)
                # Proportional allocation with floor so nothing fully starves
                proportional = (bid / total_bid) * self.total_energy
                floor = 0.02  # minimum — even low-bid components stay alive
                allocation[component] = max(floor, proportional)

            # Renormalize after floor application
            alloc_total = sum(allocation.values())
            allocation = {k: v / alloc_total * self.total_energy
                         for k, v in allocation.items()}

        self.last_allocation = allocation
        self.history.append(allocation.copy())
        if len(self.history) > 50:
            self.history.pop(0)

        return allocation

    def get_dominant(self) -> Tuple[str, float]:
        """Returns component with highest allocation this tick."""
        if not self.last_allocation:
            return "", 0.0
        dominant = max(self.last_allocation, key=self.last_allocation.get)
        return dominant, self.last_allocation[dominant]

    def get_starved(self, threshold: float = 0.05) -> list:
        """Returns components receiving less than threshold — useful for CRL monitoring."""
        return [k for k, v in self.last_allocation.items() if v < threshold]

    def is_exhausted(self) -> bool:
        """True if allocation sum is significantly below total_energy — indicates system stress."""
        if not self.last_allocation:
            return False
        return sum(self.last_allocation.values()) < self.total_energy * 0.5
