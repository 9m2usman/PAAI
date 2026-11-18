import json
import sqlite3
import threading
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

from app.identity.context import current_identity

class GoalRepository:
    def __init__(self, database_path="data/paai_autonomy.db"):
        self.database_path = str(database_path)
        self.lock = threading.RLock()
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS autonomy_goals (
                goal_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, description TEXT NOT NULL,
                status TEXT NOT NULL, trigger_type TEXT NOT NULL, interval_seconds INTEGER,
                next_run_at TEXT, max_steps INTEGER NOT NULL, max_runtime_seconds INTEGER NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_result TEXT)""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_autonomy_due
                ON autonomy_goals(status, next_run_at)""")
            db.execute("""CREATE TABLE IF NOT EXISTS autonomy_runs (
                run_id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, owner_id TEXT NOT NULL,
                status TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
                result TEXT, error TEXT, attempt INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(goal_id) REFERENCES autonomy_goals(goal_id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_autonomy_runs ON autonomy_runs(owner_id, goal_id, started_at)")

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _owner(self):
        return current_identity().user_id

    def create_goal(self, description, trigger_type="manual", interval_seconds=None, next_run_at=None, max_steps=5, max_runtime_seconds=120):
        owner = self._owner()
        now = datetime.now(timezone.utc).isoformat()
        goal_id = str(uuid.uuid4())
        if trigger_type not in {"manual", "scheduled", "event"}:
            raise ValueError("Unsupported trigger type.")
        with self.lock, self._connect() as db:
            db.execute("""INSERT INTO autonomy_goals
                (goal_id,owner_id,description,status,trigger_type,interval_seconds,next_run_at,max_steps,max_runtime_seconds,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (goal_id, owner, description, "active", trigger_type, interval_seconds, next_run_at, max_steps, max_runtime_seconds, now, now))
        return self.get_goal(goal_id)

    def get_goal(self, goal_id):
        with self.lock, self._connect() as db:
            row = db.execute("SELECT * FROM autonomy_goals WHERE goal_id=? AND owner_id=?", (goal_id, self._owner())).fetchone()
        if row is None:
            raise ValueError("Goal not found.")
        return dict(row)

    def list_goals(self):
        with self.lock, self._connect() as db:
            rows = db.execute("SELECT * FROM autonomy_goals WHERE owner_id=? ORDER BY created_at DESC", (self._owner(),)).fetchall()
        return [dict(row) for row in rows]

    def set_status(self, goal_id, status):
        allowed = {"active", "paused", "cancelled"}
        if status not in allowed:
            raise ValueError("Unsupported user-controlled goal status.")
        now = datetime.now(timezone.utc).isoformat()
        with self.lock, self._connect() as db:
            cursor = db.execute("UPDATE autonomy_goals SET status=?, updated_at=? WHERE goal_id=? AND owner_id=? AND status NOT IN ('running','awaiting_approval','completed','cancelled')", (status, now, goal_id, self._owner()))
            if cursor.rowcount != 1:
                raise ValueError("Goal not found or cannot change state.")
        return self.get_goal(goal_id)

    def request_run(self, goal_id):
        now = datetime.now(timezone.utc).isoformat()
        with self.lock, self._connect() as db:
            cursor = db.execute("UPDATE autonomy_goals SET next_run_at=?, status='active', updated_at=? WHERE goal_id=? AND owner_id=? AND status IN ('active','paused')", (now, now, goal_id, self._owner()))
            if cursor.rowcount != 1:
                raise ValueError("Goal not found or cannot be run in its current state.")
        return self.get_goal(goal_id)

    def claim_due(self, limit=20):
        owner = self._owner()
        now = datetime.now(timezone.utc).isoformat()
        claimed = []
        with self.lock:
            db = self._connect()
            try:
                db.execute("BEGIN IMMEDIATE")
                rows = db.execute("""SELECT * FROM autonomy_goals
                    WHERE owner_id=? AND status='active' AND next_run_at IS NOT NULL AND next_run_at<=?
                    ORDER BY next_run_at LIMIT ?""", (owner, now, limit)).fetchall()
                for row in rows:
                    run_id = str(uuid.uuid4())
                    changed = db.execute("UPDATE autonomy_goals SET status='running', updated_at=? WHERE goal_id=? AND owner_id=? AND status='active'", (now, row["goal_id"], owner)).rowcount
                    if changed:
                        db.execute("INSERT INTO autonomy_runs(run_id,goal_id,owner_id,status,started_at) VALUES(?,?,?,?,?)", (run_id, row["goal_id"], owner, "running", now))
                        claimed.append({"goal": dict(row), "run_id": run_id})
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        return claimed

    def finish_run(self, run_id, status, result=None, error=None):
        if status not in {"completed", "failed", "awaiting_approval", "budget_exhausted"}:
            raise ValueError("Invalid run outcome.")
        owner = self._owner()
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        with self.lock, self._connect() as db:
            run = db.execute("SELECT * FROM autonomy_runs WHERE run_id=? AND owner_id=?", (run_id, owner)).fetchone()
            if run is None:
                raise ValueError("Run not found.")
            goal = db.execute("SELECT * FROM autonomy_goals WHERE goal_id=? AND owner_id=?", (run["goal_id"], owner)).fetchone()
            if goal is None:
                raise ValueError("Goal not found.")
            db.execute("UPDATE autonomy_runs SET status=?,finished_at=?,result=?,error=? WHERE run_id=? AND owner_id=?", (status, now, result, error, run_id, owner))
            next_status = status
            next_run = None
            if status == "completed" and goal["interval_seconds"]:
                next_status = "active"
                next_run = (now_dt + timedelta(seconds=goal["interval_seconds"])).isoformat()
            db.execute("UPDATE autonomy_goals SET status=?,next_run_at=?,last_result=?,updated_at=? WHERE goal_id=? AND owner_id=?", (next_status, next_run, result, now, goal["goal_id"], owner))
        return {"run_id": run_id, "goal_id": run["goal_id"], "status": status, "finished_at": now}

    def list_runs(self, goal_id):
        with self.lock, self._connect() as db:
            goal = db.execute("SELECT 1 FROM autonomy_goals WHERE goal_id=? AND owner_id=?", (goal_id, self._owner())).fetchone()
            if goal is None:
                raise ValueError("Goal not found.")
            rows = db.execute("SELECT * FROM autonomy_runs WHERE goal_id=? AND owner_id=? ORDER BY started_at DESC", (goal_id, self._owner())).fetchall()
        return [dict(row) for row in rows]
