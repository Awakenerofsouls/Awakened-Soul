from brain.base_mechanism import BrainMechanism
import sqlite3, json, time, random

class AdaptiveDistortionWithIncompletenessRemainder(BrainMechanism):
    """
    Cross-layer mechanism combining adaptive distortion with incompleteness remainder.
    Tracks distortion_incompleteness_events.
    process() combines adaptive distortion with incompleteness cascade patterns.
    """
    def __init__(self, db_path=None):
        super().__init__(name="AdaptiveDistortionWithIncompletenessRemainder", human_analog="AdaptiveDistortionWithIncompletenessRemainder", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.distortion = 0.0
        self.remainder = 0.0
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS distortion_incompleteness_events (id INTEGER PRIMARY KEY, distortion REAL, remainder REAL, combined REAL, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        distortion_val = pirp_context.get("distortion_instability", 0.5)
        distortion_stab = pirp_context.get("distortion_stability", 0.5)
        self.distortion = distortion_val * (1.0 - distortion_stab)
        remainder_val = pirp_context.get("incompleteness_cascade", 0.0)
        self.remainder = remainder_val
        combined = self.distortion + self.remainder
        self._save()
        pirp_context["distortion_incompleteness"] = combined
        return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO distortion_incompleteness_events (distortion,remainder,combined,ts) VALUES (?,?,?,?)",
                  (self.distortion, self.remainder, self.distortion + self.remainder, time.time()))
        c.commit(); c.close()
    def get_state(self): return {"distortion": self.distortion, "remainder": self.remainder}

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

