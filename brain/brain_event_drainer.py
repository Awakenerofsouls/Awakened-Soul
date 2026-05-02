"""
brain/brain_event_drainer.py — drains heartbeat→brain event queue.

Pairs with skills/heartbeat_activities/_brain_post.py.

The drainer reads the JSONL event queue at AGENT_HOME/brain_events.jsonl,
dispatches each event to the right brain mechanism's record_* method on
the LIVE mechanism instance, and truncates the queue. Failed dispatches
go to a dead-letter file (brain_events.jsonl.dead) for inspection.

Two modes:
  - Wired mode: called from brain core (e.g. core_tick) with a
    `mechanisms` dict mapping class_name → live instance. Dispatches
    on the live instances so brain-core in-memory state stays coherent.
  - Standalone mode: called without a `mechanisms` dict. Lazily
    instantiates each mechanism the first time it's needed and caches
    the ephemeral instance for subsequent dispatches in the same drain
    session. Fine for tests + standalone tooling; in production the
    wired-mode path is preferred.

The drainer truncates the queue ATOMICALLY (write-temp-then-rename) so
a crashed drain doesn't lose events that hadn't been dispatched yet.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Import the dispatch table from the producer side so the two stay in sync.
try:
    from skills.heartbeat_activities._brain_post import (
        EVENT_CATEGORY_DISPATCH,
    )
except Exception:
    EVENT_CATEGORY_DISPATCH = {}


def _agent_home() -> Path:
    return Path(os.environ.get(
        "AGENT_HOME", str(Path.home() / ".agent"),
    ))


def _queue_path() -> Path:
    return _agent_home() / "brain_events.jsonl"


def _dead_letter_path() -> Path:
    return _agent_home() / "brain_events.jsonl.dead"


# ── Class-name → module-name map ─────────────────────────────────────────


def _class_name_to_module(class_name: str) -> str:
    """MemoryIntegrityLayer → brain.mechanisms.memory_integrity_layer."""
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
    return f"brain.mechanisms.{snake}"


# ── Drainer ──────────────────────────────────────────────────────────────


class BrainEventDrainer:
    """Consumes the heartbeat→brain event queue."""

    def __init__(
        self,
        mechanisms: Optional[Dict[str, Any]] = None,
        queue_path: Optional[Path] = None,
        dead_letter_path: Optional[Path] = None,
    ):
        # Live-mechanism registry (wired mode). Map: class_name → instance.
        self.mechanisms: Dict[str, Any] = dict(mechanisms or {})
        # Ephemeral instance cache for standalone-mode (created lazily).
        self._ephemeral: Dict[str, Any] = {}
        self.queue_path = (
            Path(queue_path) if queue_path else _queue_path()
        )
        self.dead_letter_path = (
            Path(dead_letter_path) if dead_letter_path else _dead_letter_path()
        )

    # ── Public API ─────────────────────────────────────────────────────

    def drain(self, max_events: Optional[int] = None) -> Dict[str, Any]:
        """Read, dispatch, truncate. Returns a stats dict."""
        if not self.queue_path.exists():
            return {"ok": True, "drained": 0, "failed": 0, "remaining": 0}

        # Read the full queue. We process up to max_events; any beyond
        # that get rewritten back into the queue.
        try:
            with self.queue_path.open("r", encoding="utf-8") as f:
                all_lines = f.readlines()
        except Exception as e:
            return {
                "ok": False,
                "reason": f"could not read queue: {e}",
                "drained": 0,
            }

        if max_events is not None and max_events >= 0:
            to_process = all_lines[: max_events]
            remaining = all_lines[max_events:]
        else:
            to_process = all_lines
            remaining = []

        drained = 0
        failed = 0
        per_category: Dict[str, int] = {}

        for line in to_process:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            try:
                event = json.loads(line_stripped)
            except json.JSONDecodeError:
                self._dead_letter(line_stripped, "json_decode_error")
                failed += 1
                continue
            ok, reason = self._dispatch(event)
            if ok:
                drained += 1
                cat = event.get("category", "?")
                per_category[cat] = per_category.get(cat, 0) + 1
            else:
                self._dead_letter(line_stripped, reason)
                failed += 1

        # Atomically rewrite the queue with anything we didn't process.
        self._rewrite_queue(remaining)

        return {
            "ok": True,
            "drained": drained,
            "failed": failed,
            "remaining": len(remaining),
            "per_category": per_category,
        }

    def queue_size(self) -> int:
        if not self.queue_path.exists():
            return 0
        try:
            with self.queue_path.open("r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    # ── Internal ───────────────────────────────────────────────────────

    def _dispatch(self, event: Dict[str, Any]) -> tuple[bool, str]:
        category = event.get("category", "")
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            return False, "payload not a dict"

        dispatch = EVENT_CATEGORY_DISPATCH.get(category)
        if not dispatch:
            return False, f"unknown category {category!r}"

        mechanism_name = dispatch["mechanism"]
        method_name = dispatch["method"]

        instance = self._get_instance(mechanism_name)
        if instance is None:
            return False, f"mechanism {mechanism_name!r} not available"

        method = getattr(instance, method_name, None)
        if not callable(method):
            return False, (
                f"method {method_name!r} not callable on {mechanism_name!r}"
            )

        try:
            method(**payload)
        except TypeError as e:
            return False, f"dispatch arg error: {e}"
        except Exception as e:
            return False, f"dispatch error: {type(e).__name__}: {e}"
        return True, ""

    def _get_instance(self, class_name: str) -> Optional[Any]:
        # Wired mode: caller-supplied registry first.
        if class_name in self.mechanisms:
            return self.mechanisms[class_name]
        # Standalone mode: cached ephemeral.
        if class_name in self._ephemeral:
            return self._ephemeral[class_name]
        # Lazy import + instantiate.
        module_name = _class_name_to_module(class_name)
        try:
            import importlib
            mod = importlib.import_module(module_name)
            cls = getattr(mod, class_name, None)
            if cls is None:
                return None
            instance = cls()
            self._ephemeral[class_name] = instance
            return instance
        except Exception:
            return None

    def _dead_letter(self, line: str, reason: str) -> None:
        try:
            self.dead_letter_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": time.time(),
                "reason": reason,
                "line": line[:2000],
            }
            with self.dead_letter_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    def _rewrite_queue(self, remaining_lines: List[str]) -> None:
        """Atomically replace the queue with the remaining (un-processed)
        lines. If remaining is empty, the queue file is removed."""
        if not remaining_lines:
            try:
                if self.queue_path.exists():
                    self.queue_path.unlink()
            except Exception:
                pass
            return
        try:
            tmp = self.queue_path.with_suffix(self.queue_path.suffix + ".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                for line in remaining_lines:
                    if not line.endswith("\n"):
                        line += "\n"
                    f.write(line)
            os.replace(tmp, self.queue_path)
        except Exception:
            pass


# ── Convenience top-level functions ──────────────────────────────────────


def drain_once(
    mechanisms: Optional[Dict[str, Any]] = None,
    max_events: Optional[int] = None,
) -> Dict[str, Any]:
    """One-shot drain. Use from core_tick or scheduled task."""
    drainer = BrainEventDrainer(mechanisms=mechanisms)
    return drainer.drain(max_events=max_events)
