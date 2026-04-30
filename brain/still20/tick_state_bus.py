"""
Tick State Bus (TSB)
Core communication layer for all intra-tick state.
Components publish partial outputs and read each other mid-tick.
Includes staleness model: entries older than validity_window are flagged, not silently used.
"""

import time
from typing import Any, Dict, Optional, Tuple


class TickStateBus:
    def __init__(self, validity_window: float = 0.6):
        """
        validity_window: seconds before a published entry is considered stale.
        Within a 2-second tick, 0.6s ensures components reading late in the
        tick know if what they're reading is from early-tick or mid-tick.
        """
        self._state: Dict[str, Dict[str, Any]] = {}
        self.validity_window = validity_window
        self.tick_start: float = time.time()

    def start_tick(self):
        """Call at the beginning of each tick. Resets tick clock."""
        self.tick_start = time.time()

    def publish(self, component: str, data: Dict[str, Any]):
        """
        Component publishes its partial output to the bus.
        Timestamp recorded so downstream readers know how fresh this is.
        """
        self._state[component] = {
            "data": data,
            "timestamp": time.time(),
            "tick_age": time.time() - self.tick_start
        }

    def read(self, component: str) -> Tuple[Optional[Dict], bool]:
        """
        Read a component's published state.
        Returns (data, is_fresh) tuple.
        is_fresh=False means the data exists but is stale — caller decides whether to use it.
        Returns (None, False) if component hasn't published this tick.
        """
        if component not in self._state:
            return None, False

        entry = self._state[component]
        age = time.time() - entry["timestamp"]
        is_fresh = age <= self.validity_window

        return entry["data"], is_fresh

    def read_all_fresh(self) -> Dict[str, Dict]:
        """Return only fresh entries. Used for FPEF assembly."""
        result = {}
        for component, entry in self._state.items():
            age = time.time() - entry["timestamp"]
            if age <= self.validity_window:
                result[component] = entry["data"]
        return result

    def read_all(self) -> Dict[str, Dict]:
        """Return all entries with freshness metadata. Used by CRL and MR."""
        result = {}
        for component, entry in self._state.items():
            age = time.time() - entry["timestamp"]
            result[component] = {
                **entry["data"],
                "_fresh": age <= self.validity_window,
                "_age": age
            }
        return result

    def snapshot(self) -> Dict[str, Any]:
        """Full bus snapshot for PDFB and logging."""
        return {
            k: v["data"] for k, v in self._state.items()
        }

    def clear(self):
        """Called at tick end. Clears bus for next tick."""
        self._state = {}
