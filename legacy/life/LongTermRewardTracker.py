import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS long_term_reward(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,session_reward REAL,cumulative_reward REAL)""")
        c.commit()
class LongTermRewardTracker:
    def __init__(self):
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
