from uuid import UUID

from sqlmodel import Session, select

from app.core.enums import UserRole
from app.models.user import User


class UserRepo:
    """Repository for User entity. All DB operations go through here."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _normalize_email(email: str) -> str:
        """Lowercase + strip whitespace."""
        return email.strip().lower()

    def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID. Returns None if not found."""
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Get user by email. Email is normalized before query."""
        normalized = self._normalize_email(email)
        stmt = select(User).where(User.email == normalized)
        return self.db.exec(stmt).first()

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str | None,
        role: UserRole,
        phone: str | None = None,
    ) -> User:
        """Create new user. Email is normalized. Commits transaction."""
        user = User(
            email=self._normalize_email(email),
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            phone=phone,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
