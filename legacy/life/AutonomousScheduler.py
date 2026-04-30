import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("NOVA_HOME", str(Path.home() / ".nova")))) / "nova.db"
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS autonomous_scheduler(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,focus_mode TEXT,task_weight REAL,self_weight REAL)""")
        c.commit()
class AutonomousScheduler:
    def __init__(self):
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
