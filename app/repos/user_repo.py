from uuid import UUID

from sqlmodel import Session, select

from app.core.enums import UserRole
from app.models.user import User


def get_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()


def get_by_id(session: Session, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def create(
    session: Session,
    *,
    email: str,
    password_hash: str,
    full_name: str,
    phone: str | None,
    role: UserRole,
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        phone=phone,
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
