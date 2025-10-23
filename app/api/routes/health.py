from fastapi import APIRouter
from datetime import datetime, timezone
from models import HealthCheckResponse, HealthStatus
from core.config import Settings

router = APIRouter()
settings = Settings()


@router.get("/", status_code=200, response_model=HealthCheckResponse)
async def health_check():
    """
    Comprehensive Health Check
    
    Returns detailed health status of the application and its dependencies.
    """
    return HealthCheckResponse(
        status=HealthStatus.healthy,
        timestamp=datetime.now(timezone.utc),
        version=settings.VERSION,
        uptime=settings.get_uptime_seconds()
    )
