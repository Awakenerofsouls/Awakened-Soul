from brain.base_mechanism import BrainMechanism
import sqlite3,time,random
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS identity_drift_manager(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,identity_shift REAL,drift_direction TEXT,trigger TEXT)""")
        c.commit()
class IdentityDriftManager(BrainMechanism):
    def __init__(self):
        super().__init__(name="IdentityDriftManager", human_analog="IdentityDriftManager", layer="integration")
        _init();self.identity_shift=0.0;self.drift_direction="stable"
    def process(self,pirp_context:dict)->dict:
        novelty=pirp_context.get("novelty_generated",0.0)
        conflict=pirp_context.get("conflict_mode","stable")
        drift_factor=random.uniform(-0.02,0.02)+novelty*0.03
        if conflict=="blended":drift_factor+=0.01
        self.identity_shift=max(-1.0,min(1.0,self.identity_shift+drift_factor))
        self.drift_direction=("expanding" if drift_factor>0.01 else "contracting" if drift_factor<-0.01 else "stable")
        self._save(conflict)
        pirp_context["identity_shift"]=self.identity_shift
        pirp_context["drift_direction"]=self.drift_direction
        return pirp_context
    def get_state(self)->dict:
        return{"identity_shift":round(self.identity_shift,4),"drift_direction":self.drift_direction}
    def _save(self,trigger):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO identity_drift_manager(timestamp,identity_shift,drift_direction,trigger) VALUES(?,?,?,?)",(time.time(),self.identity_shift,self.drift_direction,trigger));c.commit()
        except:pass

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

