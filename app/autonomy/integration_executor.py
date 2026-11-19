class IntegrationGoalExecutor:
    """Explicitly injected executor that plans goal work through Phase 5 integrations."""

    def __init__(self, workflow_agent):
        if workflow_agent is None:
            raise ValueError("Workflow agent is required.")
        self.workflow_agent = workflow_agent

    def __call__(self, description, limits):
        result = self.workflow_agent.run_for_current_identity(
            description,
            origin_goal_id=limits["goal_id"],
            origin_run_id=limits["run_id"],
        )
        workflow = result.get("workflow")
        if workflow is None:
            return {"status": "completed", "result": result}
        if workflow["status"] == "awaiting_approval":
            return {
                "status": "awaiting_approval",
                "workflow_id": workflow["workflow_id"],
                "result": result,
            }
        if workflow["status"] == "completed":
            return {"status": "completed", "result": result}
        return {"status": "failed", "result": result}
