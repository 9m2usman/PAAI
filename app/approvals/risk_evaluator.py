class RiskEvaluator:

    HIGH_RISK_ACTIONS = {
        "send",
        "send_email",
        "delete",
        "delete_record",
        "delete_event",
        "cancel",
        "cancel_event",
        "submit",
        "purchase",
        "pay",
        "transfer",
        "publish"
    }

    MEDIUM_RISK_ACTIONS = {
        "create",
        "create_draft",
        "create_event",
        "update",
        "update_record",
        "update_event",
        "modify",
        "click",
        "fill",
        "create_document"
    }

    LOW_RISK_ACTIONS = {
        "read",
        "list",
        "get",
        "search",
        "retrieve",
        "view",
        "list_emails",
        "read_email",
        "list_events",
        "open_page",
        "extract_text",
        "read_document"
    }

    def classify(self, integration, action, parameters=None):

        if not isinstance(integration, str) or not integration.strip():
            return "high"

        if not isinstance(action, str) or not action.strip():
            return "high"

        integration = integration.strip().lower()
        action = action.strip().lower()

        if action in self.HIGH_RISK_ACTIONS:
            return "high"

        if action in self.MEDIUM_RISK_ACTIONS:
            return "medium"

        if action in self.LOW_RISK_ACTIONS:
            return "low"

        return "high"

    def requires_approval(self, risk_level):
        return risk_level in {"medium", "high"}