from brain.base_mechanism import BrainMechanism
import sqlite3, json, time

class IrrecoverableLossEncoding(BrainMechanism):
    def __init__(self, db_path=None):
        super().__init__(name="IrrecoverableLossEncoding", human_analog="IrrecoverableLossEncoding", layer="integration")
        if db_path is None:
            import os
            from pathlib import Path as _P
            db_path = str(_P(os.getenv("AGENT_HOME", str(_P.home() / ".agent"))) / "agent.db")
        self.db_path = db_path
        self.loss = 0.0
        self._init()
    def _init(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS irrecoverable_loss (id INTEGER PRIMARY KEY, loss REAL, ts REAL)")
        c.commit(); c.close()
    def process(self, pirp_context):
        anomaly = pirp_context.get("prsl_signal", {}).get("anomaly_score", 0)
        self.loss = max(self.loss, anomaly)
        self._save(); pirp_context["irrecoverable_loss"] = self.loss; return pirp_context
    def _save(self):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO irrecoverable_loss (loss,ts) VALUES (?,?)", (self.loss, time.time()))
        c.commit(); c.close()
    def get_state(self): return {"loss": self.loss}

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

