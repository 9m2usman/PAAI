import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

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
        self.service = GoalService(self.repo)
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
        registry = TriggerRegistry()
        with self.assertRaises(ValueError):
            registry.validate_event("arbitrary.execute", {})
        with self.assertRaises(ValueError):
            registry.validate_event("report.ready", {"large": "x" * 20000})
