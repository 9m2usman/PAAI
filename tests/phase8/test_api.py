import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("PAAI_AUTH_SECRET", "test-secret-for-import-only-1234567890")

from fastapi.testclient import TestClient
from app.api.main import create_app
from app.runtime.multi_user_runtime import MultiUserRuntime

class ApiTests(unittest.TestCase):
    def test_authenticated_api_and_tenant_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = MultiUserRuntime(
                auth_database=str(Path(folder) / "auth.db"),
                token_secret="api-test-secret-" * 3,
                memory_database=str(Path(folder) / "memory.db"),
                autonomy_database=str(Path(folder) / "autonomy.db"),
            )
            settings = SimpleNamespace(
                log_level="ERROR",
                docs_enabled=False,
                max_request_bytes=100000,
                requests_per_minute=100,
                cors_origins=[],
            )
            app = create_app(runtime=runtime, settings=settings)
            with TestClient(app) as client:
                first = client.post("/api/v1/auth/register", json={
                    "email": "first@example.com",
                    "password": "a-secure-password-123",
                })
                second = client.post("/api/v1/auth/register", json={
                    "email": "second@example.com",
                    "password": "another-secure-password-123",
                })
                self.assertEqual(first.status_code, 201)
                self.assertEqual(second.status_code, 201)
                token_a = first.json()["access_token"]
                token_b = second.json()["access_token"]
                me = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token_a})
                self.assertEqual(me.json()["email"], "first@example.com")
                created = client.post(
                    "/api/v1/goals",
                    headers={"Authorization": "Bearer " + token_a},
                    json={"description": "Summarize my notes"},
                )
                self.assertEqual(created.status_code, 201)
                goal_id = created.json()["goal_id"]
                denied = client.get(
                    "/api/v1/goals/" + goal_id,
                    headers={"Authorization": "Bearer " + token_b},
                )
                self.assertEqual(denied.status_code, 404)

                event_goal = client.post(
                    "/api/v1/goals",
                    headers={"Authorization": "Bearer " + token_a},
                    json={"description": "Process incoming reports", "event_type": "report.ready"},
                )
                self.assertEqual(event_goal.status_code, 201)
                event_headers = {"Authorization": "Bearer " + token_a}
                event = client.post(
                    "/api/v1/events",
                    headers=event_headers,
                    json={"event_id": "report-001", "event_type": "report.ready", "payload": {"report_id": "r-1"}},
                )
                self.assertEqual(event.status_code, 202)
                self.assertEqual(event.json()["matched_goals"], 1)
                duplicate = client.post(
                    "/api/v1/events",
                    headers=event_headers,
                    json={"event_id": "report-001", "event_type": "report.ready", "payload": {"report_id": "r-1"}},
                )
                self.assertTrue(duplicate.json()["duplicate"])
                other_tenant_event = client.post(
                    "/api/v1/events",
                    headers={"Authorization": "Bearer " + token_b},
                    json={"event_id": "report-001", "event_type": "report.ready", "payload": {"report_id": "other"}},
                )
                self.assertEqual(other_tenant_event.json()["matched_goals"], 0)
                unauthenticated = client.get("/api/v1/goals")
                self.assertEqual(unauthenticated.status_code, 401)
