import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from app.identity.context import current_identity


class AutonomyApprovalBridge:
    """Durably connects an approval-gated workflow to its originating goal run."""

    def __init__(self, database_path):
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS autonomy_approval_links (
                workflow_id TEXT PRIMARY KEY, run_id TEXT NOT NULL UNIQUE,
                goal_id TEXT NOT NULL, owner_id TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_approval_links_owner ON autonomy_approval_links(owner_id,status)")

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=20)
        db.row_factory = sqlite3.Row
        return db

    def pause_run_for_approval(self, run_id, goal_id, workflow_id):
        owner = current_identity().user_id
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = db.execute("""SELECT status FROM autonomy_runs
                WHERE run_id=? AND goal_id=? AND owner_id=?""", (run_id, goal_id, owner)).fetchone()
            if run is None or run["status"] != "running":
                raise ValueError("Originating goal run is not active.")
            goal = db.execute("""SELECT status FROM autonomy_goals
                WHERE goal_id=? AND owner_id=?""", (goal_id, owner)).fetchone()
            if goal is None or goal["status"] != "running":
                raise ValueError("Originating goal is not active.")
            db.execute("""INSERT INTO autonomy_approval_links
                (workflow_id,run_id,goal_id,owner_id,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?)""", (workflow_id, run_id, goal_id, owner, "pending", now, now))
            db.execute("""UPDATE autonomy_runs SET status='awaiting_approval',
                finished_at=?,result=? WHERE run_id=? AND owner_id=? AND status='running'""",
                (now, json.dumps({"workflow_id": workflow_id}), run_id, owner))
            db.execute("""UPDATE autonomy_goals SET status='awaiting_approval',
                next_run_at=NULL,lease_expires_at=NULL,updated_at=?
                WHERE goal_id=? AND owner_id=? AND status='running'""", (now, goal_id, owner))
            db.commit()
        return {"run_id": run_id, "goal_id": goal_id, "workflow_id": workflow_id,
                "status": "awaiting_approval"}

    def complete_workflow(self, workflow_id, workflow_status, result=None):
        owner = current_identity().user_id
        if workflow_status not in {"completed", "rejected", "failed"}:
            return None
        final_status = "completed" if workflow_status == "completed" else "failed"
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            link = db.execute("""SELECT * FROM autonomy_approval_links
                WHERE workflow_id=? AND owner_id=?""", (workflow_id, owner)).fetchone()
            if link is None:
                db.commit()
                return None
            if link["status"] != "pending":
                db.commit()
                return {"workflow_id": workflow_id, "status": link["status"]}
            db.execute("""UPDATE autonomy_runs SET status=?,finished_at=?,result=?,error=?
                WHERE run_id=? AND owner_id=? AND status='awaiting_approval'""",
                (final_status, now, json.dumps(result, default=str) if result is not None else None,
                 "Workflow rejected by user." if workflow_status == "rejected" else None,
                 link["run_id"], owner))
            db.execute("""UPDATE autonomy_goals SET status=?,last_result=?,updated_at=?
                WHERE goal_id=? AND owner_id=? AND status='awaiting_approval'""",
                (final_status, json.dumps(result, default=str) if result is not None else None,
                 now, link["goal_id"], owner))
            db.execute("""UPDATE autonomy_approval_links SET status=?,updated_at=?
                WHERE workflow_id=? AND owner_id=? AND status='pending'""",
                (workflow_status, now, workflow_id, owner))
            db.commit()
        return {"workflow_id": workflow_id, "run_id": link["run_id"], "status": final_status}
