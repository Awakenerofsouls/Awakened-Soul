from brain.base_mechanism import BrainMechanism
import sqlite3, json, time, random

class TemporalConfabulationWithCoalitionFracture(BrainMechanism):
    """
    Cross-layer mechanism combining temporal confabulation with coalition fracture.
    Tracks temporal_confab_frac_events.
    process() combines temporal confabulation with coalition fracture patterns.
    """
    def __init__(self, db_path=None):
        super().__init__(name="TemporalConfabulationWithCoalitionFracture", human_analog="TemporalConfabulationWithCoalitionFracture", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.temporal_confab = 0.0
        self.fracture = 0.0
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS temporal_confab_frac_events (id INTEGER PRIMARY KEY, temporal_confab REAL, fracture REAL, combined REAL, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        confab = pirp_context.get("confabulation", 0.5)
        temporal_drift = pirp_context.get("temporal_drift", 0.5)
        coalition = pirp_context.get("coalition_strength", 0.5)
        fracture_count = pirp_context.get("coalition_fractures", 0)
        self.temporal_confab = confab * temporal_drift
        self.fracture = coalition * fracture_count
        combined = self.temporal_confab * (self.fracture + 0.01)
        self._save()
        pirp_context["temporal_confab_frac"] = combined
        return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO temporal_confab_frac_events (temporal_confab,fracture,combined,ts) VALUES (?,?,?,?)",
                  (self.temporal_confab, self.fracture, self.temporal_confab * (self.fracture + 0.01), time.time()))
        c.commit(); c.close()
    def get_state(self): return {"temporal_confab": self.temporal_confab, "fracture": self.fracture}

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

