from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import authenticated_identity, get_runtime
from app.api.schemas import PermissionGrantRequest

router = APIRouter(prefix="/api/v1/permissions", tags=["integration permissions"])


@router.get("")
def list_permissions(request: Request, identity=Depends(authenticated_identity)):
    return get_runtime(request).permissions.list_permissions(identity.user_id)


@router.post("", status_code=201)
def grant_permission(payload: PermissionGrantRequest, request: Request,
                     identity=Depends(authenticated_identity)):
    runtime = get_runtime(request)
    integration = payload.integration.strip().lower()
    action = payload.action.strip().lower()
    try:
        connector = runtime.phase5_runtime["integration_registry"].get(integration)
        if action not in connector.get_supported_actions():
            raise ValueError("Action is not supported by this integration.")
        runtime.permissions.grant_permission(identity.user_id, integration, [action])
        return {"integration": integration, "action": action, "granted": True}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.delete("/{integration}/{action}")
def revoke_permission(integration: str, action: str, request: Request,
                      identity=Depends(authenticated_identity)):
    runtime = get_runtime(request)
    integration = integration.strip().lower()
    action = action.strip().lower()
    try:
        connector = runtime.phase5_runtime["integration_registry"].get(integration)
        if action not in connector.get_supported_actions():
            raise ValueError("Action is not supported by this integration.")
        removed = runtime.permissions.revoke_permission(
            identity.user_id, integration, action
        )
        return {"integration": integration, "action": action, "revoked": removed}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
