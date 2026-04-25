"""Pytest fixtures for RMS tests."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

# Load test env BEFORE app imports
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://rms:JR5fRlLH8XCQFmI05dV4Oo83QiUeh7KB@localhost:5433/rms_test",
)
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_pytest_only")

import app.models
from app.api.deps import get_db
from app.main import app


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    """Session-scoped: create engine + schema once per pytest run."""
    engine = create_engine(os.environ["DATABASE_URL"], echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Function-scoped: rollback transaction after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with get_db overridden to use test session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
