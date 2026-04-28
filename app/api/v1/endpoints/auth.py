from fastapi import APIRouter, status

from app.api.deps import AuthServiceDep
from app.schemas.auth import AuthSuccessResponse, LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Landlord account",
)
def register(req: RegisterRequest, svc: AuthServiceDep) -> AuthSuccessResponse:
    return svc.register_landlord(req)


@router.post(
    "/login",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
)
def login(req: LoginRequest, svc: AuthServiceDep) -> AuthSuccessResponse:
    return svc.login(req)
