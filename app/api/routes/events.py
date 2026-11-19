from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.dependencies import authenticated_identity, get_runtime
from app.api.schemas import EventIngestRequest

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post("", status_code=202)
def ingest_event(payload: EventIngestRequest, request: Request,
                 identity=Depends(authenticated_identity)):
    runtime = get_runtime(request)
    try:
        result = runtime.goals.publish_event(
            payload.event_id, payload.event_type, payload.payload
        )
        return {"accepted": True, **result}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
