class IntegrationToolAdapter:

    def __init__(self, execution_manager):
        self.execution_manager = execution_manager

    def execute(
        self,
        user_id,
        integration,
        action,
        parameters,
        approval_id=None
    ):

        return self.execution_manager.execute(
            user_id=user_id,
            integration=integration,
            action=action,
            parameters=parameters,
            approval_id=approval_id
        )

    def register_with_registry(self, tool_registry):

        if not isinstance(tool_registry, dict):
            raise ValueError("Tool registry must be a dictionary.")

        if "execute_integration" in tool_registry:
            raise ValueError("Integration tool is already registered.")

        tool_registry["execute_integration"] = self.execute

        return True