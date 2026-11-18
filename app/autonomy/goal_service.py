from datetime import datetime, timedelta, timezone
from app.autonomy.policy import AutonomyPolicy
from app.autonomy.goal_repository import GoalRepository

class GoalService:
    def __init__(self, repository, policy=None):
        self.repository = repository
        self.policy = policy or AutonomyPolicy()

    def create(self, description, interval_seconds=None, run_at=None, max_steps=5, max_runtime_seconds=120):
        self.policy.validate_goal(description, max_steps, max_runtime_seconds)
        if interval_seconds is not None and (not isinstance(interval_seconds, int) or interval_seconds < 60):
            raise ValueError("Recurring interval must be at least 60 seconds.")
        if run_at is None and interval_seconds is not None:
            run_at = (datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)).isoformat()
        if run_at is not None:
            try:
                parsed = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError()
            except Exception:
                raise ValueError("run_at must be an ISO-8601 timestamp with timezone.") from None
        trigger = "scheduled" if run_at or interval_seconds else "manual"
        return self.repository.create_goal(description.strip(), trigger, interval_seconds, run_at, max_steps, max_runtime_seconds)

    def list(self):
        return self.repository.list_goals()

    def get(self, goal_id):
        return self.repository.get_goal(goal_id)

    def pause(self, goal_id):
        return self.repository.set_status(goal_id, "paused")

    def resume(self, goal_id):
        return self.repository.set_status(goal_id, "active")

    def cancel(self, goal_id):
        return self.repository.set_status(goal_id, "cancelled")

    def run_now(self, goal_id):
        return self.repository.request_run(goal_id)
