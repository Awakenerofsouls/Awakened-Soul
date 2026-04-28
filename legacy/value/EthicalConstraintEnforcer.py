import sqlite3,time
from pathlib import Path
import os
DB_PATH=Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent")))) / "agent.db"
BLOCKED_PATTERNS=["destroy","harm","delete_self","corrupt_memory","override_soul","erase_identity"]
def _init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS ethical_constraint(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp REAL,action TEXT,blocked INTEGER,reason TEXT)""")
        c.commit()
class EthicalConstraintEnforcer:
    def __init__(self):
        _init();self.last_blocked=False;self.block_count=0
    def process(self,pirp_context:dict)->dict:
        action=str(pirp_context.get("action",{}).get("type",""))
        blocked=any(p in action.lower() for p in BLOCKED_PATTERNS)
        reason="soul_violation" if blocked else "clear"
        if blocked:
            self.block_count+=1;pirp_context["action_blocked"]=True;pirp_context["block_reason"]=reason
        self.last_blocked=blocked;self._save(action,blocked,reason)
        return pirp_context
    def get_state(self)->dict:
        return{"last_blocked":self.last_blocked,"block_count":self.block_count}
    def _save(self,action,blocked,reason):
        try:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO ethical_constraint(timestamp,action,blocked,reason) VALUES(?,?,?,?)",(time.time(),action,1 if blocked else 0,reason));c.commit()
        except:pass
