import tempfile
import unittest
import sqlite3
from pathlib import Path

from app.approvals.approval_manager import ApprovalManager
from app.workflows.workflow_manager import WorkflowManager
from app.autonomy.goal_repository import GoalRepository
from app.autonomy.approval_bridge import AutonomyApprovalBridge
from app.security.permission_manager import PermissionManager
from app.identity.context import identity_scope
from app.auth.token_service import TokenService


class FakeExecution:
    def __init__(self, approvals):
        self.approval_manager = approvals
        self.risk_evaluator = type("Risk", (), {"classify": lambda self, *args: "high"})()
        self.audit_logger = type("Audit", (), {"log": lambda self, *args: None})()


class DurableApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "paai.db")
        tokens = TokenService("x" * 40)
        self.identity = tokens.verify_token(tokens.issue_token("owner-a", "a@example.com"))
        self.other = tokens.verify_token(tokens.issue_token("owner-b", "b@example.com"))

    def tearDown(self):
        self.temp.cleanup()

    def test_permissions_survive_manager_restart_and_remain_tenant_scoped(self):
        first = PermissionManager(database_path=self.db)
        first.grant_permission("owner-a", "gmail", ["send_email"])
        first.grant_automatic_permission("owner-a", "gmail", "send_email")
        first.close()
        second = PermissionManager(database_path=self.db)
        self.assertTrue(second.is_allowed("owner-a", "gmail", "send_email"))
        self.assertTrue(second.is_automatic_allowed("owner-a", "gmail", "send_email"))
        self.assertFalse(second.is_allowed("owner-b", "gmail", "send_email"))
        second.revoke_permission("owner-a", "gmail", "send_email")
        self.assertFalse(second.is_allowed("owner-a", "gmail", "send_email"))
        second.close()

    def test_inflight_workflow_is_marked_uncertain_after_restart(self):
        approvals = ApprovalManager(database_path=self.db)
        workflow = WorkflowManager(FakeExecution(approvals), database_path=self.db)
        state = {
            "workflow_id": "wf-running", "user_id": "owner-a",
            "steps": [{"integration": "gmail", "action": "send_email", "parameters": {}}],
            "current_step": 0, "results": [], "status": "executing",
        }
        with workflow.db:
            workflow._save(state)
        workflow.close()
        restarted = WorkflowManager(FakeExecution(approvals), database_path=self.db)
        recovered = restarted.get_workflow("owner-a", "wf-running")
        self.assertEqual(recovered["status"], "execution_uncertain")
        with self.assertRaises(RuntimeError):
            restarted._continue_workflow("wf-running", "owner-a")
        restarted.close()
        approvals.close()

    def test_approval_survives_manager_restart_and_is_single_use(self):
        first = ApprovalManager(database_path=self.db)
        action = {"integration": "gmail", "action": "send_email", "parameters": {"to": "a@example.com"}}
        pending = first.request_approval("owner-a", action)
        first.close()
        second = ApprovalManager(database_path=self.db)
        self.assertEqual(second.get_approval("owner-a", pending["approval_id"])["status"], "pending")
        second.approve("owner-a", pending["approval_id"])
        second.close()
        third = ApprovalManager(database_path=self.db)
        self.assertEqual(third.get_approval("owner-a", pending["approval_id"])["status"], "approved")
        third.consume_approval("owner-a", pending["approval_id"], action)
        with self.assertRaises(PermissionError):
            third.consume_approval("owner-a", pending["approval_id"], action)
        third.close()

    def test_approval_is_tenant_isolated_and_action_bound(self):
        manager = ApprovalManager(database_path=self.db)
        action = {"integration": "gmail", "action": "send_email", "parameters": {"to": "a@example.com"}}
        pending = manager.request_approval("owner-a", action)
        with self.assertRaises(PermissionError):
            manager.get_approval("owner-b", pending["approval_id"])
        manager.approve("owner-a", pending["approval_id"])
        changed = {"integration": "gmail", "action": "send_email", "parameters": {"to": "attacker@example.com"}}
        with self.assertRaises(PermissionError):
            manager.consume_approval("owner-a", pending["approval_id"], changed)
        manager.close()

    def test_workflow_survives_restart_and_does_not_replay_inflight_action(self):
        approvals = ApprovalManager(database_path=self.db)
        workflow = WorkflowManager(FakeExecution(approvals), database_path=self.db)
        state = {
            "workflow_id": "wf-1", "user_id": "owner-a", "steps": [
                {"integration": "gmail", "action": "send_email", "parameters": {"to": "a@example.com"}}
            ], "current_step": 0, "results": [], "status": "awaiting_approval",
            "pending_approval": {"approval_id": "approval-1", "action_data": {}},
            "origin_goal_id": None, "origin_run_id": None,
        }
        with workflow.db:
            workflow._save(state)
        workflow.close()
        restarted = WorkflowManager(FakeExecution(approvals), database_path=self.db)
        self.assertEqual(restarted.get_workflow("owner-a", "wf-1")["status"], "awaiting_approval")
        with self.assertRaises(ValueError):
            restarted.get_workflow("owner-b", "wf-1")
        restarted.close()
        approvals.close()

    def test_approval_pauses_and_resolves_original_goal_run(self):
        repository = GoalRepository(self.db)
        bridge = AutonomyApprovalBridge(self.db)
        with identity_scope(self.identity):
            goal = repository.create_goal("Send a report")
            repository.request_run(goal["goal_id"])
            claim = repository.claim_due()[0]
            paused = bridge.pause_run_for_approval(claim["run_id"], goal["goal_id"], "workflow-1")
            self.assertEqual(paused["status"], "awaiting_approval")
            self.assertEqual(repository.get_goal(goal["goal_id"])["status"], "awaiting_approval")
            result = bridge.complete_workflow("workflow-1", "completed", {"sent": True})
            self.assertEqual(result["run_id"], claim["run_id"])
            self.assertEqual(repository.list_runs(goal["goal_id"])[0]["status"], "completed")
            self.assertEqual(repository.get_goal(goal["goal_id"])["status"], "completed")

    def test_bridge_recovers_orphaned_pending_workflow_after_restart(self):
        repository = GoalRepository(self.db)
        bridge = AutonomyApprovalBridge(self.db)
        with identity_scope(self.identity):
            goal = repository.create_goal("Send a report")
            repository.request_run(goal["goal_id"])
            claim = repository.claim_due()[0]
        import json
        with sqlite3.connect(self.db) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, state_json TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            state = {
                "workflow_id": "orphan-workflow", "user_id": "owner-a",
                "origin_goal_id": goal["goal_id"], "origin_run_id": claim["run_id"],
                "status": "awaiting_approval", "steps": [], "current_step": 0,
                "results": [], "pending_approval": {"approval_id": "approval-1"},
            }
            db.execute("INSERT INTO workflows(workflow_id,user_id,state_json,status) VALUES(?,?,?,?)",
                       ("orphan-workflow", "owner-a", json.dumps(state), "awaiting_approval"))
        recovered = bridge.recover_workflows()
        self.assertEqual(recovered[0]["status"], "awaiting_approval")
        with identity_scope(self.identity):
            self.assertEqual(repository.get_goal(goal["goal_id"])["status"], "awaiting_approval")

    def test_bridge_rejects_other_tenant(self):
        repository = GoalRepository(self.db)
        bridge = AutonomyApprovalBridge(self.db)
        with identity_scope(self.identity):
            goal = repository.create_goal("Send a report")
            repository.request_run(goal["goal_id"])
            claim = repository.claim_due()[0]
            bridge.pause_run_for_approval(claim["run_id"], goal["goal_id"], "workflow-1")
        with identity_scope(self.other):
            self.assertIsNone(bridge.complete_workflow("workflow-1", "completed", {}))
        with identity_scope(self.identity):
            self.assertEqual(repository.get_goal(goal["goal_id"])["status"], "awaiting_approval")


if __name__ == "__main__":
    unittest.main()
