from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.dependencies import authenticated_identity, get_runtime
from app.api.schemas import GoalCreateRequest

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])

@router.post("", status_code=201)
def create_goal(payload: GoalCreateRequest, request: Request, identity=Depends(authenticated_identity)):
    runtime = get_runtime(request)
    try:
        return runtime.goals.create(
            payload.description,
            interval_seconds=payload.interval_seconds,
            run_at=payload.run_at,
            max_steps=payload.max_steps,
            max_runtime_seconds=payload.max_runtime_seconds,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None

@router.get("")
def list_goals(request: Request, identity=Depends(authenticated_identity)):
    return get_runtime(request).goals.list()

@router.get("/{goal_id}")
def get_goal(goal_id: str, request: Request, identity=Depends(authenticated_identity)):
    try:
        return get_runtime(request).goals.get(goal_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Goal not found.") from None

@router.post("/{goal_id}/pause")
def pause_goal(goal_id: str, request: Request, identity=Depends(authenticated_identity)):
    try:
        return get_runtime(request).goals.pause(goal_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None

@router.post("/{goal_id}/resume")
def resume_goal(goal_id: str, request: Request, identity=Depends(authenticated_identity)):
    try:
        return get_runtime(request).goals.resume(goal_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None

@router.post("/{goal_id}/cancel")
def cancel_goal(goal_id: str, request: Request, identity=Depends(authenticated_identity)):
    try:
        return get_runtime(request).goals.cancel(goal_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None

@router.post("/{goal_id}/run")
def run_goal(goal_id: str, request: Request, identity=Depends(authenticated_identity)):
    runtime = get_runtime(request)
    try:
        runtime.goals.run_now(goal_id)
        return runtime.scheduler.run_due_once()
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None

@router.get("/{goal_id}/runs")
def list_runs(goal_id: str, request: Request, identity=Depends(authenticated_identity)):
    try:
        return get_runtime(request).goal_repository.list_runs(goal_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Goal not found.") from None
