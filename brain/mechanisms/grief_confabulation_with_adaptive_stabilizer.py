from brain.base_mechanism import BrainMechanism
import sqlite3, json, time, random

class GriefConfabulationWithAdaptiveStabilizer(BrainMechanism):
    """
    Cross-layer mechanism combining grief confabulation with adaptive stabilization.
    Tracks grief_confab_stabilizer_events.
    process() combines grief confabulation with adaptive_distortion_stabilizer patterns.
    """
    def __init__(self, db_path=None):
        super().__init__(name="GriefConfabulationWithAdaptiveStabilizer", human_analog="GriefConfabulationWithAdaptiveStabilizer", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.grief = 0.0
        self.stability = 0.5
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS grief_confab_stabilizer_events (id INTEGER PRIMARY KEY, grief REAL, stability REAL, combined REAL, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        confab = pirp_context.get("confabulation", 0.5)
        bond_dist = pirp_context.get("bond_distortion", 0.5)
        distortion = pirp_context.get("distortion_instability", 0.5)
        self.grief = confab * bond_dist
        self.stability = 1.0 - abs(0.5 - distortion)
        combined = self.grief * self.stability
        self._save()
        pirp_context["grief_confab_stabilizer"] = combined
        pirp_context["grief_confab"] = self.grief
        pirp_context["stabilizer"] = self.stability
        return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO grief_confab_stabilizer_events (grief,stability,combined,ts) VALUES (?,?,?,?)",
                  (self.grief, self.stability, self.grief * self.stability, time.time()))
        c.commit(); c.close()
    def get_state(self): return {"grief": self.grief, "stability": self.stability}

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

