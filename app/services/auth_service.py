from datetime import datetime, timezone

from sqlmodel import Session

from app.core import security
from app.core.enums import UserRole
from app.core.exceptions import RMSException
from app.models.user import User
from app.repos import token_repo, user_repo
from app.schemas.auth import LoginRequest, RegisterRequest


def register(session: Session, data: RegisterRequest) -> tuple[User, str, str]:
    if user_repo.get_by_email(session, data.email):
        raise RMSException(409, "DUPLICATE_TENANT_EMAIL", "Email already registered")

    password_hash = security.hash_password(data.password)
    user = user_repo.create(
        session,
        email=data.email,
        password_hash=password_hash,
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole.LANDLORD,
    )

    access_token = security.create_access_token(user.id, user.role)
    raw_refresh, token_hash = security.generate_refresh_token()
    token_repo.create_refresh_token(session, user_id=user.id, token_hash=token_hash)

    return user, access_token, raw_refresh


def login(session: Session, data: LoginRequest) -> tuple[User, str, str]:
    user = user_repo.get_by_email(session, data.email)
    if not user or not security.verify_password(data.password, user.password_hash):
        raise RMSException(401, "INVALID_CREDENTIALS", "Invalid email or password")

    if not user.is_active:
        raise RMSException(401, "ACCOUNT_DISABLED", "Account has been disabled")

    access_token = security.create_access_token(user.id, user.role)
    raw_refresh, token_hash = security.generate_refresh_token()
    token_repo.create_refresh_token(session, user_id=user.id, token_hash=token_hash)

    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()

    return user, access_token, raw_refresh
