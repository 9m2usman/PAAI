import unittest
import tempfile
from pathlib import Path
from urllib.request import Request
from urllib.error import HTTPError
from unittest.mock import patch

from app.approvals.approval_manager import ApprovalManager
from app.approvals.risk_evaluator import RiskEvaluator
from app.execution.audit_logger import AuditLogger
from app.execution.execution_manager import ExecutionManager
from app.integrations.api_connector import APIConnector, _NoRedirectHandler
from app.integrations.gmail.gmail_connector import GmailConnector
from app.integrations.calendar.calendar_connector import CalendarConnector
from app.documents.document_processor import DocumentProcessor
from app.integrations.browser.browser_connector import BrowserConnector
from app.integrations.google_oauth import GoogleOAuthManager
from app.integrations.integration_registry import IntegrationRegistry
from app.security.credential_manager import CredentialManager
from app.security.permission_manager import PermissionManager
from app.tools.integration_tool import IntegrationToolAdapter
from app.workflows.workflow_manager import WorkflowManager
from app.agents.integration_workflow_agent import IntegrationWorkflowAgent
from app.integrations.register_integrations import (
    create_phase5_runtime,
    close_phase5_runtime
)


class FakeConnector:

    name = "demo"

    def __init__(self):
        self.calls = []

    def get_supported_actions(self):
        return ["read", "create", "send_email"]

    def execute(self, action, parameters, credentials=None):
        self.calls.append((action, parameters))
        return {"action": action, "parameters": parameters}


class FakeWorkflowManager:

    def __init__(self, result=None):
        self.result = result or {"status": "completed"}
        self.run_arguments = None
        self.resume_arguments = None
        self.reject_arguments = None

    def run(self, user_id, steps):
        self.run_arguments = (user_id, steps)
        return self.result

    def resume(self, user_id, workflow_id, approval_id):
        self.resume_arguments = (user_id, workflow_id, approval_id)
        return {"status": "completed"}

    def reject(self, user_id, workflow_id, approval_id):
        self.reject_arguments = (user_id, workflow_id, approval_id)
        return {"status": "rejected"}


class FakeBrowserDriver:

    def __init__(self, final_url="https://example.com/home"):
        self.url = final_url
        self.redirect_to = None
        self.allowed_domains = set()

    def set_allowed_domains(self, domains):
        self.allowed_domains = set(domains)

    def open_page(self, url):
        self.url = self.redirect_to or url
        return {"url": self.url, "status": 200, "title": "Example"}

    def current_url(self):
        return self.url

    def extract_text(self):
        return "Example page"

    def click(self, selector):
        return {"status": "clicked", "selector": selector}

    def fill(self, selector, value):
        return {"status": "filled", "selector": selector, "value": value}


class TestApprovalExpiry(unittest.TestCase):

    def setUp(self):
        self.manager = ApprovalManager(approval_ttl_seconds=10)
        self.action = {
            "integration": "gmail",
            "action": "send_email",
            "parameters": {"to": "user@example.com"}
        }

    def test_approval_contains_expiry(self):
        approval = self.manager.request_approval("user_a", self.action)
        self.assertGreater(approval["expires_at"], approval["created_at"])

    def test_expired_approval_cannot_be_approved(self):
        with patch("app.approvals.approval_manager.time.time", return_value=100):
            approval = self.manager.request_approval("user_a", self.action)

        with patch("app.approvals.approval_manager.time.time", return_value=111):
            with self.assertRaisesRegex(ValueError, "expired"):
                self.manager.approve("user_a", approval["approval_id"])

    def test_expired_approved_action_cannot_be_consumed(self):
        with patch("app.approvals.approval_manager.time.time", return_value=100):
            approval = self.manager.request_approval("user_a", self.action)
            self.manager.approve("user_a", approval["approval_id"])

        with patch("app.approvals.approval_manager.time.time", return_value=111):
            with self.assertRaisesRegex(PermissionError, "expired"):
                self.manager.consume_approval(
                    "user_a", approval["approval_id"], self.action
                )

    def test_approval_remains_bound_to_exact_action(self):
        approval = self.manager.request_approval("user_a", self.action)
        self.manager.approve("user_a", approval["approval_id"])

        changed_action = {
            "integration": "gmail",
            "action": "send_email",
            "parameters": {"to": "attacker@example.com"}
        }

        with self.assertRaisesRegex(PermissionError, "changed"):
            self.manager.consume_approval(
                "user_a", approval["approval_id"], changed_action
            )

    def test_other_user_cannot_approve(self):
        approval = self.manager.request_approval("user_a", self.action)

        with self.assertRaises(PermissionError):
            self.manager.approve("user_b", approval["approval_id"])


