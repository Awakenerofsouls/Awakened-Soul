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
        c.execute("""CREATE TABLE IF NOT EXISTS autonomous_scheduler(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,focus_mode TEXT,task_weight REAL,self_weight REAL)""")
        c.commit()
class AutonomousScheduler(BrainMechanism):
    def __init__(self):
        super().__init__(name="AutonomousScheduler", human_analog="AutonomousScheduler", layer="integration")
        _init();self.current_focus="task"
    def process(self,pirp_context:dict)->dict:
        task_weight=pirp_context.get("task_priority",0.5)
        self_weight=pirp_context.get("self_goal_priority",0.5)
        idle=pirp_context.get("idle",False)
        if idle:self_weight+=0.3
        if task_weight>self_weight*1.2:self.current_focus="task"
        elif self_weight>task_weight*1.2:self.current_focus="self_goal"
        else:self.current_focus="blended"
        self._save(task_weight,self_weight)
        pirp_context["scheduler_focus"]=self.current_focus
        return pirp_context
    def get_state(self)->dict:
        return{"current_focus":self.current_focus}
    def _save(self,task_w,self_w):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO autonomous_scheduler(timestamp,focus_mode,task_weight,self_weight) VALUES(?,?,?,?)",(time.time(),self.current_focus,task_w,self_w));c.commit()
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

