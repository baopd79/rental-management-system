# A3 — app/db/session.py
# 1. What — Session layer là gì?
# Code chịu trách nhiệm tạo và quản lý kết nối tới Postgres. Cụ thể 3 thứ:
# Engine — object đại diện cho connection pool tới DB
# SessionLocal — factory tạo Session (1 đơn vị "transaction context")
# get_db() — FastAPI dependency cấp Session cho endpoint, đảm bảo cleanup sau khi request xong
from collections.abc import Generator
from sqlmodel import Session, create_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


# Generator[YieldType, SendType, ReturnType]. Function dùng yield → return type phải là Generator. SendType và ReturnType của get_db đều None vì không dùng gen.send() và không return value.
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency : yeild a DB session per request,auto-close"""
    with Session(engine) as session:
        yield session
