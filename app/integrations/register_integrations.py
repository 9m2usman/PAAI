import os
from dotenv import load_dotenv
from app.integrations.integration_registry import IntegrationRegistry
from app.integrations.gmail.gmail_connector import GmailConnector
from app.integrations.calendar.calendar_connector import CalendarConnector
from app.integrations.browser.browser_connector import BrowserConnector
from app.integrations.browser.playwright_driver import PlaywrightDriver
from app.integrations.google_oauth import GoogleOAuthManager
from app.security.credential_manager import CredentialManager
from app.security.permission_manager import PermissionManager
from app.approvals.approval_manager import ApprovalManager
from app.approvals.risk_evaluator import RiskEvaluator
from app.execution.execution_manager import ExecutionManager
from app.execution.audit_logger import AuditLogger
from app.workflows.workflow_manager import WorkflowManager
from app.tools.integration_tool import IntegrationToolAdapter
from app.agents.integration_workflow_agent import IntegrationWorkflowAgent


def load_google_oauth_config():
    load_dotenv()
    config = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    }
    configured = [bool(value) for value in config.values()]
    if not any(configured):
        return None
    if not all(configured):
        raise ValueError("Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI together in .env.")
    return config


def create_phase5_runtime(
    google_oauth_config=None, enable_browser=False, browser_allowed_domains=None,
    browser_headless=True, credential_manager=None, permission_manager=None,
    oauth_manager=None, state_database=None
):
    integration_registry = IntegrationRegistry()
    credential_manager = credential_manager or CredentialManager()
    permission_manager = permission_manager or PermissionManager()
    approval_manager = ApprovalManager(database_path=state_database)
    risk_evaluator = RiskEvaluator()
    audit_logger = AuditLogger()
    if google_oauth_config is None:
        google_oauth_config = load_google_oauth_config()
    if google_oauth_config and oauth_manager is None:
        required = {"client_id", "client_secret", "redirect_uri"}
        if not required.issubset(google_oauth_config):
            raise ValueError("Google OAuth configuration is incomplete.")
        oauth_manager = GoogleOAuthManager(
            client_id=google_oauth_config["client_id"],
            client_secret=google_oauth_config["client_secret"],
            redirect_uri=google_oauth_config["redirect_uri"],
            credential_manager=credential_manager)
    integration_registry.register(GmailConnector())
    integration_registry.register(CalendarConnector())
    browser_driver = None
    if enable_browser:
        if not isinstance(browser_allowed_domains, list) or not browser_allowed_domains:
            raise ValueError("Browser allowlisted domains are required when browser is enabled.")
        browser_driver = PlaywrightDriver(headless=browser_headless, allowed_domains=browser_allowed_domains)
        integration_registry.register(BrowserConnector(
            browser_driver=browser_driver, allowed_domains=browser_allowed_domains))
    execution_manager = ExecutionManager(
        integration_registry=integration_registry, credential_manager=credential_manager,
        permission_manager=permission_manager, approval_manager=approval_manager,
        risk_evaluator=risk_evaluator, audit_logger=audit_logger, oauth_manager=oauth_manager)
    workflow_manager = WorkflowManager(execution_manager, database_path=state_database)
    integration_tool = IntegrationToolAdapter(execution_manager)
    workflow_agent = IntegrationWorkflowAgent(workflow_manager, integration_registry)
    return {
        "integration_registry": integration_registry, "credential_manager": credential_manager,
        "permission_manager": permission_manager, "approval_manager": approval_manager,
        "risk_evaluator": risk_evaluator, "audit_logger": audit_logger,
        "oauth_manager": oauth_manager, "execution_manager": execution_manager,
        "workflow_manager": workflow_manager, "integration_tool": integration_tool,
        "workflow_agent": workflow_agent, "browser_driver": browser_driver
    }


def close_phase5_runtime(runtime):
    if not isinstance(runtime, dict):
        raise ValueError("Runtime must be a dictionary.")
    browser_driver = runtime.get("browser_driver")
    if browser_driver is not None:
        browser_driver.close()
    for key in ("workflow_manager", "approval_manager"):
        manager = runtime.get(key)
        if manager is not None and hasattr(manager, "close"):
            manager.close()
