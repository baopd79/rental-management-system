from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.core.config import get_settings
from app.core.enums import UserRole
from app.core.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repo import UserRepo
from app.schemas.auth import (
    AuthSuccessResponse,
    LoginRequest,
    RegisterRequest,
    UserRead,
)


class AuthService:
    """Business logic for authentication: register, login.
    Stage 1.2 access token only. Refesh tokens deferred to Stage 1.3
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repo = UserRepo(db)

    def register_landlord(self, req: RegisterRequest) -> AuthSuccessResponse:
        """Register new Landlord. Auto-login (return access token)."""
        password_hash = hash_password(req.password)
        try:
            user = self.user_repo.create(
                email=req.email,
                password_hash=password_hash,
                full_name=req.full_name,
                role=UserRole.LANDLORD,
                phone=req.phone,
            )
        except IntegrityError as e:
            self.db.rollback()
            raise EmailAlreadyExistsError() from e
        return self._build_auth_response(user)

    def login(self, req: LoginRequest) -> AuthSuccessResponse:
        """verify credentials and return access token."""
        user = self.user_repo.get_by_email(req.email)
        # Generic error for all failure model (anti-enumeration)
        if user is None or not user.is_active:
            raise InvalidCredentialsError()
        if not verify_password(req.password, user.password_hash):
            raise InvalidCredentialsError()

        # Update last_login_at
        user.last_login_at = datetime.now(UTC)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self._build_auth_response(user)

    # Private helper
    def _build_auth_response(self, user: User) -> AuthSuccessResponse:
        """Build AuthSuccessResponse from User entity."""
        assert user.id is not None
        settings = get_settings()
        token = create_access_token(user.id, user.role.value)
        return AuthSuccessResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user=UserRead.model_validate(user),
        )
