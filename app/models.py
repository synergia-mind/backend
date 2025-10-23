from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime, timezone
from enum import Enum
from decimal import Decimal
import uuid


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

# ==============================================
# Model table models
class ModelBase(SQLModel):
    name: str = Field(max_length=255)
    provider: str = Field(max_length=100)
    price_per_million_tokens: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=6)
    is_enabled: bool = Field(default=True)


class Model(ModelBase, table=True):
    __tablename__ = "models"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelCreate(ModelBase):
    pass


class ModelUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=255)
    provider: Optional[str] = Field(default=None, max_length=100)
    price_per_million_tokens: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=6)
    is_enabled: Optional[bool] = None


class ModelPublic(ModelBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

# ==============================================