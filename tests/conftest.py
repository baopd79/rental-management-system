"""Pytest fixtures for RMS tests."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
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
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

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
