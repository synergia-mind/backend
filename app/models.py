from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime, timezone
from enum import Enum
from decimal import Decimal
import uuid


# Generic message response
class MessageResponse(SQLModel):
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
    price_per_million_tokens: Decimal = Field(max_digits=10, decimal_places=6)
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
# Chat table models
class ChatBase(SQLModel):
    title: Optional[str] = Field(default=None, max_length=500)
    summary: Optional[str] = None


class Chat(ChatBase, table=True):
    __tablename__ = "chats"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str = Field(max_length=255)
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatCreate(ChatBase):
    pass


class ChatUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=500)
    summary: Optional[str] = None


class ChatPublic(ChatBase):
    id: uuid.UUID
    user_id: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class ChatPublicWithMessages(ChatPublic):
    messages: list["MessagePublic"] = []

# ==============================================
# Message table models
class MessageType(str, Enum):
    user = "user"
    assistant = "ai"
    system = "system"


class MessageFeedback(str, Enum):
    positive = "positive"
    negative = "negative"


class MessageBase(SQLModel):
    chat_id: uuid.UUID
    model_id: uuid.UUID
    type: MessageType
    content: str
    tokens: Optional[int] = None
    feedback: Optional[str] = Field(default=None, max_length=20)
    is_deleted: bool = Field(default=False)


class Message(MessageBase, table=True):
    __tablename__ = "messages"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MessageCreate(SQLModel):
    chat_id: uuid.UUID
    model_id: uuid.UUID
    type: str = Field(max_length=50)
    content: str
    tokens: Optional[int] = None


class MessageUpdate(SQLModel):
    model_id: Optional[uuid.UUID] = None
    type: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = None
    tokens: Optional[int] = None
    feedback: Optional[str] = Field(default=None, max_length=20)
    is_deleted: Optional[bool] = None


class MessagePublic(MessageBase):
    id: uuid.UUID
    model: ModelPublic
    created_at: datetime
    updated_at: datetime

# ==============================================
# Bulk operation models
class BulkOperationResponse(BaseModel):
    """Response model for bulk operations."""
    successful: int
    failed: int
    total: int


class ChatBulkOperationRequest(BaseModel):
    """Request model for bulk operations on chats."""
    chat_ids: list[uuid.UUID]


class MessageBulkOperationRequest(BaseModel):
    """Request model for bulk operations on messages."""
    message_ids: list[uuid.UUID]

# ==============================================
# Message-specific request/response models
class MessageWithAutoChatRequest(BaseModel):
    """Request model for creating a message with automatic chat creation."""
    model_id: uuid.UUID
    content: str
    message_type: str = "user"
    tokens: Optional[int] = None
    chat_title: Optional[str] = None


class MessageWithAutoChatResponse(BaseModel):
    """Response model for creating a message with automatic chat creation."""
    message: MessagePublic
    chat_id: uuid.UUID


class MessageFeedbackRequest(BaseModel):
    """Request model for updating message feedback."""
    feedback: str


class ConversationSummaryResponse(BaseModel):
    """Response model for conversation summary statistics."""
    total_messages: int
    user_messages: int
    ai_messages: int
    system_messages: int
    total_tokens: int
    total_cost: float
    latest_message_at: Optional[datetime] = None

# ==============================================