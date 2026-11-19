from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.identity.context import identity_scope

bearer_scheme = HTTPBearer(auto_error=False)

def get_runtime(request: Request):
    runtime = getattr(request.app.state, "paai_runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Application runtime is unavailable.")
    return runtime

async def authenticated_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer authentication is required.")
    runtime = get_runtime(request)
    try:
        identity = runtime.authenticate(credentials.credentials)
    except (PermissionError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token.") from None
    with identity_scope(identity):
        yield identity
