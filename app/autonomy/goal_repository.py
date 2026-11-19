import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta, timezone

from app.identity.context import current_identity


class GoalRepository:
    MAX_PENDING_EVENTS_PER_GOAL = 100

    def __init__(self, database_path="data/paai_autonomy.db"):
        self.database_path = str(database_path)
        self.lock = threading.RLock()
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS autonomy_goals (
                goal_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, description TEXT NOT NULL,
                status TEXT NOT NULL, trigger_type TEXT NOT NULL, interval_seconds INTEGER,
                next_run_at TEXT, max_steps INTEGER NOT NULL, max_runtime_seconds INTEGER NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_result TEXT,
                event_type TEXT, pending_event_json TEXT, lease_expires_at TEXT)""")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(autonomy_goals)")}
            if "event_type" not in columns:
                db.execute("ALTER TABLE autonomy_goals ADD COLUMN event_type TEXT")
            if "pending_event_json" not in columns:
                db.execute("ALTER TABLE autonomy_goals ADD COLUMN pending_event_json TEXT")
            if "lease_expires_at" not in columns:
                db.execute("ALTER TABLE autonomy_goals ADD COLUMN lease_expires_at TEXT")
            db.execute("CREATE INDEX IF NOT EXISTS idx_autonomy_due ON autonomy_goals(status,next_run_at)")
            db.execute("""CREATE TABLE IF NOT EXISTS autonomy_runs (
                run_id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, owner_id TEXT NOT NULL,
                status TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
                result TEXT, error TEXT, attempt INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(goal_id) REFERENCES autonomy_goals(goal_id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_autonomy_runs ON autonomy_runs(owner_id,goal_id,started_at)")
            db.execute("""CREATE TABLE IF NOT EXISTS autonomy_events (
                event_id TEXT NOT NULL, owner_id TEXT NOT NULL, event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL, occurred_at TEXT NOT NULL, accepted_at TEXT NOT NULL,
                matched_goals INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(event_id,owner_id))""")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def _owner(self):
        return current_identity().user_id

    def create_goal(self, description, trigger_type="manual", interval_seconds=None,
                    next_run_at=None, max_steps=5, max_runtime_seconds=120,
                    event_type=None):
        owner = self._owner()
        now = datetime.now(timezone.utc).isoformat()
        goal_id = str(uuid.uuid4())
        if trigger_type not in {"manual", "scheduled", "event"}:
            raise ValueError("Unsupported trigger type.")
        if trigger_type == "event" and (not isinstance(event_type, str) or not event_type.strip()):
            raise ValueError("Event goals require a registered event type.")
        with self.lock, self._connect() as db:
            db.execute("""INSERT INTO autonomy_goals
                (goal_id,owner_id,description,status,trigger_type,interval_seconds,next_run_at,
                 max_steps,max_runtime_seconds,created_at,updated_at,event_type)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (goal_id, owner, description, "active", trigger_type, interval_seconds,
                 next_run_at, max_steps, max_runtime_seconds, now, now, event_type))
        return self.get_goal(goal_id)

    def get_goal(self, goal_id):
        with self.lock, self._connect() as db:
            row = db.execute("SELECT * FROM autonomy_goals WHERE goal_id=? AND owner_id=?",
                             (goal_id, self._owner())).fetchone()
        if row is None:
            raise ValueError("Goal not found.")
        return dict(row)

    def list_goals(self):
        with self.lock, self._connect() as db:
            rows = db.execute("SELECT * FROM autonomy_goals WHERE owner_id=? ORDER BY created_at DESC",
                              (self._owner(),)).fetchall()
        return [dict(row) for row in rows]

    def set_status(self, goal_id, status):
        if status not in {"active", "paused", "cancelled"}:
            raise ValueError("Unsupported user-controlled goal status.")
        now = datetime.now(timezone.utc).isoformat()
        with self.lock, self._connect() as db:
            cursor = db.execute("""UPDATE autonomy_goals SET status=?,updated_at=?
                WHERE goal_id=? AND owner_id=?
                AND status NOT IN ('running','awaiting_approval','completed','cancelled')""",
                (status, now, goal_id, self._owner()))
            if cursor.rowcount != 1:
                raise ValueError("Goal not found or cannot change state.")
        return self.get_goal(goal_id)

    def request_run(self, goal_id):
        now = datetime.now(timezone.utc).isoformat()
        with self.lock, self._connect() as db:
            cursor = db.execute("""UPDATE autonomy_goals SET next_run_at=?,status='active',
                pending_event_json=NULL,updated_at=? WHERE goal_id=? AND owner_id=?
                AND status IN ('active','paused') AND trigger_type!='event'""",
                (now, now, goal_id, self._owner()))
            if cursor.rowcount != 1:
                raise ValueError("Goal not found or cannot be manually run in its current state.")
        return self.get_goal(goal_id)

    def publish_event(self, event_id, event_type, payload, occurred_at):
        owner = self._owner()
        now = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        with self.lock:
            db = sqlite3.connect(self.database_path, timeout=20)
            db.row_factory = sqlite3.Row
            try:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT matched_goals FROM autonomy_events WHERE event_id=? AND owner_id=?",
                                      (event_id, owner)).fetchone()
                if existing:
                    db.commit()
                    return {"event_id": event_id, "duplicate": True,
                            "matched_goals": existing["matched_goals"]}
                goals = db.execute("""SELECT goal_id FROM autonomy_goals
                    WHERE owner_id=? AND event_type=? AND trigger_type='event' AND status IN ('active','running')""",
                    (owner, event_type)).fetchall()
                for row in goals:
                    queued = db.execute(
                        "SELECT pending_event_json FROM autonomy_goals WHERE goal_id=? AND owner_id=?",
                        (row["goal_id"], owner)
                    ).fetchone()["pending_event_json"]
                    pending = json.loads(queued) if queued else []
                    if len(pending) >= self.MAX_PENDING_EVENTS_PER_GOAL:
                        raise ValueError("Event goal queue is full; retry after pending work is processed.")
                    pending.append({
                        "event_id": event_id,
                        "event_type": event_type,
                        "payload": payload,
                        "occurred_at": occurred_at
                    })
                    db.execute("""UPDATE autonomy_goals SET next_run_at=?,pending_event_json=?,updated_at=?
                        WHERE goal_id=? AND owner_id=? AND status IN ('active','running')""",
                        (now, json.dumps(pending, separators=(",", ":"), sort_keys=True),
                         now, row["goal_id"], owner))
                db.execute("""INSERT INTO autonomy_events
                    (event_id,owner_id,event_type,payload_json,occurred_at,accepted_at,matched_goals)
                    VALUES(?,?,?,?,?,?,?)""",
                    (event_id, owner, event_type, payload_json, occurred_at, now, len(goals)))
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        return {"event_id": event_id, "duplicate": False, "matched_goals": len(goals)}

    def claim_due(self, limit=20):
        owner = self._owner()
        now = datetime.now(timezone.utc).isoformat()
        claimed = []
        with self.lock:
            db = sqlite3.connect(self.database_path, timeout=20)
            db.row_factory = sqlite3.Row
            try:
                db.execute("BEGIN IMMEDIATE")
                stale = db.execute("""SELECT goal_id FROM autonomy_goals
                    WHERE owner_id=? AND status='running' AND lease_expires_at IS NOT NULL
                    AND lease_expires_at<=?""", (owner, now)).fetchall()
                for stale_goal in stale:
                    db.execute("""UPDATE autonomy_runs SET status='failed',finished_at=?,
                        error='Worker lease expired before completion.'
                        WHERE goal_id=? AND owner_id=? AND status='running'""",
                        (now, stale_goal["goal_id"], owner))
                    db.execute("""UPDATE autonomy_goals SET status='active',next_run_at=?,
                        lease_expires_at=NULL,updated_at=? WHERE goal_id=? AND owner_id=?
                        AND status='running'""",
                        (now, now, stale_goal["goal_id"], owner))
                rows = db.execute("""SELECT * FROM autonomy_goals
                    WHERE owner_id=? AND status='active' AND next_run_at IS NOT NULL AND next_run_at<=?
                    ORDER BY next_run_at LIMIT ?""", (owner, now, limit)).fetchall()
                for row in rows:
                    run_id = str(uuid.uuid4())
                    lease_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
                    changed = db.execute("""UPDATE autonomy_goals SET status='running',
                        lease_expires_at=?,updated_at=?
                        WHERE goal_id=? AND owner_id=? AND status='active'""",
                        (lease_expires_at, now, row["goal_id"], owner)).rowcount
                    if changed:
                        db.execute("""INSERT INTO autonomy_runs
                            (run_id,goal_id,owner_id,status,started_at) VALUES(?,?,?,?,?)""",
                            (run_id, row["goal_id"], owner, "running", now))
                        item = dict(row)
                        pending = json.loads(row["pending_event_json"]) if row["pending_event_json"] else []
                        item["event_payload"] = pending.pop(0) if pending else None
                        remaining = json.dumps(pending, separators=(",", ":"), sort_keys=True) if pending else None
                        db.execute("""UPDATE autonomy_goals SET pending_event_json=?
                            WHERE goal_id=? AND owner_id=?""",
                            (remaining, row["goal_id"], owner))
                        claimed.append({"goal": item, "run_id": run_id})
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
            run = db.execute("SELECT * FROM autonomy_runs WHERE run_id=? AND owner_id=?",
                             (run_id, owner)).fetchone()
            if run is None:
                raise ValueError("Run not found.")
            if run["status"] != "running":
                raise ValueError("Run has already reached a terminal state.")
            goal = db.execute("SELECT * FROM autonomy_goals WHERE goal_id=? AND owner_id=?",
                              (run["goal_id"], owner)).fetchone()
            if goal is None:
                raise ValueError("Goal not found.")
            db.execute("""UPDATE autonomy_runs SET status=?,finished_at=?,result=?,error=?
                WHERE run_id=? AND owner_id=? AND status='running'""",
                (status, now, result, error, run_id, owner))
            next_status = status
            next_run = None
            pending_events = json.loads(goal["pending_event_json"]) if goal["pending_event_json"] else []
            if status == "completed" and goal["interval_seconds"]:
                next_status = "active"
                next_run = (now_dt + timedelta(seconds=goal["interval_seconds"])).isoformat()
            elif status == "completed" and goal["trigger_type"] == "event" and pending_events:
                next_status = "active"
                next_run = now
            elif status == "failed" and goal["trigger_type"] == "event" and pending_events:
                next_status = "active"
                next_run = now
            db.execute("""UPDATE autonomy_goals SET status=?,next_run_at=?,last_result=?,
                lease_expires_at=NULL,updated_at=? WHERE goal_id=? AND owner_id=?""",
                (next_status, next_run, result, now, goal["goal_id"], owner))
        return {"run_id": run_id, "goal_id": run["goal_id"], "status": status, "finished_at": now}

    def list_runs(self, goal_id):
        with self.lock, self._connect() as db:
            owner = self._owner()
            goal = db.execute("SELECT 1 FROM autonomy_goals WHERE goal_id=? AND owner_id=?",
                              (goal_id, owner)).fetchone()
            if goal is None:
                raise ValueError("Goal not found.")
            rows = db.execute("""SELECT * FROM autonomy_runs WHERE goal_id=? AND owner_id=?
                ORDER BY started_at DESC""", (goal_id, owner)).fetchall()
        return [dict(row) for row in rows]
