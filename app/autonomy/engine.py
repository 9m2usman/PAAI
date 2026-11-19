import time
from app.autonomy.policy import AutonomyPolicy


class AutonomyEngine:
    def __init__(self, repository, executor, policy=None, approval_bridge=None):
        self.repository = repository
        self.executor = executor
        self.policy = policy or AutonomyPolicy()
        self.approval_bridge = approval_bridge

    def run_due_once(self):
        claims = self.repository.claim_due(self.policy.max_due_goals_per_tick)
        outcomes = []
        for claim in claims:
            goal = claim["goal"]
            run_id = claim["run_id"]
            started = time.monotonic()
            try:
                result = self.executor(goal["description"], {
                    "goal_id": goal["goal_id"], "run_id": run_id,
                    "max_steps": min(goal["max_steps"], self.policy.max_steps),
                    "max_runtime_seconds": min(goal["max_runtime_seconds"], self.policy.max_runtime_seconds),
                    "trigger_type": goal["trigger_type"], "event_type": goal.get("event_type"),
                    "event_payload": goal.get("event_payload"),
                })
                if result is None or result == "":
                    raise RuntimeError("Autonomy executor returned an empty result.")
                elapsed = time.monotonic() - started
                if elapsed > min(goal["max_runtime_seconds"], self.policy.max_runtime_seconds):
                    outcome = self.repository.finish_run(run_id, "budget_exhausted",
                        error="Execution time budget exceeded.")
                elif isinstance(result, dict) and result.get("status") == "awaiting_approval":
                    workflow_id = result.get("workflow_id")
                    if workflow_id and self.approval_bridge is not None:
                        outcome = self.approval_bridge.pause_run_for_approval(
                            run_id, goal["goal_id"], workflow_id)
                    else:
                        outcome = self.repository.finish_run(
                            run_id, "awaiting_approval", result=str(result))
                elif isinstance(result, dict) and result.get("status") == "budget_exhausted":
                    outcome = self.repository.finish_run(run_id, "budget_exhausted", result=str(result))
                elif isinstance(result, dict) and result.get("status") == "failed":
                    outcome = self.repository.finish_run(run_id, "failed", error=str(result)[:500])
                else:
                    outcome = self.repository.finish_run(run_id, "completed", result=str(result))
            except Exception as error:
                outcome = self.repository.finish_run(
                    run_id, "failed", error=type(error).__name__ + ": " + str(error)[:500])
            outcomes.append(outcome)
        return outcomes