class TestGoogleOAuthState(unittest.TestCase):

    def setUp(self):
        self.credentials = CredentialManager()
        self.oauth = GoogleOAuthManager(
            "client-id",
            "client-secret",
            "https://localhost/callback",
            self.credentials
        )

    def test_state_is_bound_to_user(self):
        url = self.oauth.create_authorization_url("user_a")
        state = url.split("state=")[-1]

        with self.assertRaises(PermissionError):
            self.oauth.exchange_code("user_b", "auth-code", state)

    def test_expired_state_is_rejected(self):
        with patch("app.integrations.google_oauth.time.time", return_value=100):
            url = self.oauth.create_authorization_url("user_a")

        state = url.split("state=")[-1]

        with patch("app.integrations.google_oauth.time.time", return_value=701):
            with self.assertRaisesRegex(PermissionError, "expired"):
                self.oauth.exchange_code("user_a", "auth-code", state)

    def test_failed_exchange_still_consumes_state(self):
        url = self.oauth.create_authorization_url("user_a")
        state = url.split("state=")[-1]

        with patch.object(
            self.oauth,
            "_send_token_request",
            side_effect=RuntimeError("Token endpoint failed.")
        ):
            with self.assertRaises(RuntimeError):
                self.oauth.exchange_code("user_a", "auth-code", state)

        self.assertNotIn(state, self.oauth.pending_states)

    def test_successful_exchange_consumes_state(self):
        url = self.oauth.create_authorization_url("user_a")
        state = url.split("state=")[-1]

        with patch.object(
            self.oauth,
            "_send_token_request",
            return_value={
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_in": 3600
            }
        ):
            result = self.oauth.exchange_code(
                "user_a", "auth-code", state
            )

        self.assertEqual(result["status"], "connected")
        self.assertTrue(self.credentials.has_credentials("user_a", "gmail"))
        self.assertTrue(self.credentials.has_credentials("user_a", "calendar"))
        self.assertNotIn(state, self.oauth.pending_states)


class TestBrowserDomainSecurity(unittest.TestCase):

    def setUp(self):
        self.driver = FakeBrowserDriver()
        self.connector = BrowserConnector(
            self.driver,
            ["example.com"]
        )

    def test_allowed_https_domain_is_accepted(self):
        result = self.connector.execute(
            "open_page",
            {"url": "https://www.example.com"}
        )
        self.assertEqual(result["status"], 200)

    def test_untrusted_domain_is_rejected(self):
        with self.assertRaises(PermissionError):
            self.connector.execute(
                "open_page",
                {"url": "https://evil-example.com"}
            )

    def test_http_is_rejected(self):
        with self.assertRaises(ValueError):
            self.connector.execute(
                "open_page",
                {"url": "http://example.com"}
            )

    def test_nonstandard_https_port_is_rejected(self):
        with self.assertRaises(ValueError):
            self.connector.execute(
                "open_page",
                {"url": "https://example.com:8443"}
            )

    def test_redirect_to_untrusted_domain_is_rejected(self):
        self.driver.redirect_to = "https://attacker.invalid"
        with self.assertRaises(PermissionError):
            self.connector.execute(
                "open_page",
                {"url": "https://example.com"}
            )


