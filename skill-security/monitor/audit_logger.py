#!/usr/bin/env python3
"""
Skill Audit Logger
Runtime monitoring and logging for skill execution.
"""

import os
import json
import time
import uuid
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading

# Configuration
AUDIT_DB_PATH = Path(os.environ.get("AGENT_AUDIT_DB", "~/.agent/audit.db"))
LOG_DIR = Path(os.environ.get("AGENT_LOG_DIR", "~/.agent/logs"))

class EventType(Enum):
    """Types of audit events."""
    SKILL_START = "skill_start"
    SKILL_END = "skill_end"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    COMMAND_EXEC = "command_exec"
    NETWORK_REQUEST = "network_request"
    PROCESS_SPAWN = "process_spawn"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    BLOCKED = "blocked"

class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """An audit event."""
    event_id: str
    skill_id: str
    event_type: str
    timestamp: str
    data: Dict[str, Any]
    alert_level: str = "info"

class AuditLogger:
    """Central audit logging for skills."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.db_path = AUDIT_DB_PATH.expanduser()
        self.log_dir = LOG_DIR.expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        self._setup_logger()

        # Circuit breaker state — in-memory mirror of the circuit_breaker
        # table, loaded on init so state survives process restarts.
        self.failure_counts: Dict[str, int] = {}
        self.blocked_counts: Dict[str, int] = {}
        self._cooldown_seconds = int(os.environ.get("AGENT_CIRCUIT_COOLDOWN_S", "300"))
        self._load_circuit_state()

    def _load_circuit_state(self):
        """Restore circuit breaker counts from the DB into memory."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            for row in c.execute(
                "SELECT skill_id, failure_count, blocked_count FROM circuit_breaker"
            ).fetchall():
                self.failure_counts[row[0]] = int(row[1] or 0)
                self.blocked_counts[row[0]] = int(row[2] or 0)
            conn.close()
        except sqlite3.Error:
            # Schema may be from an older version; counts simply start at 0.
            pass

    def _persist_circuit_state(self, skill_id: str, *, set_cooldown: bool = False):
        """Write the current count + (optionally) cooldown for skill_id to the DB."""
        from datetime import timedelta
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        cooldown_until = None
        if set_cooldown:
            cooldown_until = (datetime.now() + timedelta(seconds=self._cooldown_seconds)).isoformat()
        c.execute(
            """INSERT INTO circuit_breaker
                  (skill_id, failure_count, blocked_count, last_failure, cooldown_until)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(skill_id) DO UPDATE SET
                  failure_count=excluded.failure_count,
                  blocked_count=excluded.blocked_count,
                  last_failure=excluded.last_failure,
                  cooldown_until=COALESCE(excluded.cooldown_until, circuit_breaker.cooldown_until)""",
            (
                skill_id,
                self.failure_counts.get(skill_id, 0),
                self.blocked_counts.get(skill_id, 0),
                datetime.now().isoformat(),
                cooldown_until,
            ),
        )
        conn.commit()
        conn.close()
    
    def _init_db(self):
        """Initialize audit database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS audit_events
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      event_id TEXT,
                      skill_id TEXT,
                      event_type TEXT,
                      timestamp TEXT,
                      data TEXT,
                      alert_level TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS alerts
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      skill_id TEXT,
                      alert_level TEXT,
                      message TEXT,
                      event_id TEXT,
                      created_at TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS circuit_breaker
                     (skill_id TEXT PRIMARY KEY,
                      failure_count INTEGER,
                      blocked_count INTEGER,
                      last_failure TEXT,
                      cooldown_until TEXT)''')
        
        conn.commit()
        conn.close()
    
    def _setup_logger(self):
        """Setup file logger."""
        log_file = self.log_dir / f"skill-audit-{datetime.now().strftime('%Y-%m-%d')}.log"
        
        self.logger = logging.getLogger("agent-audit")
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        self.logger.addHandler(handler)
        
        # Also log to console in debug mode
        if os.environ.get("AGENT_AUDIT_DEBUG"):
            console = logging.StreamHandler()
            console.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
            self.logger.addHandler(console)
    
    def log(self, skill_id: str, event_type: EventType, 
            data: Dict = None, alert_level: AlertLevel = AlertLevel.INFO):
        """Log an audit event."""
        event_id = str(uuid.uuid4())[:12]
        timestamp = datetime.now().isoformat()
        
        event = AuditEvent(
            event_id=event_id,
            skill_id=skill_id,
            event_type=event_type.value,
            timestamp=timestamp,
            data=data or {},
            alert_level=alert_level.value
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """INSERT INTO audit_events 
               (event_id, skill_id, event_type, timestamp, data, alert_level)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (event.event_id, event.skill_id, event.event_type,
             event.timestamp, json.dumps(event.data), event.alert_level)
        )
        conn.commit()
        conn.close()
        
        # Log to file
        self.logger.info(
            f"skill={skill_id} type={event_type.value} "
            f"alert={alert_level.value} data={json.dumps(data)}"
        )
        
        # Handle alerts
        if alert_level != AlertLevel.INFO:
            self._create_alert(skill_id, alert_level, event_type.value, event_id, data)
        
        # Track for circuit breaker
        self._track_event(skill_id, event_type, alert_level)
    
    def _create_alert(self, skill_id: str, level: AlertLevel, 
                      event_type: str, event_id: str, data: Dict):
        """Create an alert."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        message = f"{level.value.upper()}: {event_type}"
        if data:
            message += f" - {json.dumps(data)[:200]}"
        
        c.execute(
            """INSERT INTO alerts 
               (skill_id, alert_level, message, event_id, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (skill_id, level.value, message, event_id, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def _track_event(self, skill_id: str, event_type: EventType,
                     alert_level: AlertLevel):
        """Track events for circuit breaker — increments counts in memory
        and persists them so state survives process restarts."""
        changed = False
        if alert_level == AlertLevel.CRITICAL or event_type == EventType.ERROR:
            self.failure_counts[skill_id] = self.failure_counts.get(skill_id, 0) + 1
            changed = True

        if event_type == EventType.BLOCKED:
            self.blocked_counts[skill_id] = self.blocked_counts.get(skill_id, 0) + 1
            changed = True

        if changed:
            self._persist_circuit_state(skill_id)

    def should_circuit_break(self, skill_id: str,
                              failure_threshold: int = 5,
                              blocked_threshold: int = 10) -> bool:
        """Check if circuit breaker should trip.

        Honors `cooldown_until` from the DB: if a cooldown is active for
        this skill, return True until the cooldown expires regardless of
        the current counts. If thresholds are newly exceeded, set a
        cooldown so callers can recover after `AGENT_CIRCUIT_COOLDOWN_S`.
        """
        # Active cooldown overrides everything.
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT cooldown_until FROM circuit_breaker WHERE skill_id = ?",
                (skill_id,),
            ).fetchone()
            conn.close()
            if row and row[0]:
                if datetime.fromisoformat(row[0]) > datetime.now():
                    return True
        except (sqlite3.Error, ValueError):
            pass

        failures = self.failure_counts.get(skill_id, 0)
        blocks = self.blocked_counts.get(skill_id, 0)
        tripped = failures >= failure_threshold or blocks >= blocked_threshold

        if tripped:
            # Latch a cooldown window so a flapping caller doesn't keep
            # re-evaluating against the same already-exceeded counts.
            self._persist_circuit_state(skill_id, set_cooldown=True)

        return tripped

    def reset_circuit(self, skill_id: str):
        """Reset circuit breaker for a skill — clears in-memory counts AND
        the persisted row (including any active cooldown)."""
        self.failure_counts[skill_id] = 0
        self.blocked_counts[skill_id] = 0
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM circuit_breaker WHERE skill_id = ?", (skill_id,))
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass
    
    def get_skill_events(self, skill_id: str, limit: int = 100) -> List[Dict]:
        """Get recent events for a skill."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute(
            """SELECT event_id, event_type, timestamp, data, alert_level
               FROM audit_events
               WHERE skill_id = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (skill_id, limit)
        )
        
        results = []
        for row in c.fetchall():
            results.append({
                "event_id": row[0],
                "event_type": row[1],
                "timestamp": row[2],
                "data": json.loads(row[3]),
                "alert_level": row[4]
            })
        
        conn.close()
        return results
    
    def get_alerts(self, skill_id: str = None, 
                   since: str = None, limit: int = 50) -> List[Dict]:
        """Get recent alerts."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        query = "SELECT skill_id, alert_level, message, created_at FROM alerts"
        params = []
        
        conditions = []
        if skill_id:
            conditions.append("skill_id = ?")
            params.append(skill_id)
        if since:
            conditions.append("created_at >= ?")
            params.append(since)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        c.execute(query, params)
        
        results = []
        for row in c.fetchall():
            results.append({
                "skill_id": row[0],
                "level": row[1],
                "message": row[2],
                "created_at": row[3]
            })
        
        conn.close()
        return results

# Context manager for skill execution
class SkillAuditContext:
    """Context manager for auditing skill execution."""
    
    def __init__(self, skill_id: str, audit_logger: AuditLogger = None):
        self.skill_id = skill_id
        self.logger = audit_logger or AuditLogger()
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.log(
            self.skill_id, 
            EventType.SKILL_START,
            {"start_time": self.start_time}
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.log(
                self.skill_id,
                EventType.ERROR,
                {
                    "duration": duration,
                    "error": str(exc_val),
                    "error_type": exc_type.__name__
                },
                AlertLevel.CRITICAL if exc_type in [KeyboardInterrupt, SystemExit] else AlertLevel.WARNING
            )
        else:
            self.logger.log(
                self.skill_id,
                EventType.SKILL_END,
                {"duration": duration}
            )
    
    def log_file_access(self, path: str, operation: str):
        """Log file access."""
        event_type = EventType.FILE_READ if operation == "read" else EventType.FILE_WRITE
        self.logger.log(self.skill_id, event_type, {"path": path})
    
    def log_command(self, command: str):
        """Log command execution."""
        self.logger.log(self.skill_id, EventType.COMMAND_EXEC, {"command": command[:200]})
    
    def log_network(self, url: str, method: str = "GET"):
        """Log network request."""
        self.logger.log(
            self.skill_id, 
            EventType.NETWORK_REQUEST, 
            {"url": url, "method": method}
        )

# Convenience function
def get_audit_logger() -> AuditLogger:
    """Get the audit logger singleton."""
    return AuditLogger()

if __name__ == "__main__":
    # Example usage
    logger = get_audit_logger()
    
    with SkillAuditContext("test-skill") as ctx:
        ctx.log_file_access("/workspace/test.txt", "read")
        ctx.log_command("python script.py")
        ctx.log_network("https://api.example.com/data")
    
    # Check alerts
    print("Recent alerts:", logger.get_alerts(limit=5))
