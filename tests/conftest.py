import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.db.session import get_session
from app.main import app


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(settings.test_database_url)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    conn = test_engine.connect()
    trans = conn.begin()
    # Session(bind=conn) joins the open transaction — soft-deprecated in
    # SQLAlchemy 2.x but still functional. Revisit if SQLAlchemy 3.x removes it.
    session = Session(bind=conn)
    yield session
    session.close()
    trans.rollback()
    conn.close()


@pytest.fixture
def client(db_session: Session):
    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
