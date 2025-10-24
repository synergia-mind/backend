import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock
from clerk_backend_api.models import Session as ClerkSession

from app.main import app
from app.core.db import get_session
from app.api.auth import verify_clerk_session


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio to only use asyncio backend."""
    return "asyncio"


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


@pytest.fixture(name="mock_clerk_session")
def mock_clerk_session_fixture():
    """
    Create a mock Clerk session for authentication bypass in tests.
    """
    mock_session = Mock(spec=ClerkSession)
    mock_session.id = "test_session_id"
    mock_session.user_id = "test_user_id"
    mock_session.status = "active"
    mock_session.client_id = "test_client_id"
    return mock_session


@pytest.fixture(name="client")
def client_fixture(session: Session, mock_clerk_session: ClerkSession):
    """
    Create a test client with overridden database session and mocked authentication.
    """
    def get_session_override():
        return session
    
    async def verify_clerk_session_override():
        return mock_clerk_session
    
    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[verify_clerk_session] = verify_clerk_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
