from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.exceptions import RMSException
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import User
from app.repos import user_repo

_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    payload = decode_access_token(credentials.credentials)
    user = user_repo.get_by_id(session, UUID(payload["sub"]))
    if not user or not user.is_active:
        raise RMSException(401, "INVALID_TOKEN", "Token invalid or user inactive")
    return user
