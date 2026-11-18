from app.orchestration.agent_communication import AgentCommunication
from app.orchestration.failure_manager import FailureManager


class TaskDelegator:

    def __init__(self, registry, shared_state, failure_manager=None):
        self.registry = registry
        self.shared_state = shared_state
        self.communication = AgentCommunication()
        self.failure_manager = failure_manager or FailureManager()

    def execute_workflow(
        self,
        user_id,
        task_id,
        user_request,
        workflow
    ):
        self.shared_state.update_status(
            user_id,
            task_id,
            "in_progress"
        )

        completed_results = {}

        for index, step in enumerate(workflow, start=1):
            agent_name = step["agent"]
            instruction = step["instruction"]
            subtask_id = f"{task_id}_step_{index}"

            subtask = {
                "subtask_id": subtask_id,
                "agent": agent_name,
                "instruction": instruction,
                "status": "pending"
            }

            self.shared_state.add_subtask(
                user_id,
                task_id,
                subtask
            )

            self.shared_state.update_subtask(
                user_id,
                task_id,
                subtask_id,
                "in_progress"
            )

            agent = self.registry.get_agent(agent_name)

            message = self.communication.create_message(
                sender="supervisor_agent",
                receiver=agent_name,
                task_id=task_id,
                content=instruction
            )

            self.communication.validate_message(message)

            self.shared_state.add_message(
                user_id,
                task_id,
                message
            )

            context = {
                "original_request": user_request,
                "previous_results": dict(completed_results)
            }

            execution = self.failure_manager.execute_agent(
                agent,
                user_id,
                task_id,
                instruction,
                context
            )

            if not execution["success"]:
                self.shared_state.update_subtask(
                    user_id,
                    task_id,
                    subtask_id,
                    "failed"
                )

                self.shared_state.add_error(
                    user_id,
                    task_id,
                    execution["error"]
                )

                self.shared_state.update_status(
                    user_id,
                    task_id,
                    "failed"
                )

                raise RuntimeError(
                    f"{agent_name} failed: {execution['error']}"
                )

            result = execution["result"]

            completed_results[agent_name] = result

            self.shared_state.add_result(
                user_id,
                task_id,
                agent_name,
                result
            )

            self.shared_state.update_subtask(
                user_id,
                task_id,
                subtask_id,
                "completed"
            )

            result_message = self.communication.create_message(
                sender=agent_name,
                receiver="supervisor_agent",
                task_id=task_id,
                content=result
            )

            self.shared_state.add_message(
                user_id,
                task_id,
                result_message
            )

        self.shared_state.update_status(
            user_id,
            task_id,
            "completed"
        )

        return completed_results