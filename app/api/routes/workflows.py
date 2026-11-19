from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import authenticated_identity, get_runtime
from app.api.schemas import WorkflowCreateRequest, ApprovalDecisionRequest

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


@router.post("", status_code=202)
def create_workflow(payload: WorkflowCreateRequest, request: Request,
                    identity=Depends(authenticated_identity)):
    runtime = get_runtime(request)
    try:
        return runtime.workflow_agent.run(identity.user_id, payload.request)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Workflow action is not permitted.") from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str, request: Request,
                 identity=Depends(authenticated_identity)):
    try:
        return runtime_workflow(request, identity.user_id, workflow_id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="Workflow not found.") from None
    except ValueError:
        raise HTTPException(status_code=404, detail="Workflow not found.") from None


@router.post("/{workflow_id}/approve")
def approve_workflow(workflow_id: str, payload: ApprovalDecisionRequest,
                     request: Request, identity=Depends(authenticated_identity)):
    runtime = get_runtime(request)
    try:
        workflow = runtime.workflow_manager.get_workflow(identity.user_id, workflow_id)
        pending = workflow.get("pending_approval")
        if not pending or pending.get("approval_id") != payload.approval_id:
            raise ValueError("Approval does not match this workflow.")
        runtime.approvals.approve(identity.user_id, payload.approval_id)
        return runtime.workflow_manager.resume(
            identity.user_id, workflow_id, payload.approval_id
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Approval is not permitted.") from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/{workflow_id}/reject")
def reject_workflow(workflow_id: str, payload: ApprovalDecisionRequest,
                    request: Request, identity=Depends(authenticated_identity)):
    runtime = get_runtime(request)
    try:
        return runtime.workflow_manager.reject(
            identity.user_id, workflow_id, payload.approval_id
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Approval is not permitted.") from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


def runtime_workflow(request, user_id, workflow_id):
    runtime = get_runtime(request)
    return runtime.workflow_manager.get_workflow(user_id, workflow_id)
