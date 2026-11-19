from datetime import datetime, timedelta, timezone
from app.autonomy.policy import AutonomyPolicy
from app.autonomy.goal_repository import GoalRepository


class GoalService:
    def __init__(self, repository, policy=None, trigger_registry=None):
        self.repository = repository
        self.policy = policy or AutonomyPolicy()
        self.trigger_registry = trigger_registry

    def create(self, description, interval_seconds=None, run_at=None,
               max_steps=5, max_runtime_seconds=120, event_type=None):
        self.policy.validate_goal(description, max_steps, max_runtime_seconds)
        if event_type is not None:
            if self.trigger_registry is None:
                raise ValueError("Event triggers are unavailable.")
            if event_type not in self.trigger_registry.allowed_event_types:
                raise ValueError("Event type is not registered.")
            if interval_seconds is not None or run_at is not None:
                raise ValueError("Event goals cannot also have a time schedule.")
            return self.repository.create_goal(
                description.strip(), "event", None, None, max_steps,
                max_runtime_seconds, event_type=event_type
            )
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
        return self.repository.create_goal(
            description.strip(), trigger, interval_seconds, run_at,
            max_steps, max_runtime_seconds
        )

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

    def publish_event(self, event_id, event_type, payload):
        if self.trigger_registry is None:
            raise ValueError("Event triggers are unavailable.")
        event = self.trigger_registry.validate_event(event_type, payload)
        return self.repository.publish_event(
            event_id, event.event_type, event.payload, event.occurred_at
        )
