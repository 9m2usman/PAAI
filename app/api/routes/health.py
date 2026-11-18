from fastapi import APIRouter, Request
router = APIRouter(tags=["health"])

@router.get("/health/live")
def live():
    return {"status": "alive"}

@router.get("/health/ready")
def ready(request: Request):
    runtime = getattr(request.app.state, "paai_runtime", None)
    if runtime is None:
        return {"status": "not_ready"}
    return {"status": "ready"}
