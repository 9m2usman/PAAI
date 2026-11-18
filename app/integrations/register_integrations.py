
from app.integrations.integration_registry import IntegrationRegistry
from app.integrations.gmail.gmail_connector import GmailConnector
from app.integrations.calendar.calendar_connector import CalendarConnector
from app.integrations.browser.browser_connector import BrowserConnector
from app.integrations.google_oauth import GoogleOAuthManager

from app.security.credential_manager import CredentialManager
from app.security.permission_manager import PermissionManager

from app.approvals.approval_manager import ApprovalManager
from app.approvals.risk_evaluator import RiskEvaluator

from app.execution.execution_manager import ExecutionManager
from app.execution.audit_logger import AuditLogger

from app.workflows.workflow_manager import WorkflowManager
from app.tools.integration_tool import IntegrationToolAdapter


def create_phase5_runtime(google_oauth_config=None, enable_browser=False):

    integration_registry = IntegrationRegistry()
    credential_manager = CredentialManager()
    permission_manager = PermissionManager()
    approval_manager = ApprovalManager()
    risk_evaluator = RiskEvaluator()
    audit_logger = AuditLogger()

    oauth_manager = None

    if google_oauth_config:
        oauth_manager = GoogleOAuthManager(
            client_id=google_oauth_config["client_id"],
            client_secret=google_oauth_config["client_secret"],
            redirect_uri=google_oauth_config["redirect_uri"],
            credential_manager=credential_manager
        )

    integration_registry.register(GmailConnector())
    integration_registry.register(CalendarConnector())

    if enable_browser:
        integration_registry.register(BrowserConnector())

    execution_manager = ExecutionManager(
        integration_registry=integration_registry,
        credential_manager=credential_manager,
        permission_manager=permission_manager,
        approval_manager=approval_manager,
        risk_evaluator=risk_evaluator,
        audit_logger=audit_logger,
        oauth_manager=oauth_manager
    )

    workflow_manager = WorkflowManager(
        execution_manager=execution_manager,
        approval_manager=approval_manager
    )

    integration_tool = IntegrationToolAdapter(execution_manager)

    return {
        "integration_registry": integration_registry,
        "credential_manager": credential_manager,
        "permission_manager": permission_manager,
        "approval_manager": approval_manager,
        "risk_evaluator": risk_evaluator,
        "audit_logger": audit_logger,
        "oauth_manager": oauth_manager,
        "execution_manager": execution_manager,
        "workflow_manager": workflow_manager,
        "integration_tool": integration_tool
    }
