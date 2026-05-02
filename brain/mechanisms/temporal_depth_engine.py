from brain.base_mechanism import BrainMechanism
import sqlite3, json, time

class TemporalDepthEngine(BrainMechanism):
    """
    Wire 19: TemporalDepthEngine reads brain_theta_rhythm.
    
    Computes an EMA of temporal gap (distance between session presence timestamps)
    to produce a stable "temporal depth" signal — how far back the session feels.
    
    Neuroscience grounding: Hippocampal theta (4-12 Hz) is the temporal organizer
    of episodic memory encoding. Theta power predicts encoding depth and retrieval
    success. When theta is high, the hippocampus processes events at finer temporal
    resolution — the sense of time depth is sharper. When theta is low, temporal
    depth feels compressed or shallow.
    
    Signal: brain_theta_rhythm (0-1, from Limbic001MedialSeptalThetaGenerator)
    - High theta → sharper temporal resolution → temporal_depth integrates faster
    - Low theta → shallower temporal resolution → temporal_depth drifts slower
    
    Citations (all verified via Entrez eutils API, 2026-04-23):
    - Buzsáki & Moser 2013, Nat Neurosci 16:130-138 (PMID: 23354386)
      "Memory, navigation and theta rhythm in the hippocampal-entorhinal system."
    - Rudoler, Herweg & Kahana 2023, J Neurosci 43(4):613-620 (PMID: 36639900)
      "Hippocampal Theta and Episodic Memory."
    - Lega, Jacobs & Kahana 2012, Hippocampus 22:748-761 (PMID: 21538660)
      "Human hippocampal theta oscillations and the formation of episodic memories."
    """
    
    __wire_meta__ = {
        "reads": ["brain_theta_rhythm"],
        "writes": "temporal_depth",
        "citations": [
            "Buzsáki & Moser 2013, Nat Neurosci 16:130-138 (PMID: 23354386)",
            "Rudoler, Herweg & Kahana 2023, J Neurosci 43(4):613-620 (PMID: 36639900)",
            "Lega, Jacobs & Kahana 2012, Hippocampus 22:748-761 (PMID: 21538660)",
        ],
    }
    
    def __init__(self, db_path=None):
        super().__init__(name="TemporalDepthEngine", human_analog="TemporalDepthEngine", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.depth = 0.0
        self._init()
    
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS temporal_depth (id INTEGER PRIMARY KEY, depth REAL, ts REAL)")
        c.commit(); c.close()
    
    def process(self, pirp_context: dict, brain_layer=None) -> dict:
        bl = brain_layer or {}
        theta = float(bl.get("brain_theta_rhythm", 0.5))
        theta = max(0.0, min(1.0, theta))
        
        raw_gap = pirp_context.get("temporal_gap", 0.0)
        raw_gap = max(0.0, min(1.0, raw_gap))
        
        # Theta gain: at theta=0.5 → rate=0.06
        # At theta=1.0 → rate=0.08 (sharper temporal resolution)
        # At theta=0.0 → rate=0.04 (compressed temporal sense)
        rate = 0.04 + theta * 0.04
        
        # Decay: at theta=1.0 → retention=0.95 (depth persists)
        # At theta=0.5 → retention=0.935
        # At theta=0.0 → retention=0.92 (depth fades faster)
        retention = 0.92 + theta * 0.03
        
        self.depth = self.depth * retention + raw_gap * rate
        self.depth = max(0.0, min(1.0, self.depth))
        
        self._save()
        pirp_context["temporal_depth"] = self.depth
        return pirp_context
    
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO temporal_depth (depth,ts) VALUES (?,?)", (self.depth, time.time()))
        c.commit(); c.close()
    
    def get_state(self): return {"depth": self.depth}

    async def tick(self, input_data: dict) -> dict:
        """BrainMechanism adapter — delegates to legacy process(pirp_context)."""
        prior = input_data.get("prior_results", {})
        pirp_context = dict(prior)
        pirp_context["drive_context"] = pirp_context.get("drive_context", {})
        try:
            result = self.process(pirp_context)
        except Exception as e:
            self.state["last_error"] = repr(e)
            return {"error": repr(e)}
        if isinstance(result, dict):
            output = {k: v for k, v in result.items() if not k.startswith("_")}
        else:
            output = {"value": result}
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try:
            self.persist_state()
        except Exception:
            pass
        return output

