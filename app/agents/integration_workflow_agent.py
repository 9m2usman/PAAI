import json
from app.core.llm_client import generate_response


class IntegrationWorkflowAgent:
    MAX_WORKFLOW_STEPS = 10
    ACTION_GUIDANCE = {
        "gmail": {
            "list_emails": "Optional parameters: max_results (integer 1-100), query (Gmail search text).",
            "read_email": "Required parameter: message_id (string).",
            "create_draft": "Required parameters: to, subject, body (strings).",
            "send_email": "Required parameters: to, subject, body (strings). Sending always requires human approval."
        },
        "calendar": {
            "list_events": "Optional parameters: max_results (integer), time_min, time_max (RFC3339 strings).",
            "create_event": "Required parameter: event object containing summary, start, and end. Creating requires approval unless automatic permission is enabled.",
            "update_event": "Required parameters: event_id (string), event (non-empty object). Updating requires approval unless automatic permission is enabled.",
            "delete_event": "Required parameter: event_id (string). Deleting always requires human approval."
        },
        "browser": {
            "open_page": "Required parameter: url (HTTPS URL on an explicitly allowlisted domain).",
            "extract_text": "No parameters. Reads text from the current allowlisted page.",
            "click": "Required parameter: selector (string). Clicking always requires human approval.",
            "fill": "Required parameters: selector and value (strings)."
        }
    }

    def __init__(self, workflow_manager, integration_registry):
        if workflow_manager is None or integration_registry is None:
            raise ValueError("Workflow manager and integration registry are required.")
        self.workflow_manager = workflow_manager
        self.integration_registry = integration_registry

    def _get_action_catalog(self):
        catalog = {}
        for integration in self.integration_registry.list_integrations():
            connector = self.integration_registry.get(integration)
            catalog[integration] = {}
            for action in connector.get_supported_actions():
                catalog[integration][action] = self.ACTION_GUIDANCE.get(integration, {}).get(
                    action, "Provide the parameters required by this action.")
        return catalog

    def _create_plan(self, user_request):
        catalog = self._get_action_catalog()
        messages = [
            {"role": "system", "content": (
                "You are PAAI's real-world workflow planner. Convert the user's request into an ordered workflow "
                "using only exact integrations/actions in the catalog. Return only JSON with goal and steps; "
                "each step has integration, action, parameters. Do not include user IDs, approval IDs, credentials, "
                "tokens, or extra fields. Never invent actions. Use no more than "
                f"{self.MAX_WORKFLOW_STEPS} steps. If no integration action is needed, return empty steps.")},
            {"role": "user", "content": "Available integration action catalog:\n" +
             json.dumps(catalog, indent=2) + "\n\nUser request:\n" + user_request}
        ]
        try:
            plan = json.loads(generate_response(messages))
        except (json.JSONDecodeError, TypeError):
            raise ValueError("The workflow planner returned invalid JSON.") from None
        return self._validate_plan(plan, catalog)

    def _validate_plan(self, plan, catalog):
        if not isinstance(plan, dict) or set(plan) != {"goal", "steps"}:
            raise ValueError("Workflow plan contains missing or unexpected fields.")
        if not isinstance(plan["goal"], str) or not plan["goal"].strip():
            raise ValueError("Workflow plan must contain a goal.")
        steps = plan["steps"]
        if not isinstance(steps, list) or len(steps) > self.MAX_WORKFLOW_STEPS:
            raise ValueError("Workflow steps are invalid or exceed the maximum step limit.")
        validated = []
        for step in steps:
            if not isinstance(step, dict) or set(step) != {"integration", "action", "parameters"}:
                raise ValueError("Workflow step contains missing or unexpected fields.")
            integration, action, parameters = step["integration"], step["action"], step["parameters"]
            if not isinstance(integration, str) or integration not in catalog:
                raise ValueError("Workflow contains an unavailable integration.")
            if not isinstance(action, str) or action not in catalog[integration]:
                raise ValueError("Workflow contains an unsupported integration action.")
            if not isinstance(parameters, dict):
                raise ValueError("Workflow action parameters must be an object.")
            validated.append({"integration": integration, "action": action, "parameters": parameters})
        return {"goal": plan["goal"].strip(), "steps": validated}

    def run(self, authenticated_user_id, user_request, origin_goal_id=None, origin_run_id=None):
        if not isinstance(authenticated_user_id, str) or not authenticated_user_id.strip():
            raise ValueError("Authenticated user ID is required.")
        if not isinstance(user_request, str) or not user_request.strip():
            raise ValueError("A valid workflow request is required.")
        plan = self._create_plan(user_request)
        if not plan["steps"]:
            return {"status": "no_actions", "goal": plan["goal"], "workflow": None}
        workflow = self.workflow_manager.run(
            authenticated_user_id, plan["steps"],
            origin_goal_id=origin_goal_id, origin_run_id=origin_run_id)
        return {"status": workflow["status"], "goal": plan["goal"], "workflow": workflow}

    def resume(self, authenticated_user_id, workflow_id, approval_id):
        workflow = self.workflow_manager.resume(authenticated_user_id, workflow_id, approval_id)
        return {"status": workflow["status"], "workflow": workflow}

    def reject(self, authenticated_user_id, workflow_id, approval_id):
        workflow = self.workflow_manager.reject(authenticated_user_id, workflow_id, approval_id)
        return {"status": workflow["status"], "workflow": workflow}

    def run_for_current_identity(self, user_request, origin_goal_id=None, origin_run_id=None):
        from app.identity.context import current_identity
        return self.run(current_identity().user_id, user_request, origin_goal_id, origin_run_id)

    def resume_for_current_identity(self, workflow_id, approval_id):
        from app.identity.context import current_identity
        return self.resume(current_identity().user_id, workflow_id, approval_id)

    def reject_for_current_identity(self, workflow_id, approval_id):
        from app.identity.context import current_identity
        return self.reject(current_identity().user_id, workflow_id, approval_id)
