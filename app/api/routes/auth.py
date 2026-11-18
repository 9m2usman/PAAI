from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.dependencies import authenticated_identity, get_runtime
from app.api.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, request: Request):
    runtime = get_runtime(request)
    try:
        return runtime.auth.register(payload.email, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request):
    runtime = get_runtime(request)
    try:
        return runtime.auth.login(payload.email, payload.password)
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid email or password.") from None

@router.get("/me", response_model=UserResponse)
def me(identity=Depends(authenticated_identity)):
    return {"user_id": identity.user_id, "email": identity.email}
