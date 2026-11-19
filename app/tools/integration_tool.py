class IntegrationToolAdapter:

    def __init__(self, execution_manager):
        self.execution_manager = execution_manager

    def execute(
        self,
        authenticated_user_id,
        integration,
        action,
        parameters,
        approval_id=None
    ):

        if (
            not isinstance(authenticated_user_id, str)
            or not authenticated_user_id.strip()
        ):
            raise ValueError("Authenticated user ID is required.")

        if not isinstance(integration, str) or not integration.strip():
            raise ValueError("Integration name is required.")

        if not isinstance(action, str) or not action.strip():
            raise ValueError("Integration action is required.")

        if not isinstance(parameters, dict):
            raise ValueError("Integration parameters must be a dictionary.")

        return self.execution_manager.execute(
            user_id=authenticated_user_id,
            integration=integration,
            action=action,
            parameters=parameters,
            approval_id=approval_id
        )

    def for_authenticated_user(self, authenticated_user_id):

        if (
            not isinstance(authenticated_user_id, str)
            or not authenticated_user_id.strip()
        ):
            raise ValueError("Authenticated user ID is required.")

        def execute_for_user(
            integration,
            action,
            parameters,
            approval_id=None
        ):

            return self.execute(
                authenticated_user_id,
                integration,
                action,
                parameters,
                approval_id
            )

        return execute_for_user
