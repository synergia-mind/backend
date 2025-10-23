# Developer Guide

This document provides detailed information for developers working on the Synergia-Mind backend.

## 📚 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Development Setup](#development-setup)
- [Code Structure](#code-structure)
- [Adding New Features](#adding-new-features)
- [Configuration Management](#configuration-management)
- [Logging](#logging)
- [Testing](#testing)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

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
├─────────────────────────────────────┤
│        Business Logic               │
│         (Future: services/)         │
├─────────────────────────────────────┤
│         Data Models                 │
│        (app/models.py)              │
├─────────────────────────────────────┤
│      Core Infrastructure            │
│  (app/core/config.py, logging.py)   │
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

3. **Core (`app/core/`)**
   - `config.py`: Environment-based settings
   - `logging.py`: Centralized logging configuration

4. **Models (`app/models.py`)**
   - Pydantic models for validation
   - SQLModel for future database integration
   - Request/response schemas

## 🔧 Development Setup

### 1. Install Dependencies

```bash
# Development dependencies
make install-dev
```

This uses `uv` for fast, reliable dependency management.

### 2. Environment Configuration

Create a `.env` file in the project root:

```shell
copy .env.sample .env
```

### 3. Run Development Server

```bash
make dev
```

The server will start at `http://localhost:8000` with:

- Auto-reload disabled (for stability)
- All interfaces accessible (`0.0.0.0`)
- Port 8000

### 4. Access Documentation

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

> **Note**: Documentation endpoints are automatically disabled in production mode.

## 📁 Code Structure

### File Organization

```
app/
├── main.py                 # Application factory and setup
├── models.py              # All data models
├── api/
│   ├── __init__.py
│   ├── main.py            # API router aggregation
│   └── routes/
│       ├── __init__.py
│       └── health.py      # Health check endpoints
└── core/
    ├── __init__.py
    ├── config.py          # Settings and configuration
    └── logging.py         # Logging setup
```

## 🆕 Adding New Features

### 1. Create a New Route

**Step 1**: Create route file in `app/api/routes/`

```python
# app/api/routes/users.py
from fastapi import APIRouter
from models import UserResponse, UserCreate

router = APIRouter()

@router.get("/", response_model=list[UserResponse])
async def list_users():
    """List all users."""
    # Implementation here
    pass

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    """Create a new user."""
    # Implementation here
    pass
```

**Step 2**: Define models in `app/models.py`

```python
# Add to app/models.py
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
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

### 2. Add Configuration Settings

Update `app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # New setting
    DATABASE_URL: PostgresDsn
    MAX_CONNECTIONS: int = 10
```

### 3. Create Service Layer (Future)

For complex business logic, create a service:

```python
# app/services/user_service.py
from models import UserCreate, UserResponse

class UserService:
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        # Business logic here
        pass
```

## ⚙️ Configuration Management

### Settings Priority

1. Environment variables (highest priority)
2. `.env` file
3. Default values in `Settings` class

### Accessing Settings

```python
from core.config import Settings

settings = Settings()

# Use settings
if settings.IS_PRODUCTION:
    # Production-specific logic
    pass
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
├── conftest.py           # Pytest fixtures
└── routes/
    └── test_health.py    # Health check tests
```

### Writing Tests

```python
# app/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(name="client")
def client_fixture():
    """Create a test client."""
    client = TestClient(app)
    yield client

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
# Run tests with coverage
make test

# This executes:
# uv run coverage run --source=app -m pytest
# uv run coverage report --show-missing
```

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

- **fastapi[standard]**: Web framework with built-in validation
- **pydantic**: Data validation using Python type annotations
- **pydantic-settings**: Settings management
- **sqlmodel**: SQL databases with Python objects

### Development Dependencies

Add to `pyproject.toml` when needed using UV:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.24.0",  # For TestClient
    "ruff>=0.1.0",    # Linting
]
```

## 🚀 Deployment Preparation

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in production environment
- [ ] Configure proper CORS origins
- [ ] Set up proper secret management (not in `.env`)
- [ ] Enable HTTPS only
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Database connection pooling
- [ ] Rate limiting
- [ ] Health check monitoring

### Production Settings

```env
ENVIRONMENT=production
LOG_LEVEL=INFO
BACKEND_CORS_ORIGINS=https://app.example.com
```

## 🔐 Security Considerations

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Use secrets management** for sensitive data in production
3. **Enable HTTPS** in production (handled by reverse proxy)
4. **Validate all inputs** using Pydantic models
5. **Rate limit** API endpoints (future: add rate limiting middleware)
6. **Sanitize logs** - avoid logging sensitive data

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

---

**Last Updated**: October 22, 2025  
**Current Version**: 0.1.0