class TestAPIConnectorValidation(unittest.TestCase):

    def setUp(self):
        self.api = APIConnector(
            name="test_api",
            base_url="https://api.example.com"
        )

    def test_relative_path_is_accepted(self):
        target = self.api._build_target("v1/items", {"page": 1})
        self.assertEqual(
            target,
            "https://api.example.com/v1/items?page=1"
        )

    def test_absolute_url_is_rejected(self):
        with self.assertRaises(ValueError):
            self.api._build_target(
                "https://attacker.invalid/steal",
                {}
            )

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            self.api._build_target("../admin", {})

    def test_double_encoded_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            self.api._build_target("%252e%252e%252fadmin", {})

    def test_non_https_base_url_is_rejected(self):
        with self.assertRaises(ValueError):
            APIConnector("unsafe", "http://api.example.com")

    def test_redirect_handler_rejects_redirects(self):
        request = Request("https://api.example.com/data")
        handler = _NoRedirectHandler()

        with self.assertRaises(HTTPError):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://attacker.invalid/data"
            )


class TestGmailConnector(unittest.TestCase):

    def setUp(self):
        self.connector = GmailConnector()
        self.credentials = {"access_token": "test-token"}

    def test_list_emails_builds_expected_api_request(self):
        with patch.object(
            self.connector.api,
            "execute",
            return_value={"messages": []}
        ) as mock_execute:
            self.connector.execute(
                "list_emails",
                {"max_results": 5, "query": "is:unread"},
                self.credentials
            )

        args = mock_execute.call_args.args
        self.assertEqual(args[0], "read")
        self.assertEqual(
            args[1]["path"],
            "gmail/v1/users/me/messages"
        )
        self.assertEqual(args[1]["query"]["maxResults"], 5)
        self.assertEqual(args[1]["query"]["q"], "is:unread")

    def test_read_email_encodes_message_id_as_one_path_segment(self):
        with patch.object(
            self.connector.api,
            "execute",
            return_value={"id": "abc/def"}
        ) as mock_execute:
            self.connector.execute(
                "read_email",
                {"message_id": "abc/def"},
                self.credentials
            )

        path = mock_execute.call_args.args[1]["path"]
        self.assertTrue(path.endswith("abc%2Fdef"))

    def test_create_draft_uses_drafts_endpoint(self):
        with patch.object(
            self.connector.api,
            "execute",
            return_value={"id": "draft-1"}
        ) as mock_execute:
            self.connector.execute(
                "create_draft",
                {
                    "to": "person@example.com",
                    "subject": "Hello",
                    "body": "Draft body"
                },
                self.credentials
            )

        self.assertEqual(
            mock_execute.call_args.args[1]["path"],
            "gmail/v1/users/me/drafts"
        )

    def test_send_email_uses_send_endpoint(self):
        with patch.object(
            self.connector.api,
            "execute",
            return_value={"id": "sent-1"}
        ) as mock_execute:
            self.connector.execute(
                "send_email",
                {
                    "to": "person@example.com",
                    "subject": "Hello",
                    "body": "Email body"
                },
                self.credentials
            )

        self.assertEqual(
            mock_execute.call_args.args[1]["path"],
            "gmail/v1/users/me/messages/send"
        )

    def test_invalid_list_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            self.connector.execute(
                "list_emails",
                {"max_results": 1000},
                self.credentials
            )


