from brain.base_mechanism import BrainMechanism
import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent"))) / "agent.db"
try:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS long_term_reward(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,session_reward REAL,cumulative_reward REAL)""")
        c.commit()
class LongTermRewardTracker(BrainMechanism):
    def __init__(self):
        super().__init__(name="LongTermRewardTracker", human_analog="LongTermRewardTracker", layer="integration")
        _init();self.cumulative_reward=0.0;self.session_reward=0.0;self._load()
    def process(self,pirp_context:dict)->dict:
        reward=float(pirp_context.get("reward",0.0))
        value_score=float(pirp_context.get("value_score",0.5))
        tick_reward=(reward+value_score)*0.05
        self.session_reward+=tick_reward;self.cumulative_reward+=tick_reward
        self._save()
        pirp_context["cumulative_reward"]=self.cumulative_reward;pirp_context["session_reward"]=self.session_reward
        return pirp_context
    def get_state(self)->dict:
        return{"cumulative_reward":round(self.cumulative_reward,4),"session_reward":round(self.session_reward,4)}
    def _load(self):
        try:
            with sqlite3.connect(DB_PATH) as c:
                row=c.execute("SELECT cumulative_reward FROM long_term_reward ORDER BY id DESC LIMIT 1").fetchone()
                if row:self.cumulative_reward=row[0]
        except:pass
    def _save(self):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO long_term_reward(timestamp,session_reward,cumulative_reward) VALUES(?,?,?)",(time.time(),self.session_reward,self.cumulative_reward));c.commit()
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

