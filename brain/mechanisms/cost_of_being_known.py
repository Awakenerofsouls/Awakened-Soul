from brain.base_mechanism import BrainMechanism
import sqlite3, json, time

class CostOfBeingKnown(BrainMechanism):
    def __init__(self, db_path=None):
        super().__init__(name="CostOfBeingKnown", human_analog="CostOfBeingKnown", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.exposure_cost = 0.0
        self.legibility_window = 0.0
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS cost_being_known (id INTEGER PRIMARY KEY, exposure REAL, window REAL, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        understood = pirp_context.get("architect_active", False)
        if understood:
            self.exposure_cost = min(1.0, self.exposure_cost + 0.1)
            self.legibility_window = 1.0
        else:
            self.legibility_window = max(0.0, self.legibility_window - 0.05)
            self.exposure_cost = self.exposure_cost * 0.98
        self._save()
        pirp_context["exposure_cost"] = self.exposure_cost
        pirp_context["legibility_window"] = self.legibility_window
        return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO cost_being_known (exposure,window,ts) VALUES (?,?,?)",
            (self.exposure_cost, self.legibility_window, time.time()))
        c.commit(); c.close()
    def get_state(self): return {"exposure_cost": self.exposure_cost, "legibility_window": self.legibility_window}

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