class TestCalendarConnector(unittest.TestCase):

    def setUp(self):
        self.connector = CalendarConnector()
        self.credentials = {"access_token": "test-token"}

    def test_list_events_uses_calendar_endpoint(self):
        with patch.object(
            self.connector.api,
            "execute",
            return_value={"items": []}
        ) as mock_execute:
            self.connector.execute(
                "list_events",
                {"max_results": 3},
                self.credentials
            )

        self.assertEqual(mock_execute.call_args.args[0], "read")
        self.assertEqual(
            mock_execute.call_args.args[1]["path"],
            "calendar/v3/calendars/primary/events"
        )

    def test_create_event_validates_required_fields(self):
        with self.assertRaises(ValueError):
            self.connector.execute(
                "create_event",
                {"event": {"summary": "Missing dates"}},
                self.credentials
            )

    def test_create_event_uses_post_mapping(self):
        with patch.object(
            self.connector.api,
            "execute",
            return_value={"id": "event-1"}
        ) as mock_execute:
            self.connector.execute(
                "create_event",
                {
                    "event": {
                        "summary": "Meeting",
                        "start": {"dateTime": "2026-11-20T10:00:00Z"},
                        "end": {"dateTime": "2026-11-20T10:30:00Z"}
                    }
                },
                self.credentials
            )

        self.assertEqual(mock_execute.call_args.args[0], "create")

    def test_update_event_encodes_event_id(self):
        with patch.object(
            self.connector.api,
            "execute",
            return_value={"id": "event/1"}
        ) as mock_execute:
            self.connector.execute(
                "update_event",
                {
                    "event_id": "event/1",
                    "event": {"summary": "Updated"}
                },
                self.credentials
            )

        path = mock_execute.call_args.args[1]["path"]
        self.assertTrue(path.endswith("event%2F1"))

    def test_delete_event_uses_delete_mapping(self):
        with patch.object(
            self.connector.api,
            "execute",
            return_value={"status_code": 204}
        ) as mock_execute:
            self.connector.execute(
                "delete_event",
                {"event_id": "event-1"},
                self.credentials
            )

        self.assertEqual(mock_execute.call_args.args[0], "delete")


class TestDocumentProcessor(unittest.TestCase):

    def test_create_and_read_document(self):
        with tempfile.TemporaryDirectory() as directory:
            processor = DocumentProcessor(directory)

            processor.create_document(
                "notes.md",
                "Phase 5 document"
            )

            result = processor.read_document("notes.md")

            self.assertEqual(result["content"], "Phase 5 document")

    def test_path_traversal_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            processor = DocumentProcessor(directory)

            with self.assertRaises(PermissionError):
                processor.read_document("../outside.txt")

    def test_unsupported_format_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            processor = DocumentProcessor(directory)

            with self.assertRaises(ValueError):
                processor.read_document("payload.exe")

    def test_oversized_document_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            processor = DocumentProcessor(
                directory,
                max_file_size=5
            )

            path = Path(directory) / "large.txt"
            path.write_text("This is too large.", encoding="utf-8")

            with self.assertRaises(ValueError):
                processor.read_document("large.txt")


class TestIntegrationExecution(unittest.TestCase):

    def setUp(self):
        self.registry = IntegrationRegistry()
        self.registry.register(FakeConnector())
        self.credentials = CredentialManager()
        self.permissions = PermissionManager()
        self.approvals = ApprovalManager()
        self.risk = RiskEvaluator()
        self.audit = AuditLogger()

        self.execution = ExecutionManager(
            integration_registry=self.registry,
            credential_manager=self.credentials,
            permission_manager=self.permissions,
            approval_manager=self.approvals,
            risk_evaluator=self.risk,
            audit_logger=self.audit
        )

    def test_read_requires_permission_and_executes(self):
        self.permissions.grant_permission(
            "user_a", "demo", ["read"]
        )

        result = self.execution.execute(
            "user_a", "demo", "read", {"query": "hello"}
        )

        self.assertEqual(result["status"], "completed")

    def test_high_risk_action_always_requires_approval(self):
        self.permissions.grant_permission(
            "user_a", "demo", ["send_email"]
        )
        self.permissions.grant_automatic_permission(
            "user_a", "demo", "send_email"
        )

        result = self.execution.execute(
            "user_a", "demo", "send_email", {"to": "user@example.com"}
        )

        self.assertEqual(result["status"], "awaiting_approval")

    def test_medium_risk_requires_approval_without_auto_permission(self):
        self.permissions.grant_permission(
            "user_a", "demo", ["create"]
        )

        result = self.execution.execute(
            "user_a", "demo", "create", {"name": "draft"}
        )

        self.assertEqual(result["status"], "awaiting_approval")

    def test_medium_risk_runs_with_explicit_automatic_permission(self):
        self.permissions.grant_permission(
            "user_a", "demo", ["create"]
        )
        self.permissions.grant_automatic_permission(
            "user_a", "demo", "create"
        )

        result = self.execution.execute(
            "user_a", "demo", "create", {"name": "draft"}
        )

        self.assertEqual(result["status"], "completed")

    def test_low_risk_runs_without_approval(self):
        self.permissions.grant_permission(
            "user_a", "demo", ["read"]
        )

        result = self.execution.execute(
            "user_a", "demo", "read", {}
        )

        self.assertEqual(result["status"], "completed")

    def test_high_risk_executes_only_after_approval(self):
        self.permissions.grant_permission(
            "user_a", "demo", ["send_email"]
        )

        pending = self.execution.execute(
            "user_a", "demo", "send_email", {"to": "person@example.com"}
        )

        self.assertEqual(pending["status"], "awaiting_approval")
        self.assertEqual(self.registry.get("demo").calls, [])

        approval_id = pending["approval"]["approval_id"]
        self.approvals.approve("user_a", approval_id)

        completed = self.execution.execute(
            "user_a",
            "demo",
            "send_email",
            {"to": "person@example.com"},
            approval_id=approval_id
        )

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(len(self.registry.get("demo").calls), 1)

    def test_user_permissions_are_isolated(self):
        self.permissions.grant_permission(
            "user_a", "demo", ["read"]
        )

        with self.assertRaises(PermissionError):
            self.execution.execute(
                "user_b", "demo", "read", {}
            )

    def test_unknown_action_is_high_risk(self):
        self.assertEqual(
            self.risk.classify("demo", "unlisted_action", {}),
            "high"
        )

    def test_browser_click_is_high_risk(self):
        self.assertEqual(
            self.risk.classify("browser", "click", {"selector": "button"}),
            "high"
        )


