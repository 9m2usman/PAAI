from dataclasses import dataclass

@dataclass(frozen=True)
class AutonomyPolicy:
    max_steps: int = 8
    max_runtime_seconds: int = 300
    max_attempts: int = 2
    max_due_goals_per_tick: int = 20
    max_description_length: int = 4000
    max_event_payload_bytes: int = 16384

    def __post_init__(self):
        values = (self.max_steps, self.max_runtime_seconds, self.max_attempts, self.max_due_goals_per_tick, self.max_description_length, self.max_event_payload_bytes)
        if any(not isinstance(value, int) or value < 1 for value in values):
            raise ValueError("Autonomy limits must be positive integers.")

    def validate_goal(self, description, max_steps, max_runtime_seconds):
        if not isinstance(description, str) or not description.strip() or len(description) > self.max_description_length:
            raise ValueError("Goal description is empty or exceeds the allowed length.")
        if not isinstance(max_steps, int) or not 1 <= max_steps <= self.max_steps:
            raise ValueError("Goal step budget is outside the allowed range.")
        if not isinstance(max_runtime_seconds, int) or not 1 <= max_runtime_seconds <= self.max_runtime_seconds:
            raise ValueError("Goal runtime budget is outside the allowed range.")
