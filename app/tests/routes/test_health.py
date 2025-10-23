from fastapi.testclient import TestClient

from app.core import settings
from app.models import HealthStatus


def test_health_check(client: TestClient):
    """
    Test the health check endpoint to ensure it returns a healthy status.
    """
    response = client.get(f"{settings.API_V1_STR}/health/")
    assert response.status_code == 200
    assert response.json().get("status", "") == HealthStatus.healthy