class TestWorkflowApproval(unittest.TestCase):

    def setUp(self):
        registry = IntegrationRegistry()
        registry.register(FakeConnector())

        self.permissions = PermissionManager()
        self.approvals = ApprovalManager()
        self.risk = RiskEvaluator()
        self.audit = AuditLogger()

        execution = ExecutionManager(
            integration_registry=registry,
            credential_manager=CredentialManager(),
            permission_manager=self.permissions,
            approval_manager=self.approvals,
            risk_evaluator=self.risk,
            audit_logger=self.audit
        )

        self.workflow = WorkflowManager(execution)

    def test_workflow_pauses_and_resumes_after_approval(self):
        self.permissions.grant_permission(
            "user_a", "demo", ["create"]
        )

        paused = self.workflow.run(
            "user_a",
            [{
                "integration": "demo",
                "action": "create",
                "parameters": {"name": "draft"}
            }]
        )

        self.assertEqual(paused["status"], "awaiting_approval")

        approval_id = paused["pending_approval"]["approval_id"]
        self.approvals.approve("user_a", approval_id)

        completed = self.workflow.resume(
            "user_a", paused["workflow_id"], approval_id
        )

        self.assertEqual(completed["status"], "completed")

    def test_rejection_records_actual_risk_level(self):
        self.permissions.grant_permission(
            "user_a", "demo", ["create"]
        )

        paused = self.workflow.run(
            "user_a",
            [{
                "integration": "demo",
                "action": "create",
                "parameters": {"name": "draft"}
            }]
        )

        approval_id = paused["pending_approval"]["approval_id"]

        rejected = self.workflow.reject(
            "user_a", paused["workflow_id"], approval_id
        )

        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(self.workflow.execution_manager.integration_registry.get("demo").calls, [])
        records = self.audit.get_user_records("user_a")
        self.assertEqual(records[-1]["risk_level"], "medium")

    def test_workflow_is_user_isolated(self):
        self.permissions.grant_permission(
            "user_a", "demo", ["create"]
        )

        paused = self.workflow.run(
            "user_a",
            [{
                "integration": "demo",
                "action": "create",
                "parameters": {}
            }]
        )

        with self.assertRaises(PermissionError):
            self.workflow.get_workflow("user_b", paused["workflow_id"])


