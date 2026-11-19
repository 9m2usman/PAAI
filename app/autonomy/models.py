from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

GOAL_STATUSES = {"active", "paused", "running", "awaiting_approval", "completed", "failed", "cancelled", "budget_exhausted"}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class Goal:
    goal_id: str
    owner_id: str
    description: str
    status: str
    trigger_type: str
    interval_seconds: Optional[int]
    next_run_at: Optional[str]
    max_steps: int
    max_runtime_seconds: int
    created_at: str
    updated_at: str

@dataclass(frozen=True)
class GoalRun:
    run_id: str
    goal_id: str
    status: str
    started_at: str
    finished_at: Optional[str]
    result: Optional[str]
    error: Optional[str]
    attempt: int
