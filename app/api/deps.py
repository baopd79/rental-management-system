from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError
from sqlmodel import Session

from app.core.exceptions import InvalidTokenError, TokenExpiredError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepo
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db: Annotated[Session, Depends(get_db)]) -> AuthService:
    """Wire AuthService với DB session từ request scope."""
    return AuthService(db=db)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Extract JWT, validate, load User. Raises InvalidTokenError/TokenExpiredError."""
    if credentials is None:
        raise InvalidTokenError("Missing authentication token")

    token = credentials.credentials

    try:
        claims = decode_access_token(token)
    except ExpiredSignatureError as e:
        raise TokenExpiredError() from e
    except JWTError as e:
        raise InvalidTokenError() from e

    sub = claims.get("sub")
    if sub is None:
        raise InvalidTokenError("Token missing 'sub' claim")
    try:
        user_id = UUID(sub)
    except ValueError as e:
        raise InvalidTokenError("Invalid user_id in token") from e

    user_repo = UserRepo(db)
    user = user_repo.get_by_id(user_id)
    if user is None:
        raise InvalidTokenError("User not found")
    if not user.is_active:
        raise InvalidTokenError("User account inactive")

    return user


# Type aliases for FastAPI dependencies (use in endpoint signatures)
DbDep = Annotated[Session, Depends(get_db)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
