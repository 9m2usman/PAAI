from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    user_id: str
    email: str


class TokenResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "Bearer"


class GoalCreateRequest(BaseModel):
    description: str = Field(min_length=1, max_length=4000)
    interval_seconds: Optional[int] = Field(default=None, ge=60)
    run_at: Optional[str] = None
    event_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    max_steps: int = Field(default=5, ge=1, le=8)
    max_runtime_seconds: int = Field(default=120, ge=1, le=300)


class EventIngestRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=100)
    payload: dict = Field(default_factory=dict)


class GoalResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    goal_id: str
    description: str
    status: str
    trigger_type: str
    next_run_at: Optional[str] = None


class WorkflowCreateRequest(BaseModel):
    request: str = Field(min_length=1, max_length=4000)


class ApprovalDecisionRequest(BaseModel):
    approval_id: str = Field(min_length=1, max_length=128)
