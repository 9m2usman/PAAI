import uuid

from app.agents.specialized_agents import (
    ResearchAgent,
    AnalysisAgent,
    WritingAgent
)

from app.orchestration.agent_registry import AgentRegistry
from app.orchestration.shared_state import SharedTaskState
from app.orchestration.task_delegator import TaskDelegator
from app.orchestration.failure_manager import FailureManager


class SupervisorAgent:

    def __init__(self):
        self.registry = AgentRegistry()

        self.registry.register_agent(ResearchAgent())
        self.registry.register_agent(AnalysisAgent())
        self.registry.register_agent(WritingAgent())

        self.shared_state = SharedTaskState()

        self.failure_manager = FailureManager(
            max_attempts=2
        )

        self.delegator = TaskDelegator(
            registry=self.registry,
            shared_state=self.shared_state,
            failure_manager=self.failure_manager
        )

    def create_workflow(self):
        return [
            {
                "agent": "research_agent",
                "instruction": (
                    "Research and organize the user's requested topic. "
                    "Identify key information, important concepts, "
                    "and uncertainties."
                )
            },
            {
                "agent": "analysis_agent",
                "instruction": (
                    "Analyze the original request and the research "
                    "agent's findings. Identify insights, risks, "
                    "trade-offs, and conclusions."
                )
            },
            {
                "agent": "writing_agent",
                "instruction": (
                    "Prepare the final comprehensive report using "
                    "the original request, research, and analysis."
                )
            }
        ]

    def run(self, user_id, user_request):
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("A valid user ID is required.")

        if not isinstance(user_request, str) or not user_request.strip():
            raise ValueError("A valid user request is required.")

        task_id = str(uuid.uuid4())

        self.shared_state.create_task(
            user_id,
            task_id,
            user_request
        )

        try:
            results = self.delegator.execute_workflow(
                user_id=user_id,
                task_id=task_id,
                user_request=user_request,
                workflow=self.create_workflow()
            )

            final_result = results["writing_agent"]

            return {
                "user_id": user_id,
                "task_id": task_id,
                "status": "completed",
                "result": final_result,
                "agent_results": results,
                "task_state": self.shared_state.get_task(
                    user_id,
                    task_id
                )
            }

        except Exception as error:
            self.shared_state.add_error(
                user_id,
                task_id,
                error
            )

            self.shared_state.update_status(
                user_id,
                task_id,
                "failed"
            )

            return {
                "user_id": user_id,
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": str(error),
                "task_state": self.shared_state.get_task(
                    user_id,
                    task_id
                )
            }

    def run_for_current_identity(self, user_request):
        from app.identity.context import current_identity
        identity = current_identity()
        return self.run(identity.user_id, user_request)
