import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.db import get_session


@pytest.fixture(name="session")
def session_fixture():
    """
    Create a test database session using SQLite in-memory database.
    """
    # Create SQLite in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session
    
    # Clean up
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Create a test client with overridden database session.
    """
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
