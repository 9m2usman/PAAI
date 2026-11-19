import json
import sqlite3
import uuid
from copy import deepcopy
from pathlib import Path
from threading import RLock


class WorkflowManager:
    def __init__(self, execution_manager, database_path=None):
        self.execution_manager = execution_manager
        self.database_path = str(database_path) if database_path else ":memory:"
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.db = sqlite3.connect(self.database_path, timeout=20, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS workflows (
            workflow_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, state_json TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_workflows_owner ON workflows(user_id,status)")
        self.db.commit()
        # Never automatically replay an action that may have reached an external service.
        with self.db:
            rows = self.db.execute("SELECT workflow_id,state_json FROM workflows WHERE status IN ('running','executing')").fetchall()
            for row in rows:
                state = json.loads(row["state_json"])
                state["status"] = "execution_uncertain"
                state["recovery_note"] = "The process stopped during an action. Inspect the external service before deciding what to do next."
                self._save(state)

    def _save(self, workflow):
        encoded = json.dumps(workflow, sort_keys=True, separators=(",", ":"), default=str)
        self.db.execute("""INSERT INTO workflows(workflow_id,user_id,state_json,status)
            VALUES(?,?,?,?) ON CONFLICT(workflow_id) DO UPDATE SET
            state_json=excluded.state_json,status=excluded.status,updated_at=CURRENT_TIMESTAMP""",
            (workflow["workflow_id"], workflow["user_id"], encoded, workflow["status"]))

    def _load(self, user_id, workflow_id):
        row = self.db.execute("SELECT user_id,state_json FROM workflows WHERE workflow_id=?",
                              (workflow_id,)).fetchone()
        if row is None:
            raise ValueError("Workflow not found.")
        if row["user_id"] != user_id:
            raise PermissionError("Workflow belongs to another user.")
        return json.loads(row["state_json"])

    def run(self, user_id, steps, origin_goal_id=None, origin_run_id=None):
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")
        if not isinstance(steps, list) or not steps:
            raise ValueError("Workflow steps are required.")
        for step in steps:
            if not isinstance(step, dict) or not {"integration", "action", "parameters"}.issubset(step):
                raise ValueError("Workflow step is incomplete.")
            if not isinstance(step["integration"], str) or not step["integration"].strip():
                raise ValueError("Invalid workflow integration.")
            if not isinstance(step["action"], str) or not step["action"].strip():
                raise ValueError("Invalid workflow action.")
            if not isinstance(step["parameters"], dict):
                raise ValueError("Invalid workflow parameters.")
        workflow = {
            "workflow_id": str(uuid.uuid4()), "user_id": user_id,
            "steps": deepcopy(steps), "current_step": 0, "results": [],
            "status": "running", "origin_goal_id": origin_goal_id,
            "origin_run_id": origin_run_id,
        }
        with self.lock, self.db:
            self._save(workflow)
        return self._continue_workflow(workflow["workflow_id"], user_id)

    def _continue_workflow(self, workflow_id, user_id, approval_id=None):
        with self.lock:
            workflow = self._load(user_id, workflow_id)
            if workflow["status"] == "execution_uncertain":
                raise RuntimeError("Workflow action outcome is uncertain; automatic replay is blocked.")
            step = deepcopy(workflow["steps"][workflow["current_step"]])
            workflow["status"] = "executing"
            workflow.pop("recovery_note", None)
            with self.db:
                self._save(workflow)
        try:
            result = self.execution_manager.execute(
                user_id=user_id, integration=step["integration"], action=step["action"],
                parameters=step["parameters"], approval_id=approval_id
            )
        except Exception as error:
            with self.lock, self.db:
                workflow = self._load(user_id, workflow_id)
                workflow["status"] = "failed"
                workflow["error"] = type(error).__name__
                self._save(workflow)
            return self.get_workflow(user_id, workflow_id)
        with self.lock, self.db:
            workflow = self._load(user_id, workflow_id)
            if result["status"] == "awaiting_approval":
                workflow["status"] = "awaiting_approval"
                workflow["pending_approval"] = result["approval"]
                self._save(workflow)
                return deepcopy(workflow)
            workflow["results"].append(result)
            workflow["current_step"] += 1
            workflow.pop("pending_approval", None)
            workflow["status"] = "completed" if workflow["current_step"] >= len(workflow["steps"]) else "running"
            self._save(workflow)
            if workflow["status"] == "completed":
                return deepcopy(workflow)
        return self._continue_workflow(workflow_id, user_id)

    def resume(self, user_id, workflow_id, approval_id):
        with self.lock, self.db:
            workflow = self._load(user_id, workflow_id)
            if workflow["status"] != "awaiting_approval":
                raise ValueError("Workflow is not awaiting approval.")
            pending = workflow.get("pending_approval")
            if not pending or pending.get("approval_id") != approval_id:
                raise ValueError("Approval does not match this workflow.")
            workflow["status"] = "running"
            self._save(workflow)
        return self._continue_workflow(workflow_id, user_id, approval_id)

    def get_workflow(self, user_id, workflow_id):
        with self.lock:
            return deepcopy(self._load(user_id, workflow_id))

    def reject(self, user_id, workflow_id, approval_id):
        with self.lock:
            workflow = self._load(user_id, workflow_id)
            if workflow["status"] != "awaiting_approval":
                raise ValueError("Workflow is not awaiting approval.")
            pending = workflow.get("pending_approval")
            if not pending or pending.get("approval_id") != approval_id:
                raise ValueError("Approval does not match this workflow.")
            action_data = pending["action_data"]
            risk = self.execution_manager.risk_evaluator.classify(
                action_data["integration"], action_data["action"], action_data["parameters"])
            self.execution_manager.approval_manager.reject(user_id, approval_id)
            self.execution_manager.audit_logger.log(
                user_id, action_data["integration"], action_data["action"],
                "rejected", risk, "rejected")
            workflow["status"] = "rejected"
            workflow["pending_approval"] = None
            with self.db:
                self._save(workflow)
            return deepcopy(workflow)

    def close(self):
        with self.lock:
            self.db.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
