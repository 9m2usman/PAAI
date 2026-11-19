from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import authenticated_identity, get_runtime

router = APIRouter(prefix="/api/v1/integrations/google", tags=["Google integrations"])


@router.get("/connect")
def connect_google(request: Request, identity=Depends(authenticated_identity)):
    runtime = get_runtime(request)
    if runtime.google_oauth is None:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")
    return {"authorization_url": runtime.google_oauth.create_authorization_url(identity.user_id)}


@router.get("/callback")
def google_callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        raise HTTPException(status_code=400, detail="Google authorization was not granted.")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Google callback is missing code or state.")
    runtime = get_runtime(request)
    if runtime.google_oauth is None:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")
    try:
        return runtime.google_oauth.exchange_code_from_state(code, state)
    except PermissionError:
        raise HTTPException(status_code=400, detail="Invalid or expired Google OAuth state.") from None
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Google token exchange failed.") from None


@router.get("/status")
def google_status(request: Request, identity=Depends(authenticated_identity)):
    credentials = get_runtime(request).credentials
    return {
        "gmail": credentials.has_credentials(identity.user_id, "gmail"),
        "calendar": credentials.has_credentials(identity.user_id, "calendar"),
    }


@router.delete("/disconnect")
def disconnect_google(request: Request, identity=Depends(authenticated_identity)):
    credentials = get_runtime(request).credentials
    gmail = credentials.delete_credentials(identity.user_id, "gmail")
    calendar = credentials.delete_credentials(identity.user_id, "calendar")
    return {"disconnected": gmail or calendar}
