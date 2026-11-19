import json
import sqlite3
from datetime import timedelta
from contextlib import contextmanager
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

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def recover_workflows(self):
        """Reconcile workflow state with goal runs after a process restart."""
        now = datetime.now(timezone.utc).isoformat()
        recovered = []
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("""SELECT workflow_id,user_id,state_json,status
                FROM workflows WHERE status IN ('awaiting_approval','completed','failed','rejected','execution_uncertain')""").fetchall()
            for row in rows:
                state = json.loads(row["state_json"])
                run_id = state.get("origin_run_id")
                goal_id = state.get("origin_goal_id")
                workflow_id = row["workflow_id"]
                owner = row["user_id"]
                if not run_id or not goal_id:
                    continue
                link = db.execute("""SELECT status FROM autonomy_approval_links
                    WHERE workflow_id=? AND owner_id=?""", (workflow_id, owner)).fetchone()
                if link is not None:
                    continue
                run = db.execute("""SELECT status FROM autonomy_runs
                    WHERE run_id=? AND goal_id=? AND owner_id=?""", (run_id, goal_id, owner)).fetchone()
                goal = db.execute("""SELECT status,interval_seconds,trigger_type,pending_event_json
                    FROM autonomy_goals WHERE goal_id=? AND owner_id=?""", (goal_id, owner)).fetchone()
                if run is None or goal is None or run["status"] != "running" or goal["status"] != "running":
                    continue
                workflow_status = row["status"]
                if workflow_status == "awaiting_approval":
                    run_status = "awaiting_approval"
                    goal_status = "awaiting_approval"
                    link_status = "pending"
                    run_result = json.dumps({"workflow_id": workflow_id})
                    error = None
                    goal_next = None
                else:
                    run_status = "failed" if workflow_status in {"failed", "rejected", "execution_uncertain"} else "completed"
                    goal_status = run_status
                    link_status = workflow_status
                    run_result = json.dumps(state, default=str)
                    error = "Workflow execution outcome is uncertain; automatic replay is blocked." if workflow_status == "execution_uncertain" else ("Workflow rejected by user." if workflow_status == "rejected" else None)
                    goal_next = None
                    if run_status == "completed" and goal["interval_seconds"]:
                        goal_status = "active"
                        goal_next = (datetime.now(timezone.utc) + timedelta(seconds=goal["interval_seconds"])).isoformat()
                    elif run_status == "completed" and goal["trigger_type"] == "event" and goal["pending_event_json"]:
                        if json.loads(goal["pending_event_json"]):
                            goal_status = "active"
                            goal_next = now
                db.execute("""INSERT INTO autonomy_approval_links
                    (workflow_id,run_id,goal_id,owner_id,status,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?)""",
                    (workflow_id, run_id, goal_id, owner, link_status, now, now))
                db.execute("""UPDATE autonomy_runs SET status=?,finished_at=?,result=?,error=?
                    WHERE run_id=? AND owner_id=? AND status='running'""",
                    (run_status, now, run_result, error, run_id, owner))
                db.execute("""UPDATE autonomy_goals SET status=?,next_run_at=?,last_result=?,lease_expires_at=NULL,updated_at=?
                    WHERE goal_id=? AND owner_id=? AND status='running'""",
                    (goal_status, goal_next, run_result, now, goal_id, owner))
                recovered.append({"workflow_id": workflow_id, "run_id": run_id, "status": run_status, "goal_status": goal_status})
            db.commit()
        return recovered

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
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
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
            goal = db.execute("""SELECT interval_seconds,trigger_type,pending_event_json
                FROM autonomy_goals WHERE goal_id=? AND owner_id=?""",
                (link["goal_id"], owner)).fetchone()
            next_status = final_status
            next_run_at = None
            if workflow_status == "completed" and goal is not None:
                if goal["interval_seconds"]:
                    next_status = "active"
                    next_run_at = (now_dt + timedelta(seconds=goal["interval_seconds"])).isoformat()
                elif goal["trigger_type"] == "event" and goal["pending_event_json"]:
                    import json as json_module
                    if json_module.loads(goal["pending_event_json"]):
                        next_status = "active"
                        next_run_at = now
            db.execute("""UPDATE autonomy_goals SET status=?,next_run_at=?,last_result=?,updated_at=?
                WHERE goal_id=? AND owner_id=? AND status='awaiting_approval'""",
                (next_status, next_run_at, json.dumps(result, default=str) if result is not None else None,
                 now, link["goal_id"], owner))
            db.execute("""UPDATE autonomy_approval_links SET status=?,updated_at=?
                WHERE workflow_id=? AND owner_id=? AND status='pending'""",
                (workflow_status, now, workflow_id, owner))
            db.commit()
        return {"workflow_id": workflow_id, "run_id": link["run_id"], "status": final_status}
