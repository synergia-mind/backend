from sqlmodel import SQLModel
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


# Generic message response
class Message(SQLModel):
   message: str


# Health check models
class HealthStatus(str, Enum):
    healthy = "healthy"
    degraded = "degraded"
    unhealthy = "unhealthy"


class ComponentStatus(str, Enum):
    up = "up"
    down = "down"


class ComponentCheck(BaseModel):
    status: ComponentStatus
    responseTime: Optional[float] = None
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: HealthStatus
    timestamp: datetime
    version: Optional[str] = None
    uptime: Optional[float] = None