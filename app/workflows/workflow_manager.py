import uuid
from copy import deepcopy
from threading import RLock


class WorkflowManager:

    def __init__(self, execution_manager):
        self.execution_manager = execution_manager
        self.workflows = {}
        self.lock = RLock()

    def run(self, user_id, steps):

        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Valid user ID is required.")

        if not isinstance(steps, list) or not steps:
            raise ValueError("Workflow steps are required.")

        for step in steps:

            if not isinstance(step, dict):
                raise ValueError("Invalid workflow step.")

            required = {"integration", "action", "parameters"}

            if not required.issubset(step):
                raise ValueError("Workflow step is incomplete.")

            if not isinstance(step["integration"], str) or not step["integration"].strip():
                raise ValueError("Invalid workflow integration.")

            if not isinstance(step["action"], str) or not step["action"].strip():
                raise ValueError("Invalid workflow action.")

            if not isinstance(step["parameters"], dict):
                raise ValueError("Invalid workflow parameters.")

        workflow_id = str(uuid.uuid4())

        workflow = {
            "workflow_id": workflow_id,
            "user_id": user_id,
            "steps": deepcopy(steps),
            "current_step": 0,
            "results": [],
            "status": "running"
        }

        with self.lock:
            self.workflows[workflow_id] = workflow

        return self._continue_workflow(workflow_id)

    def _continue_workflow(self, workflow_id, approval_id=None):

        with self.lock:
            workflow = self.workflows[workflow_id]
            step = deepcopy(
                workflow["steps"][workflow["current_step"]]
            )
            user_id = workflow["user_id"]

        try:

            result = self.execution_manager.execute(
                user_id=user_id,
                integration=step["integration"],
                action=step["action"],
                parameters=step["parameters"],
                approval_id=approval_id
            )

        except Exception as error:

            with self.lock:
                workflow["status"] = "failed"
                workflow["error"] = type(error).__name__

            return self.get_workflow(user_id, workflow_id)

        with self.lock:

            if result["status"] == "awaiting_approval":

                workflow["status"] = "awaiting_approval"
                workflow["pending_approval"] = result["approval"]

                return deepcopy(workflow)

            workflow["results"].append(result)
            workflow["current_step"] += 1
            workflow.pop("pending_approval", None)

            if workflow["current_step"] == len(workflow["steps"]):
                workflow["status"] = "completed"
                return deepcopy(workflow)

        return self._continue_workflow(workflow_id)

    def resume(self, user_id, workflow_id, approval_id):

        with self.lock:

            workflow = self.workflows.get(workflow_id)

            if workflow is None:
                raise ValueError("Workflow not found.")

            if workflow["user_id"] != user_id:
                raise PermissionError("Workflow belongs to another user.")

            if workflow["status"] != "awaiting_approval":
                raise ValueError("Workflow is not awaiting approval.")

            pending = workflow.get("pending_approval")

            if not pending or pending["approval_id"] != approval_id:
                raise ValueError("Approval does not match this workflow.")

            workflow["status"] = "running"

        return self._continue_workflow(
            workflow_id,
            approval_id=approval_id
        )

    def get_workflow(self, user_id, workflow_id):

        with self.lock:

            workflow = self.workflows.get(workflow_id)

            if workflow is None:
                raise ValueError("Workflow not found.")

            if workflow["user_id"] != user_id:
                raise PermissionError("Workflow belongs to another user.")

            return deepcopy(workflow)

    def reject(self, user_id, workflow_id, approval_id):

        with self.lock:

            workflow = self.workflows.get(workflow_id)

            if workflow is None:
                raise ValueError("Workflow not found.")

            if workflow["user_id"] != user_id:
                raise PermissionError("Workflow belongs to another user.")

            if workflow["status"] != "awaiting_approval":
                raise ValueError("Workflow is not awaiting approval.")

            pending = workflow.get("pending_approval")

            if not pending or pending["approval_id"] != approval_id:
                raise ValueError("Approval does not match this workflow.")

            action_data = pending["action_data"]

            risk_level = self.execution_manager.risk_evaluator.classify(
                action_data["integration"],
                action_data["action"],
                action_data["parameters"]
            )

            self.execution_manager.approval_manager.reject(
                user_id, approval_id
            )

            workflow["status"] = "rejected"
            workflow["pending_approval"] = None

            self.execution_manager.audit_logger.log(
                user_id,
                action_data["integration"],
                action_data["action"],
                "rejected",
                risk_level,
                "rejected"
            )

            return deepcopy(workflow)
