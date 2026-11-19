import tempfile
import unittest
from pathlib import Path

from app.auth.token_service import TokenService
from app.identity.context import identity_scope
from app.autonomy.goal_repository import GoalRepository
from app.autonomy.goal_service import GoalService
from app.autonomy.engine import AutonomyEngine
from app.autonomy.triggers import TriggerRegistry


class Phase7Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = GoalRepository(str(Path(self.tmp.name) / "autonomy.db"))
        self.triggers = TriggerRegistry()
        self.service = GoalService(self.repo, trigger_registry=self.triggers)
        tokens = TokenService("g" * 40)
        self.a = tokens.verify_token(tokens.issue_token("a", "a@example.com"))
        self.b = tokens.verify_token(tokens.issue_token("b", "b@example.com"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_user_isolation(self):
        with identity_scope(self.a):
            goal = self.service.create("Review my tasks")
        with identity_scope(self.b):
            self.assertEqual(self.service.list(), [])
            with self.assertRaises(ValueError):
                self.service.get(goal["goal_id"])

    def test_manual_run_and_completion(self):
        with identity_scope(self.a):
            goal = self.service.create("Summarize my notes")
            self.service.run_now(goal["goal_id"])
            engine = AutonomyEngine(self.repo, lambda description, limits: "finished")
            result = engine.run_due_once()
            self.assertEqual(result[0]["status"], "completed")
            self.assertEqual(self.service.get(goal["goal_id"])["status"], "completed")

    def test_recurring_goal_reschedules(self):
        with identity_scope(self.a):
            goal = self.service.create("Daily review", interval_seconds=60)
            self.service.run_now(goal["goal_id"])
            engine = AutonomyEngine(self.repo, lambda description, limits: "ok")
            engine.run_due_once()
            updated = self.service.get(goal["goal_id"])
            self.assertEqual(updated["status"], "active")
            self.assertIsNotNone(updated["next_run_at"])

    def test_pause_and_cancel(self):
        with identity_scope(self.a):
            goal = self.service.create("Monitor")
            self.service.pause(goal["goal_id"])
            self.assertEqual(self.service.get(goal["goal_id"])["status"], "paused")
            self.service.cancel(goal["goal_id"])
            self.assertEqual(self.service.get(goal["goal_id"])["status"], "cancelled")

    def test_policy_and_trigger_validation(self):
        with identity_scope(self.a):
            with self.assertRaises(ValueError):
                self.service.create("Bad schedule", interval_seconds=1)
        with self.assertRaises(ValueError):
            self.triggers.validate_event("arbitrary.execute", {})
        with self.assertRaises(ValueError):
            self.triggers.validate_event("report.ready", {"large": "x" * 20000})


    def test_expired_worker_lease_recovers_abandoned_run(self):
        with identity_scope(self.a):
            goal = self.service.create("Recover after worker crash")
            self.service.run_now(goal["goal_id"])
            first_claim = self.repo.claim_due()[0]
            with self.repo._connect() as db:
                db.execute(
                    "UPDATE autonomy_goals SET lease_expires_at=? WHERE goal_id=?",
                    ("2000-01-01T00:00:00+00:00", goal["goal_id"]),
                )
            second_claim = self.repo.claim_due()[0]
            self.assertNotEqual(first_claim["run_id"], second_claim["run_id"])
            runs = self.repo.list_runs(goal["goal_id"])
            self.assertEqual(runs[0]["status"], "running")
            self.assertEqual(runs[1]["status"], "failed")
            self.assertIn("lease expired", runs[1]["error"])

    def test_event_goal_dispatches_persisted_payload(self):
        with identity_scope(self.a):
            goal = self.service.create(
                "Process the uploaded report",
                event_type="report.ready"
            )
            accepted = self.service.publish_event(
                "event-001", "report.ready", {"report_id": "r-1"}
            )
            self.assertFalse(accepted["duplicate"])
            self.assertEqual(accepted["matched_goals"], 1)
            captured = []
            engine = AutonomyEngine(
                self.repo,
                lambda description, limits: captured.append(limits["event_payload"]) or "processed"
            )
            outcome = engine.run_due_once()
            self.assertEqual(outcome[0]["status"], "completed")
            self.assertEqual(captured[0]["payload"], {"report_id": "r-1"})
            self.assertEqual(captured[0]["event_id"], "event-001")
            self.assertEqual(self.service.get(goal["goal_id"])["status"], "completed")

    def test_event_ingestion_is_idempotent_and_queues_multiple_events(self):
        with identity_scope(self.a):
            goal = self.service.create("Process every report", event_type="report.ready")
            first = self.service.publish_event("event-001", "report.ready", {"n": 1})
            duplicate = self.service.publish_event("event-001", "report.ready", {"n": 1})
            second = self.service.publish_event("event-002", "report.ready", {"n": 2})
            self.assertFalse(first["duplicate"])
            self.assertTrue(duplicate["duplicate"])
            self.assertFalse(second["duplicate"])
            self.assertEqual(second["matched_goals"], 1)

            received = []
            engine = AutonomyEngine(
                self.repo,
                lambda description, limits: received.append(limits["event_payload"]["payload"]["n"]) or "ok"
            )
            self.assertEqual(engine.run_due_once()[0]["status"], "completed")
            self.assertEqual(engine.run_due_once()[0]["status"], "completed")
            self.assertEqual(received, [1, 2])
            self.assertEqual(len(self.service.get(goal["goal_id"])["pending_event_json"] or ""), 0)

    def test_event_goals_are_tenant_isolated(self):
        with identity_scope(self.a):
            goal = self.service.create("Only my event", event_type="report.ready")
        with identity_scope(self.b):
            accepted = self.service.publish_event("event-b-1", "report.ready", {"secret": "b"})
            self.assertEqual(accepted["matched_goals"], 0)
            self.assertEqual(self.service.list(), [])
        with identity_scope(self.a):
            self.assertEqual(self.service.get(goal["goal_id"])["status"], "active")


if __name__ == "__main__":
    unittest.main()
