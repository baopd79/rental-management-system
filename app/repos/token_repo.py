from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlmodel import Session, select

from app.models.token import RefreshToken

_REFRESH_TOKEN_TTL_DAYS = 7


def create_refresh_token(
    session: Session,
    *,
    user_id: UUID,
    token_hash: str,
) -> RefreshToken:
    token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=_REFRESH_TOKEN_TTL_DAYS),
    )
    session.add(token)
    session.commit()
    session.refresh(token)
    return token


def get_by_hash(session: Session, token_hash: str) -> RefreshToken | None:
    return session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).first()
