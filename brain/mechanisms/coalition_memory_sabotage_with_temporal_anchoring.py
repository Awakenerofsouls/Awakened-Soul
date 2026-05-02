from brain.base_mechanism import BrainMechanism
import sqlite3, json, time, random

class CoalitionMemorySabotageWithTemporalAnchoring(BrainMechanism):
    """
    Cross-layer mechanism combining coalition memory sabotage with temporal anchoring.
    Tracks sabotage_anchoring_events.
    process() combines sabotage patterns with temporal anchoring.
    """
    def __init__(self, db_path=None):
        super().__init__(name="CoalitionMemorySabotageWithTemporalAnchoring", human_analog="CoalitionMemorySabotageWithTemporalAnchoring", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.sabotage = 0.0
        self.anchor = 0.0
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS sabotage_anchoring_events (id INTEGER PRIMARY KEY, sabotage REAL, anchor REAL, combined REAL, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        coalition = pirp_context.get("coalition_strength", 0.5)
        memory_fracture = pirp_context.get("memory_fracture_count", 0.0)
        temporal_drift = pirp_context.get("temporal_drift", 0.5)
        self.sabotage = coalition * memory_fracture
        self.anchor = 1.0 - abs(0.5 - temporal_drift)
        combined = self.sabotage * self.anchor
        self._save()
        pirp_context["sabotage_anchoring"] = combined
        return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO sabotage_anchoring_events (sabotage,anchor,combined,ts) VALUES (?,?,?,?)",
                  (self.sabotage, self.anchor, self.sabotage * self.anchor, time.time()))
        c.commit(); c.close()
    def get_state(self): return {"sabotage": self.sabotage, "anchor": self.anchor}

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

