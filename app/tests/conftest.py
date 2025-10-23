import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(name="client")
def client_fixture():
    """
    Create a test client.
    """
    client = TestClient(app)
    yield client
