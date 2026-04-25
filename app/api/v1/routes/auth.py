from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.core.config import settings
from app.db.session import get_session
from app.schemas.auth import AuthSuccessResponse, LoginRequest, RegisterRequest, UserResponse
from app.services import auth_service

router = APIRouter()

_REFRESH_COOKIE = "refresh_token"
_COOKIE_PATH = "/api/v1/auth/refresh"


@router.post("/register", status_code=201)
def register(
    data: RegisterRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> AuthSuccessResponse:
    user, access_token, raw_refresh = auth_service.register(session, data)
    _set_refresh_cookie(response, raw_refresh)
    return _build_auth_response(user, access_token)


@router.post("/login")
def login(
    data: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> AuthSuccessResponse:
    user, access_token, raw_refresh = auth_service.login(session, data)
    _set_refresh_cookie(response, raw_refresh)
    return _build_auth_response(user, access_token)


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=raw_token,
        httponly=True,
        samesite="strict",
        path=_COOKIE_PATH,
    )


def _build_auth_response(user, access_token: str) -> AuthSuccessResponse:
    return AuthSuccessResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )
