# Developer Guide

This document provides detailed information for developers working on the Synergia-Mind backend.

## 📚 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Development Setup](#development-setup)
- [Code Structure](#code-structure)
- [Adding New Features](#adding-new-features)
- [Database Management](#database-management)
- [Configuration Management](#configuration-management)
- [Logging](#logging)
- [Testing](#testing)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Dependencies](#dependencies)
- [Deployment Preparation](#deployment-preparation)
- [Security Best Practices](#security-best-practices)

## 🏛️ Architecture Overview

### Application Design

The backend follows a **layered architecture** pattern:

```text
┌─────────────────────────────────────┐
│          FastAPI App                │
│        (app/main.py)                │
├─────────────────────────────────────┤
│          API Layer                  │
│    (app/api/routes/*.py)            │
│    Request/Response handling        │
├─────────────────────────────────────┤
│       Service Layer                 │
│      (app/services/)                │
│    Business logic & orchestration   │
├─────────────────────────────────────┤
│     Repository Layer                │
│    (app/repositories/)              │
│    Data access & queries            │
├─────────────────────────────────────┤
│         Data Models                 │
│        (app/models.py)              │
│    SQLModel tables & schemas        │
├─────────────────────────────────────┤
│      Database Layer                 │
│        (app/core/db.py)             │
│    Connection & session management  │
├─────────────────────────────────────┤
│      Core Infrastructure            │
│  (app/core/config.py, logging.py)   │
│    Configuration & logging          │
└─────────────────────────────────────┘
```

### Key Components

1. **Application Entry (`app/main.py`)**
   - FastAPI application initialization
   - Middleware configuration (CORS)
   - Router registration
   - Lifespan management

2. **API Layer (`app/api/`)**
   - Route definitions grouped by feature
   - Request/response handling
   - API versioning via prefix
   - Delegates to service layer

3. **Service Layer (`app/services/`)**
   - Business logic and validation
   - Orchestration of repository operations
   - Error handling and data transformation
   - Current services: `ModelService`, `ChatService`, `MessageService`

4. **Repository Layer (`app/repositories/`)**
   - Data access patterns
   - Database queries and operations
   - CRUD operations
   - Current repositories: `ModelRepository`, `ChatRepository`, `MessageRepository`

5. **Core (`app/core/`)**
   - `config.py`: Environment-based settings
   - `db.py`: Database engine and session management
   - `logging.py`: Centralized logging configuration

6. **Models (`app/models.py`)**
   - SQLModel table definitions (Model, Chat, Message)
   - Pydantic schemas for API requests/responses
   - Data validation and serialization

## 🔧 Development Setup

### 1. Install Dependencies

```bash
# Development dependencies
make install-dev
```

This uses `uv` for fast, reliable dependency management.

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.sample .env
```

Configure your settings (see `.env.sample` for all options):

```env
# Database - Update with your local PostgreSQL credentials
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=***CHANGE_ME***
POSTGRES_DB=synergia_mind

# Application
ENVIRONMENT=local
FRONTEND_HOST=http://localhost:5173
```

> **Security Note**: Never commit `.env` files. Use strong passwords for local development.

### 4. Work with Database Sessions

Use dependency injection to get database sessions:

```python
from fastapi import Depends
from sqlmodel import Session, select
from core.db import get_session
from models import Chat

@router.get("/chats/{chat_id}")
async def get_chat(chat_id: str, session: Session = Depends(get_session)):
    """Get a chat by ID."""
    statement = select(Chat).where(Chat.id == chat_id)
    chat = session.exec(statement).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat
```

**Database operation patterns:**

```python
# CREATE
new_chat = Chat(title="New Chat", user_id=user_id)
session.add(new_chat)
session.commit()
session.refresh(new_chat)

# READ
statement = select(Chat).where(Chat.user_id == user_id)
chats = session.exec(statement).all()

# UPDATE
statement = select(Chat).where(Chat.id == chat_id)
chat = session.exec(statement).first()
if chat:
    chat.title = "Updated Title"
    session.add(chat)
    session.commit()
    session.refresh(chat)

# DELETE (soft delete)
chat.is_deleted = True
session.add(chat)
session.commit()
```

### 5. Migrations

Run migrations to create the database schema:

```bash
make migrate-upgrade
```

This creates the following tables:

- `models` - AI model configurations
- `chats` - User chat sessions
- `messages` - Chat messages

### 4. Run Development Server

```bash
make dev
```

The server will start at `http://localhost:8000` with:

- Auto-reload disabled (for stability)
- All interfaces accessible (`0.0.0.0`)
- Port 8000

### 5. Access Documentation

- **Swagger UI**: <http://localhost:8000/api/v1/docs>
- **ReDoc**: <http://localhost:8000/api/v1/redoc>
- **OpenAPI JSON**: <http://localhost:8000/api/v1/openapi.json>

> **Note**: Documentation endpoints are automatically disabled in production mode.

## 📁 Code Structure

### File Organization

```text
app/
├── main.py                 # Application factory and setup
├── models.py              # SQLModel tables and Pydantic schemas
├── api/
│   ├── __init__.py
│   ├── main.py            # API router aggregation
│   └── routes/
│       ├── __init__.py
│       └── health.py      # Health check endpoints
├── services/              # Business logic layer
│   ├── __init__.py
│   ├── model.py           # Model service
│   ├── chat.py            # Chat service
│   └── message.py         # Message service
├── repositories/          # Data access layer
│   ├── __init__.py
│   ├── model.py           # Model repository
│   ├── chat.py            # Chat repository
│   └── message.py         # Message repository
├── core/
│   ├── __init__.py
│   ├── config.py          # Settings and configuration
│   ├── db.py              # Database engine and session
│   └── logging.py         # Logging setup
├── logs/                  # Application logs
└── tests/
    ├── conftest.py        # Pytest fixtures
    ├── routes/
    │   └── test_health.py
    ├── repositories/      # Repository layer tests
    │   ├── test_model.py
    │   ├── test_chat.py
    │   └── test_message.py
    └── services/          # Service layer tests
        ├── test_modelservice.py
        ├── test_chatservice.py
        └── test_messageservice.py
alembic/
├── env.py                 # Alembic environment
└── versions/              # Database migrations
```

## 🆕 Adding New Features

### 1. Create a New Route

**Step 1**: Create route file in `app/api/routes/`

```python
# app/api/routes/users.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from core.db import get_session
from models import UserPublic, UserCreate, User

router = APIRouter()

@router.get("/", response_model=list[UserPublic])
async def list_users(session: Session = Depends(get_session)):
    """List all users."""
    statement = select(User)
    users = session.exec(statement).all()
    return users

@router.post("/", response_model=UserPublic, status_code=201)
async def create_user(user: UserCreate, session: Session = Depends(get_session)):
    """Create a new user."""
    db_user = User.model_validate(user)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user
```

**Step 2**: Define models in `app/models.py`

```python
# Add to app/models.py
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
import uuid

# Database table model
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(max_length=255, unique=True)
    username: str = Field(max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# API schemas
class UserBase(SQLModel):
    email: str = Field(max_length=255)
    username: str = Field(max_length=100)

class UserCreate(UserBase):
    password: str

class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
```

**Step 3**: Register router in `app/api/main.py`

```python
# app/api/main.py
from api.routes.health import router as health_router
from api.routes.users import router as users_router  # Add this
from fastapi import APIRouter

router = APIRouter()

router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(users_router, prefix="/users", tags=["users"])  # Add this
```

### 2. Add Database Migration

After adding or modifying table models, create and apply a migration:

```bash
make migrate-create MSG="add users table"
make migrate-upgrade
```

> See [Database Management](#database-management) section for complete migration workflow and commands.

### 3. Create Repository Layer

Create a repository for data access:

```python
# app/repositories/user.py
from typing import Optional
from uuid import UUID
from sqlmodel import Session, select
from app.models import User, UserCreate, UserUpdate

class UserRepository:
    """Repository for User data access."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, user_data: UserCreate) -> User:
        """Create a new user."""
        db_user = User.model_validate(user_data)
        self.session.add(db_user)
        self.session.commit()
        self.session.refresh(db_user)
        return db_user
    
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        statement = select(User).where(User.id == user_id)
        return self.session.exec(statement).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()
    
    def list_all(self) -> list[User]:
        """List all users."""
        statement = select(User)
        return list(self.session.exec(statement).all())
    
    def update(self, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        """Update a user."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_user, key, value)
        
        self.session.add(db_user)
        self.session.commit()
        self.session.refresh(db_user)
        return db_user
    
    def delete(self, user_id: UUID) -> bool:
        """Soft delete a user."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            return False
        
        db_user.is_deleted = True
        self.session.add(db_user)
        self.session.commit()
        return True
```

### 4. Create Service Layer

Create a service for business logic:

```python
# app/services/user.py
from typing import Optional
from uuid import UUID
from sqlmodel import Session
from app.repositories.user import UserRepository
from app.models import User, UserCreate, UserUpdate, UserPublic

class UserService:
    """Service layer for User business logic."""
    
    def __init__(self, session: Session):
        self.repository = UserRepository(session)
    
    def create_user(self, user_data: UserCreate) -> UserPublic:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user as UserPublic
            
        Raises:
            ValueError: If email already exists
        """
        # Check if email exists
        existing_user = self.repository.get_by_email(user_data.email)
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")
        
        # Create user
        user = self.repository.create(user_data)
        return UserPublic.model_validate(user)
    
    def get_user(self, user_id: UUID) -> Optional[UserPublic]:
        """Get a user by ID."""
        user = self.repository.get_by_id(user_id)
        if not user:
            return None
        return UserPublic.model_validate(user)
    
    def list_users(self) -> list[UserPublic]:
        """List all non-deleted users."""
        users = self.repository.list_all()
        return [UserPublic.model_validate(user) for user in users if not user.is_deleted]
    
    def update_user(self, user_id: UUID, user_data: UserUpdate) -> Optional[UserPublic]:
        """Update a user."""
        user = self.repository.update(user_id, user_data)
        if not user:
            return None
        return UserPublic.model_validate(user)
    
    def delete_user(self, user_id: UUID) -> bool:
        """Soft delete a user."""
        return self.repository.delete(user_id)
```

### 5. Update Routes to Use Services

Update your routes to use the service layer:

```python
# app/api/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from uuid import UUID
from app.core.db import get_session
from app.models import UserPublic, UserCreate, UserUpdate
from app.services.user import UserService

router = APIRouter()

@router.get("/", response_model=list[UserPublic])
async def list_users(session: Session = Depends(get_session)):
    """List all users."""
    service = UserService(session)
    return service.list_users()

@router.post("/", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    session: Session = Depends(get_session)
):
    """Create a new user."""
    service = UserService(session)
    try:
        return service.create_user(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: UUID,
    session: Session = Depends(get_session)
):
    """Get a user by ID."""
    service = UserService(session)
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    return user

@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    session: Session = Depends(get_session)
):
    """Update a user."""
    service = UserService(session)
    user = service.update_user(user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    session: Session = Depends(get_session)
):
    """Delete a user."""
    service = UserService(session)
    if not service.delete_user(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
```

### 6. Add Configuration Settings

Update `app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # New setting
    MAX_CONNECTIONS: int = 10
    FEATURE_FLAG_NEW_FEATURE: bool = False
```

## 🗄️ Database Management

### Overview

The application uses PostgreSQL with SQLModel ORM. The schema includes tables for AI models, chat sessions, and messages. For complete schema details, see `doc/db.dbml`.

### Key Tables

- **models** - AI model configurations (providers, pricing)
- **chats** - User chat sessions
- **messages** - Chat history with AI responses

### Migration Workflow

**Best Practices:**

- Always review generated migrations before applying
- Test migrations in development first  
- Use descriptive messages
- Keep migrations atomic (one logical change)
- Never edit applied migrations

**Steps:**

1. **Modify models** in `app/models.py`
2. **Create migration**: `make migrate-create MSG="description"`
3. **Review** generated file in `alembic/versions/`
4. **Apply migration**: `make migrate-upgrade`

### Common Commands

```bash
make migrate-create MSG="add new table"  # Create migration
make migrate-upgrade                      # Apply migrations
make migrate-current                      # Check version
make migrate-history                      # View history
```

> **Warning**: `make migrate-reset` destroys all data. Only use in development.

### Database Connection

Configure via environment variables in `.env`:

```env
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=***SECURE_PASSWORD***
POSTGRES_DB=synergia_mind
```

Connection uses `postgresql+psycopg` adapter (configured in `app/core/config.py`).

## ⚙️ Configuration Management

### Settings Priority

1. Environment variables (highest priority)
2. `.env` file
3. Default values in `Settings` class

### Accessing Settings

```python
from core.config import settings

# Use settings (already instantiated)
if settings.IS_PRODUCTION:
    # Production-specific logic
    pass

# Get database connection
db_uri = settings.SQLALCHEMY_DATABASE_URI
```

### Environment-Specific Behavior

```python
# Example: Conditional feature based on environment
@app.get("/debug")
async def debug_info():
    if settings.IS_PRODUCTION:
        raise HTTPException(status_code=404)
    return {"environment": settings.ENVIRONMENT}
```

## 📝 Logging

### Getting a Logger

```python
from core.logging import get_logger

logger = get_logger(__name__)

# Use logger
logger.info("Processing request")
logger.error("Error occurred", exc_info=True)
logger.debug("Debug information")
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages
- **ERROR**: Error messages

### Log Files

Logs are stored in `app/logs/` with:

- Maximum size: 10MB per file
- Rotation: 3 backup files
- Format: `timestamp - logger_name - level - message`

### Noisy Logger Suppression

The following loggers are set to WARNING level to reduce noise:

- `uvicorn`
- `watchfiles`
- `passlib`
- `azure`

## 🧪 Testing

### Test Structure

```text
app/tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── routes/
│   └── test_health.py       # Route tests
├── repositories/            # Repository layer tests
│   ├── test_model.py
│   ├── test_chat.py
│   └── test_message.py
└── services/                # Service layer tests
    ├── test_modelservice.py
    ├── test_chatservice.py
    └── test_messageservice.py
```

### Writing Tests

#### Test Fixtures

```python
# app/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from app.main import app
from app.core.db import get_session

@pytest.fixture(name="client")
def client_fixture():
    """Create a test client."""
    client = TestClient(app)
    yield client

@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
```

#### Repository Tests

```python
# app/tests/repositories/test_model.py
import pytest
from uuid import uuid4
from app.repositories.model import ModelRepository
from app.models import ModelCreate

def test_create_model(session):
    """Test creating a model."""
    repository = ModelRepository(session)
    model_data = ModelCreate(
        name="GPT-4",
        provider="OpenAI",
        price_per_million_tokens=10.0,
        is_enabled=True
    )
    
    model = repository.create(model_data)
    
    assert model.id is not None
    assert model.name == "GPT-4"
    assert model.provider == "OpenAI"

def test_get_by_id(session):
    """Test retrieving a model by ID."""
    repository = ModelRepository(session)
    
    # Create a model
    model_data = ModelCreate(
        name="Claude",
        provider="Anthropic",
        price_per_million_tokens=15.0
    )
    created_model = repository.create(model_data)
    
    # Retrieve it
    retrieved_model = repository.get_by_id(created_model.id)
    
    assert retrieved_model is not None
    assert retrieved_model.id == created_model.id
    assert retrieved_model.name == "Claude"
```

#### Service Tests

```python
# app/tests/services/test_modelservice.py
import pytest
from uuid import uuid4
from app.services.model import ModelService
from app.models import ModelCreate

def test_create_model_success(session):
    """Test successful model creation."""
    service = ModelService(session)
    model_data = ModelCreate(
        name="GPT-4",
        provider="OpenAI",
        price_per_million_tokens=10.0
    )
    
    model = service.create_model(model_data)
    
    assert model.id is not None
    assert model.name == "GPT-4"

def test_create_duplicate_model_fails(session):
    """Test that creating a duplicate model raises an error."""
    service = ModelService(session)
    model_data = ModelCreate(
        name="GPT-4",
        provider="OpenAI",
        price_per_million_tokens=10.0
    )
    
    # Create first model
    service.create_model(model_data)
    
    # Attempt to create duplicate
    with pytest.raises(ValueError, match="already exists"):
        service.create_model(model_data)
```

#### Route Tests

```python
# app/tests/routes/test_health.py
from fastapi.testclient import TestClient
from app.core import settings
from app.models import HealthStatus

def test_health_check(client: TestClient):
    """Test the health check endpoint to ensure it returns a healthy status."""
    response = client.get(f"{settings.API_V1_STR}/health/")
    assert response.status_code == 200
    assert response.json().get("status", "") == HealthStatus.healthy
```

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage report
make test-cov

# Run specific test file
uv run pytest app/tests/services/test_modelservice.py

# Run specific test function
uv run pytest app/tests/services/test_modelservice.py::test_create_model_success

# Run with verbose output
uv run pytest -v

# Run with print statements visible
uv run pytest -s
```

### Test Coverage

The project maintains comprehensive test coverage across all layers:

- **Repository Layer**: CRUD operations, edge cases, error handling
- **Service Layer**: Business logic, validation, error scenarios
- **API Layer**: Endpoint responses, status codes, error handling

Current coverage includes:
- `ModelRepository` and `ModelService`
- `ChatRepository` and `ChatService`
- `MessageRepository` and `MessageService`

## ✨ Best Practices

### 1. Type Hints

Always use type hints for better IDE support and runtime validation:

```python
# ✅ Good
async def get_user(user_id: int) -> UserResponse:
    pass

# ❌ Avoid
async def get_user(user_id):
    pass
```

### 2. Pydantic Models

Use Pydantic for all data validation:

```python
# ✅ Good
class UserCreate(BaseModel):
    email: EmailStr
    age: int = Field(..., ge=0, le=150)

# ❌ Avoid
def create_user(email: str, age: int):
    if not email or age < 0:
        raise ValueError("Invalid input")
```

### 3. Async/Await

Use async functions for I/O operations:

```python
# ✅ Good
@router.get("/")
async def read_items():
    items = await database.fetch_all()
    return items

# ❌ Avoid blocking operations
@router.get("/")
def read_items():
    items = database.fetch_all_sync()  # Blocks event loop
    return items
```

### 4. Error Handling

```python
from fastapi import HTTPException, status

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await user_service.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    return user
```

### 5. Dependency Injection

```python
from fastapi import Depends

def get_current_user(token: str = Depends(oauth2_scheme)):
    # Decode token and return user
    pass

@router.get("/me")
async def read_current_user(user = Depends(get_current_user)):
    return user
```

### 6. Documentation

Use docstrings and OpenAPI descriptions:

```python
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    """
    Create a new user.
    
    - **email**: Valid email address
    - **username**: Unique username (3-50 characters)
    - **password**: Strong password (min 8 characters)
    """
    return await user_service.create(user)
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Solution**: Run from project root and ensure paths are correct:

```bash
cd backend
make dev
```

#### 2. CORS Errors

**Problem**: Frontend can't access API

**Solution**: Check CORS settings in `.env`:

```env
FRONTEND_HOST=http://localhost:5173
BACKEND_CORS_ORIGINS=http://localhost:5173
```

#### 3. Port Already in Use

**Problem**: `Address already in use`

**Solution**:

```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uv run fastapi dev app/main.py --port 8001
```

#### 4. Logs Not Writing

**Problem**: Log files not created

**Solution**: Ensure logs directory exists and has write permissions:

```bash
mkdir -p app/logs
chmod 755 app/logs
```

#### 5. Database Connection Errors

**Problem**: `could not connect to server` or connection refused

**Solution**:

```bash
# Check if PostgreSQL is running (macOS example)
brew services list | grep postgresql

# Verify .env configuration (don't log passwords!)
echo "Server: $POSTGRES_SERVER, DB: $POSTGRES_DB"
```

#### 6. Migration Conflicts

**Problem**: Alembic detects conflicting changes

**Solution**:

```bash
# Check current state
make migrate-current

# If needed, manually resolve conflicts in migration file
# Or rollback and recreate
make migrate-downgrade
make migrate-create MSG="fixed migration"
```

### Debug Mode

Enable debug logging:

```env
LOG_LEVEL=DEBUG
```

### Checking Application Health

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "timestamp": "2025-10-22T10:30:00.000Z",
  "version": "0.1.0",
  "uptime": 123.45
}
```

## 📦 Dependencies

### Production Dependencies

- **fastapi[standard]**: Web framework (v0.119.1+)
- **pydantic**: Data validation (v2.12.3+)
- **pydantic-settings**: Settings management (v2.11.0+)
- **sqlmodel**: SQL ORM with Pydantic integration (v0.0.27+)
- **psycopg**: PostgreSQL adapter (v3.2.11+)
- **alembic**: Database migrations (v1.17.0+)

### Development Dependencies

- **pytest**: Testing framework (v8.4.2+)
- **pytest-cov**: Coverage reporting (v7.11.0+)
- **coverage**: Code coverage measurement (v7.11.0+)
- **httpx**: Async HTTP client for TestClient (v0.28.1+)
- **ruff**: Fast Python linter and formatter (v0.14.1+)

### Managing Dependencies

```bash
# Add production dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Update all dependencies
uv sync

# Update specific package
uv add --upgrade package-name
```

## 🚀 Deployment Preparation

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in production environment
- [ ] Configure proper CORS origins
- [ ] Set up proper secret management (not in `.env`)
- [ ] Configure production database with connection pooling
- [ ] Run all migrations: `make migrate-upgrade`
- [ ] Enable HTTPS only
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Implement rate limiting
- [ ] Set up health check monitoring
- [ ] Configure backup strategy for database
- [ ] Set appropriate `LOG_LEVEL` (INFO or WARNING)

### Production Settings

```env
ENVIRONMENT=production
LOG_LEVEL=WARNING

# Use environment-specific secrets management
# Examples: AWS Secrets Manager, Azure Key Vault, HashiCorp Vault
POSTGRES_SERVER=${DATABASE_HOST}
POSTGRES_USER=${DATABASE_USER}
POSTGRES_PASSWORD=${DATABASE_PASSWORD}
POSTGRES_DB=${DATABASE_NAME}
```

> **Security**: Never hardcode production credentials. Use your cloud provider's secrets management service.

## 🔐 Security Best Practices

### Development

1. **Never commit `.env` files** (already in `.gitignore`)
2. **Use strong local passwords** - even in development
3. **Rotate credentials regularly**
4. **Sanitize logs** - never log passwords, tokens, or PII

### Production

1. **Use secrets management services** (AWS Secrets Manager, Azure Key Vault, etc.)
2. **Enable HTTPS only** (configure at reverse proxy/load balancer)
3. **Implement rate limiting** on all public endpoints
4. **Enable database SSL/TLS** connections
5. **Use read-only database users** where possible
6. **Regular security audits** and dependency updates
7. **Minimize exposed error details** in production responses

### Code Level

1. **Validate all inputs** using Pydantic models
2. **Parameterize SQL queries** (SQLModel does this automatically)
3. **Implement proper authentication/authorization**
4. **Use CORS restrictively** - only allow known origins
5. **Set security headers** (CSP, HSTS, X-Frame-Options)

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

## 🏗️ Design Patterns

### Repository Pattern

The repository pattern provides a clean separation between data access logic and business logic:

**Benefits:**
- Centralizes data access logic
- Makes testing easier with mock repositories
- Allows switching data sources without changing business logic
- Provides consistent interface for data operations

**Example:**
```python
# Repository handles only data access
class ChatRepository:
    def get_by_id(self, chat_id: UUID) -> Optional[Chat]:
        statement = select(Chat).where(Chat.id == chat_id)
        return self.session.exec(statement).first()

# Service uses repository for business logic
class ChatService:
    def get_chat(self, chat_id: UUID) -> Optional[ChatPublic]:
        chat = self.repository.get_by_id(chat_id)
        if not chat or chat.is_deleted:
            return None
        return ChatPublic.model_validate(chat)
```

### Service Layer Pattern

The service layer encapsulates business logic and orchestrates operations:

**Benefits:**
- Keeps routes thin and focused on HTTP concerns
- Centralizes business rules and validation
- Enables code reuse across different endpoints
- Simplifies testing of business logic

**Example:**
```python
# Service handles validation and orchestration
class MessageService:
    def create_message(self, message_data: MessageCreate) -> MessagePublic:
        # Validate chat exists
        chat = self.chat_repository.get_by_id(message_data.chat_id)
        if not chat:
            raise ValueError("Chat not found")
        
        # Validate model exists and is enabled
        model = self.model_repository.get_by_id(message_data.model_id)
        if not model or not model.is_enabled:
            raise ValueError("Model not available")
        
        # Create message
        message = self.repository.create(message_data)
        return MessagePublic.model_validate(message)
```

### Dependency Injection

FastAPI's dependency injection system is used throughout:

```python
# Define dependency
def get_session():
    with Session(engine) as session:
        yield session

# Use in routes
@router.get("/chats/{chat_id}")
async def get_chat(
    chat_id: UUID,
    session: Session = Depends(get_session)
):
    service = ChatService(session)
    return service.get_chat(chat_id)
```

---

**Last Updated**: October 24, 2025  
**Current Version**: 0.1.0
