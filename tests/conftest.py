"""Pytest fixtures for RMS tests."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import SessionTransaction
from sqlmodel import Session, SQLModel, create_engine

# Load .env.test for local dev (skip if env already set, e.g. CI)
if "DATABASE_URL" not in os.environ:
    env_test = Path(__file__).parent.parent / ".env.test"
    if env_test.exists():
        load_dotenv(env_test)

# Hard requirement
assert (
    "DATABASE_URL" in os.environ
), "DATABASE_URL must be set (via .env.test for local or env vars for CI)"
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_pytest_only")

import app.models
from app.api.deps import get_db
from app.main import app


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    engine = create_engine(os.environ["DATABASE_URL"], echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Function-scoped DB session with transactional rollback.

    Uses SAVEPOINT pattern so app-code commit() inside the test
    only commits the savepoint (inner), allowing the outer
    transaction to rollback all data changes after the test.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Start a SAVEPOINT for the test
    nested = connection.begin_nested()

    # Restart SAVEPOINT every time the inner transaction ends
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess: Session, trans: SessionTransaction) -> None:
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def landlord_user(db_session):
    """Create a landlord user. Returns User instance.

    Password is 'ValidPass1' (matches password complexity).
    """
    from app.core.enums import UserRole
    from app.core.security import hash_password
    from app.repositories.user_repo import UserRepo

    repo = UserRepo(db_session)
    return repo.create(
        email="landlord@test.com",
        password_hash=hash_password("ValidPass1"),
        full_name="Test Landlord",
        role=UserRole.LANDLORD,
    )


@pytest.fixture
def landlord_token(landlord_user) -> str:
    """JWT access token for landlord_user."""
    from app.core.security import create_access_token

    assert landlord_user.id is not None
    return create_access_token(landlord_user.id, landlord_user.role.value)


@pytest.fixture
def auth_header(landlord_token: str) -> dict[str, str]:
    """HTTP Authorization Bearer header."""
    return {"Authorization": f"Bearer {landlord_token}"}
