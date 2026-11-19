import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("PAAI_AUTH_SECRET", "test-secret-for-import-only-1234567890")

from fastapi.testclient import TestClient
from unittest.mock import patch
from app.api.main import create_app
from app.runtime.multi_user_runtime import MultiUserRuntime

class FakeApprovalConnector:
    name = "demo"

    def get_supported_actions(self):
        return ["create"]

    def execute(self, action, parameters, credentials=None):
        return {"created": parameters.get("name")}


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
                dashboard = client.get("/")
                self.assertEqual(dashboard.status_code, 200)
                self.assertIn("PAAI", dashboard.text)
                dashboard_script = client.get("/dashboard/app.js")
                self.assertEqual(dashboard_script.status_code, 200)
                self.assertIn("api/v1/auth", dashboard_script.text)
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

                runtime.phase5_runtime["integration_registry"].register(FakeApprovalConnector())
                granted = client.post(
                    "/api/v1/permissions",
                    headers={"Authorization": "Bearer " + token_a},
                    json={"integration": "demo", "action": "create"},
                )
                self.assertEqual(granted.status_code, 201)
                with patch(
                    "app.agents.integration_workflow_agent.generate_response",
                    return_value='{"goal":"Create a demo item","steps":[{"integration":"demo","action":"create","parameters":{"name":"approved-item"}}]}',
                ):
                    pending_workflow = client.post(
                        "/api/v1/workflows",
                        headers={"Authorization": "Bearer " + token_a},
                        json={"request": "Create a demo item"},
                    )
                self.assertEqual(pending_workflow.status_code, 202)
                pending_data = pending_workflow.json()["workflow"]
                self.assertEqual(pending_data["status"], "awaiting_approval")
                pending_for_owner = client.get(
                    "/api/v1/workflows/pending",
                    headers={"Authorization": "Bearer " + token_a},
                )
                self.assertEqual(pending_for_owner.status_code, 200)
                self.assertEqual(len(pending_for_owner.json()), 1)
                pending_for_other = client.get(
                    "/api/v1/workflows/pending",
                    headers={"Authorization": "Bearer " + token_b},
                )
                self.assertEqual(pending_for_other.status_code, 200)
                self.assertEqual(pending_for_other.json(), [])
                approval_id = pending_data["pending_approval"]["approval_id"]
                resumed = client.post(
                    "/api/v1/workflows/" + pending_data["workflow_id"] + "/approve",
                    headers={"Authorization": "Bearer " + token_a},
                    json={"approval_id": approval_id},
                )
                self.assertEqual(resumed.status_code, 200)
                self.assertEqual(resumed.json()["status"], "completed")
                unauthenticated = client.get("/api/v1/goals")
                self.assertEqual(unauthenticated.status_code, 401)