class TestPhase5RuntimeFactory(unittest.TestCase):

    def test_runtime_factory_registers_supported_connectors(self):
        runtime = create_phase5_runtime()

        self.assertEqual(
            set(runtime["integration_registry"].list_integrations()),
            {"gmail", "calendar"}
        )
        self.assertIsInstance(runtime["workflow_manager"], WorkflowManager)
        self.assertIsInstance(runtime["workflow_agent"], IntegrationWorkflowAgent)
        self.assertIsNone(runtime["browser_driver"])

        close_phase5_runtime(runtime)

    def test_browser_requires_explicit_allowlist(self):
        with self.assertRaisesRegex(ValueError, "allowlisted domains"):
            create_phase5_runtime(enable_browser=True)


class TestIntegrationWorkflowAgent(unittest.TestCase):

    def setUp(self):
        self.registry = IntegrationRegistry()
        self.registry.register(FakeConnector())
        self.manager = FakeWorkflowManager()
        self.agent = IntegrationWorkflowAgent(
            self.manager,
            self.registry
        )

    @patch("app.agents.integration_workflow_agent.generate_response")
    def test_agent_validates_plan_and_uses_authenticated_identity(self, mock_response):
        mock_response.return_value = (
            '{"goal":"Read data","steps":['
            '{"integration":"demo","action":"read","parameters":{"query":"latest"}}]}'
        )

        result = self.agent.run(
            "verified_user",
            "Read the latest data."
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(self.manager.run_arguments[0], "verified_user")
        self.assertEqual(
            self.manager.run_arguments[1][0]["parameters"]["query"],
            "latest"
        )

        prompt = mock_response.call_args[0][0]
        self.assertNotIn("verified_user", str(prompt))

    @patch("app.agents.integration_workflow_agent.generate_response")
    def test_model_cannot_inject_user_identity(self, mock_response):
        mock_response.return_value = (
            '{"goal":"Read data","user_id":"attacker","steps":[]}'
        )

        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            self.agent.run("verified_user", "Read data.")

    @patch("app.agents.integration_workflow_agent.generate_response")
    def test_unsupported_action_is_rejected(self, mock_response):
        mock_response.return_value = (
            '{"goal":"Do something","steps":['
            '{"integration":"demo","action":"transfer_money","parameters":{}}]}'
        )

        with self.assertRaisesRegex(ValueError, "unsupported"):
            self.agent.run("verified_user", "Transfer money.")

    @patch("app.agents.integration_workflow_agent.generate_response")
    def test_empty_plan_does_not_start_workflow(self, mock_response):
        mock_response.return_value = '{"goal":"No integration needed","steps":[]}'

        result = self.agent.run(
            "verified_user",
            "Explain what an email is."
        )

        self.assertEqual(result["status"], "no_actions")
        self.assertIsNone(self.manager.run_arguments)

    def test_resume_and_reject_keep_authenticated_identity(self):
        self.agent.resume("verified_user", "workflow-1", "approval-1")
        self.agent.reject("verified_user", "workflow-2", "approval-2")

        self.assertEqual(
            self.manager.resume_arguments,
            ("verified_user", "workflow-1", "approval-1")
        )
        self.assertEqual(
            self.manager.reject_arguments,
            ("verified_user", "workflow-2", "approval-2")
        )


class TestIntegrationToolIdentity(unittest.TestCase):

    def test_user_bound_adapter_does_not_accept_llm_identity(self):

        registry = IntegrationRegistry()
        registry.register(FakeConnector())
        permissions = PermissionManager()
        permissions.grant_permission("trusted_user", "demo", ["read"])

        execution = ExecutionManager(
            integration_registry=registry,
            credential_manager=CredentialManager(),
            permission_manager=permissions,
            approval_manager=ApprovalManager(),
            risk_evaluator=RiskEvaluator(),
            audit_logger=AuditLogger()
        )

        adapter = IntegrationToolAdapter(execution)
        execute_for_user = adapter.for_authenticated_user("trusted_user")

        result = execute_for_user("demo", "read", {})

        self.assertEqual(result["status"], "completed")

        with self.assertRaises(TypeError):
            execute_for_user(
                "demo", "read", {}, authenticated_user_id="attacker"
            )


if __name__ == "__main__":
    unittest.main()
