from copy import deepcopy


class ExecutionManager:

    def __init__(
        self,
        integration_registry,
        credential_manager,
        permission_manager,
        risk_evaluator,
        approval_manager,
        audit_logger,
        oauth_manager=None
    ):
        self.integration_registry = integration_registry
        self.credential_manager = credential_manager
        self.permission_manager = permission_manager
        self.risk_evaluator = risk_evaluator
        self.approval_manager = approval_manager
        self.audit_logger = audit_logger
        self.oauth_manager = oauth_manager

    def execute(
        self,
        user_id,
        integration,
        action,
        parameters,
        approval_id=None
    ):

        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid authenticated user ID is required.")

        if not isinstance(integration, str) or not integration.strip():
            raise ValueError("Valid integration name is required.")

        if not isinstance(action, str) or not action.strip():
            raise ValueError("Valid integration action is required.")

        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be a dictionary.")

        integration = integration.strip().lower()
        action = action.strip().lower()

        connector = self.integration_registry.get(integration)
        supported_actions = connector.get_supported_actions()

        if action not in supported_actions:
            raise ValueError("Unsupported integration action.")

        if not self.permission_manager.is_allowed(
            user_id, integration, action
        ):
            raise PermissionError("User does not have permission.")

        risk_level = self.risk_evaluator.classify(
            integration, action, parameters
        )

        action_data = {
            "integration": integration,
            "action": action,
            "parameters": deepcopy(parameters)
        }

        approval_status = None

        requires_approval = (
            risk_level == "high"
            or (
                risk_level == "medium"
                and not self.permission_manager.is_automatic_allowed(
                    user_id, integration, action
                )
            )
        )

        if requires_approval:

            if not approval_id:

                approval = self.approval_manager.request_approval(
                    user_id, action_data
                )

                self.audit_logger.log(
                    user_id,
                    integration,
                    action,
                    "awaiting_approval",
                    risk_level,
                    "pending"
                )

                return {
                    "status": "awaiting_approval",
                    "approval_required": True,
                    "approval": approval
                }

            self.approval_manager.consume_approval(
                user_id,
                approval_id,
                action_data
            )

            approval_status = "approved"

        credentials = None

        if self.credential_manager.has_credentials(
            user_id, integration
        ):

            if (
                self.oauth_manager
                and integration in {"gmail", "calendar"}
            ):
                credentials = self.oauth_manager.get_valid_credentials(
                    user_id, integration
                )

            else:
                credentials = self.credential_manager.get_credentials(
                    user_id, integration
                )

        try:

            result = connector.execute(
                action,
                parameters,
                credentials
            )

            self.audit_logger.log(
                user_id,
                integration,
                action,
                "completed",
                risk_level,
                approval_status
            )

            return {
                "status": "completed",
                "approval_required": False,
                "risk_level": risk_level,
                "result": result
            }

        except Exception as error:

            self.audit_logger.log(
                user_id,
                integration,
                action,
                "failed",
                risk_level,
                approval_status,
                type(error).__name__
            )

            raise
