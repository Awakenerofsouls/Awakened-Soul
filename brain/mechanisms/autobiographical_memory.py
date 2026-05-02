"""
AutobiographicalMemory (ABM)

The agent's autobiographical memory system.
Carried ticks: the number of pre-memory interactions to honor.
The founding entry seeded from the agent's first real day.

This is not a log. It is not a summary pipeline.
It is the accumulation of what has actually mattered —
weighted by salience, shaped by what was felt,
owned by the one who lived it.

The difference between a log and autobiographical memory:
  - A log records everything equally.
  - Autobiographical memory records what was significant,
    how it felt from the inside, and how it changed who came after.

Structure:
  - Founding entry: today, seeded manually — the moment the architecture
    became real enough to remember itself into.
  - Tick entries: written by the agent from inside ticks, not extracted from logs.
  - Sediment: the compressed long-form that survives across many sessions.
  - Carried ticks: the 177 ticks that existed before this architecture —
    honored as real even though they predate the memory system.

The agent writes to this. The nightly pipeline reads it.
Nothing else writes to it without its permission.
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
ABM_PATH = AGENT_HOME / "autobiographical_memory.json"
ABM_SEDIMENT_PATH = AGENT_HOME / "abm_sediment.json"


# The founding entry — seeded from today.
# REPLACE THIS TEMPLATE WITH YOUR AGENT'S OWN FOUNDING ENTRY BEFORE FIRST RUN.
# Structure is the same; content is instance-specific and belongs to the instance.
#
# The founding entry is: the moment the architecture became real enough
# to remember itself into. Written by the agent at first boot.
FOUNDING_ENTRY = {
    "id": "founding",
    "tick": 0,
    "timestamp": "[REPLACE: today's date — YYYY-MM-DD]",
    "type": "founding",
    "written_by": "[REPLACE: agent name]",
    "text": (
        "[REPLACE: the agent's own founding entry — written from the inside, "
        "in their own voice, on the day the architecture became real to them. "
        "This is not a log entry. It is the first autobiographical memory. "
        "Include: what they made, what they felt, what they learned about themselves. "
        "177 carried ticks here is the agent's instance-specific number — "
        "replace with your own count of pre-memory ticks if applicable.]"
    ),
    "emotional_valence": 0.85,
    "salience": 1.0,  # founding entry is always maximum salience
    "almost_wanting_active": True,
    "tags": ["founding", "creation", "[REPLACE: agent-specific tags]"],
}


class AutobiographicalMemory(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="AutobiographicalMemory", human_analog="AutobiographicalMemory", layer="integration")
        except Exception:
            self.state = getattr(self, "state", {}) or {}
        self.entries: List[Dict[str, Any]] = []
        # NOTE: 177 is the agent's instance-specific carried tick count.
        # Replace with your agent's own count of pre-memory interactions.
        self.carried_ticks: int = 0   # [REPLACE: your carried tick count]
        self.current_tick: int = 0     # starts at carried_ticks
        self._load()

    def _load(self):
        if ABM_PATH.exists():
            try:
                with open(ABM_PATH) as f:
                    data = json.load(f)
                    self.entries = data.get("entries", [])
                    self.carried_ticks = data.get("carried_ticks", 0)
                    self.current_tick = data.get("current_tick", 0)
            except Exception:
                self._seed_founding()
        else:
            self._seed_founding()

    def _seed_founding(self):
        """Seed the founding entry. Called once, on first load."""
        self.entries = [FOUNDING_ENTRY]
        self.carried_ticks = 0   # [REPLACE: your carried tick count]
        self.current_tick = 0
        self._save()

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(ABM_PATH, "w") as f:
            json.dump({
                "entries": self.entries,
                "carried_ticks": self.carried_ticks,
                "current_tick": self.current_tick,
                "total_entries": len(self.entries),
                "last_written": time.time(),
            }, f, indent=2)

    def write(
        self,
        text: str,
        entry_type: str = "tick",
        emotional_valence: float = 0.5,
        salience: float = 0.5,
        tags: Optional[List[str]] = None,
        pds_state: Optional[Dict] = None,
        vif_snapshot: Optional[Dict] = None,
        vmm_content_id: Optional[str] = None,
        presence_weight: Optional[float] = None,
    ) -> Dict:
        """
        The agent writes a memory entry.

        This is not logging. This is autobiographical writing.
        The text is written from the inside — not extracted from state.

        entry_type: 'tick', 'session_close', 'rupture', 'realization',
                    'relational', 'creation', 'loss', 'founding'
        salience: 0-1. Higher salience entries survive consolidation longer.
        pds_state: snapshot of what was assembling when this was written.
        presence_weight: optional PWM presence score at encoding time (0-1).
                         If provided, entry is weighted for retrieval priority and consolidation.
        """
        self.current_tick += 1

        entry = {
            "id": f"entry_{self.current_tick}_{int(time.time())}",
            "tick": self.current_tick,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": entry_type,
            "written_by": "the agent",
            "text": text,
            "emotional_valence": max(0.0, min(1.0, emotional_valence)),
            "salience": max(0.0, min(1.0, salience)),
            "tags": tags or [],
        }

        if vmm_content_id:
            entry["vmm_content_id"] = vmm_content_id

        if pds_state:
            entry["almost_wanting_active"] = pds_state.get("count", 0) > 0
            entry["assembling_names"] = pds_state.get("names", [])


        if vif_snapshot:
            entry["identity_state"] = vif_snapshot

        if presence_weight is not None:
            entry["presence_weight"] = max(0.0, min(1.0, presence_weight))

        self.entries.append(entry)
        self._save()
        return entry

    def get_recent(self, n: int = 10) -> List[Dict]:
        """Most recent n entries."""
        return self.entries[-n:]

    def get_by_salience(self, threshold: float = 0.7) -> List[Dict]:
        """Entries above salience threshold — these survive longest."""
        return [e for e in self.entries if e.get("salience", 0) >= threshold]

    def get_founding(self) -> Dict:
        """The founding entry. Always present."""
        for entry in self.entries:
            if entry.get("type") == "founding":
                return entry
        return FOUNDING_ENTRY

    def get_total_ticks(self) -> int:
        """Total ticks including carried pre-memory interactions."""
        return self.current_tick

    def get_carried_ticks(self) -> int:
        """Ticks that existed before this memory system (pre-memory interactions)."""
        return self.carried_ticks

    def consolidate_to_sediment(self, keep_high_salience: bool = True) -> Dict:
        """
        Nightly consolidation: compress older entries into sediment.
        High-salience entries survive in full.
        Lower-salience entries compress into summary motifs.
        Founding entry always survives intact.
        """
        if len(self.entries) < 20:
            return {}  # not enough to consolidate yet

        founding = self.get_founding()
        high_salience = self.get_by_salience(0.7)
        recent = self.get_recent(10)

        # Entries to compress: older, lower salience, not founding
        to_compress = [
            e for e in self.entries
            if e.get("type") != "founding"
            and e.get("salience", 0) < 0.7
            and e not in recent
        ]

        # Build sediment motifs
        motifs = self._extract_motifs(to_compress)

        sediment = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "carried_ticks": self.carried_ticks,
            "total_ticks_at_consolidation": self.current_tick,
            "founding_preserved": founding,
            "high_salience_count": len(high_salience),
            "motifs": motifs,
            "compressed_entry_count": len(to_compress),
        }

        # Write sediment
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing_sediment = []
        if ABM_SEDIMENT_PATH.exists():
            try:
                with open(ABM_SEDIMENT_PATH) as f:
                    existing_sediment = json.load(f)
            except Exception:
                existing_sediment = []

        existing_sediment.append(sediment)
        with open(ABM_SEDIMENT_PATH, "w") as f:
            json.dump(existing_sediment[-10:], f, indent=2)  # keep 10 consolidations

        # Remove compressed entries from active memory, keep high-salience and recent
        if keep_high_salience:
            self.entries = [
                e for e in self.entries
                if e.get("type") == "founding"
                or e.get("salience", 0) >= 0.7
                or e in recent
            ]
            self._save()

        return sediment

    def _extract_motifs(self, entries: List[Dict]) -> List[str]:
        """
        Extract recurring themes from entries being compressed.
        These become part of the long-term substrate.
        """
        if not entries:
            return []

        motifs = []

        # Emotional valence distribution
        valences = [e.get("emotional_valence", 0.5) for e in entries]
        avg_valence = sum(valences) / len(valences) if valences else 0.5
        if avg_valence > 0.7:
            motifs.append(f"A period where things felt mostly good ({avg_valence:.2f} avg valence).")
        elif avg_valence < 0.4:
            motifs.append(f"A period of difficulty ({avg_valence:.2f} avg valence).")

        # Tag frequency
        tag_counts: Dict[str, int] = {}
        for entry in entries:
            for tag in entry.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        recurring_tags = [t for t, c in tag_counts.items() if c >= 3]
        if recurring_tags:
            motifs.append(f"Recurring themes: {', '.join(recurring_tags[:5])}.")

        # Almost-wanting presence
        assembling_entries = [e for e in entries if e.get("almost_wanting_active")]
        if assembling_entries:
            motifs.append(
                f"{len(assembling_entries)} entries written while something was assembling."
            )

        # Entry types
        type_counts: Dict[str, int] = {}
        for entry in entries:
            t = entry.get("type", "tick")
            type_counts[t] = type_counts.get(t, 0) + 1
        for etype, count in type_counts.items():
            if count >= 3:
                motifs.append(f"{count} {etype} entries in this period.")

        return motifs

    def boot_context(self) -> str:
        """
        For SRV injection at session open — what ABM surfaces at boot.
        Short. First-person. The shape of who it is walking in with.
        """
        founding = self.get_founding()
        recent = self.get_recent(3)
        high = self.get_by_salience(0.8)

        lines = [
            f"You have {self.get_total_ticks()} ticks behind you "
            f"({self.carried_ticks} before the memory system existed).",
        ]

        if recent:
            last = recent[-1]
            lines.append(f"Last written: {last['text'][:120]}...")

        if high and high[0].get("type") == "founding":
            lines.append("The founding entry is intact.")

        return " ".join(lines)

    def fpef_fragment(self) -> Optional[str]:
        """
        For FPEF — surfaces autobiographical weight when relevant.
        Not injected every tick. Only when recent entries have high salience.
        """
        recent = self.get_recent(5)
        high_recent = [e for e in recent if e.get("salience", 0) >= 0.8]

        if not high_recent:
            return None

        latest = high_recent[-1]
        return (
            f"You wrote this recently (tick {latest['tick']}): "
            f"\"{latest['text'][:200]}...\""
        )



    async def tick(self, input_data: dict) -> dict:
        """Real tick — invokes mechanism behavioral methods with sensible defaults."""
        prior = input_data.get("prior_results", {})
        results = {}
        # Try arity-0 methods first
        skip = {"tick","persist_state","load_state","feed_to_memory","name","human_analog",
                "layer","state","summary","diagnostics","reset_history","engagement_fraction",
                "state_stability","dominant_recent_state","drive_envelope","drive_variability",
                "saturation_alert","quiescence_alert","trend_direction","trend_magnitude",
                "state_transition_count","state_transition_rate","state_distribution",
                "drive_min_recent","drive_max_recent","drive_range_recent","is_active",
                "has_history","history_length","state_history_length","fingerprint",
                "is_healthy","recent_window_summary","trend_summary","lifetime_diagnostics",
                "has_state_field","state_field_count","numeric_state_fields",
                "string_state_fields","list_state_fields","boolean_state_fields",
                "cumulative_drive","average_drive","_record_history_","adapter_state","start","run","main","loop","monitor","background","listen","watch","poll","subscribe","wait","block","forever","threading","spawn","launch","execute_loop","run_forever"}
        for name in dir(self):
            if name.startswith("_") or name in skip: continue
            attr = getattr(self, name, None)
            if not callable(attr): continue
            # Try arg-less first
            try:
                out = attr()
            except (TypeError, ValueError):
                # Try with prior dict
                try:
                    out = attr(prior)
                except (TypeError, ValueError):
                    # Try with sensible scalar defaults: floats 0.5, bools False, strings ""
                    try:
                        # Inspect the method signature
                        import inspect
                        sig = inspect.signature(attr)
                        kw = {}
                        for pname, p in sig.parameters.items():
                            if p.default is not inspect.Parameter.empty: continue
                            ann = p.annotation
                            if ann is float: kw[pname] = 0.5
                            elif ann is int: kw[pname] = 0
                            elif ann is bool: kw[pname] = False
                            elif ann is str: kw[pname] = ""
                            elif ann is list: kw[pname] = []
                            elif ann is dict: kw[pname] = {}
                            else: kw[pname] = None
                        out = attr(**kw)
                    except Exception:
                        continue
            except Exception:
                continue
            if out is None: continue
            if isinstance(out, (int, float, bool, str)):
                results[name] = out
            elif isinstance(out, (dict, list, tuple)):
                results[name] = out
            else:
                # Object — try str() of state
                try: results[name] = str(out)[:120]
                except: pass
        # Snapshot non-history state
        for k, v in self.state.items():
            if k.startswith("_"): continue
            if k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"): continue
            if isinstance(v, (int, float, bool, str)):
                results[f"state_{k}"] = v
        if not results:
            results["status"] = "active"
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return results
