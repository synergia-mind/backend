from fastapi import APIRouter
from datetime import datetime, timezone
from app.models import HealthCheckResponse, HealthStatus
from app.core import settings

router = APIRouter()



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
