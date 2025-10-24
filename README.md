# Synergia-Mind Backend

Backend API service for the Synergia-Mind application, built with FastAPI and modern Python tooling.

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Install dependencies
make install-dev

# Copy environment configuration
cp .env.sample .env
# Edit .env with your database credentials and other settings
```

### Database Setup

```bash
# Run database migrations
make migrate-upgrade
```

### Running the Application

```bash
# Start development server
make dev
```

### API Documentation

For a complete list of available endpoints, see:

- Interactive documentation: `http://localhost:8000/api/v1/docs` (when running locally)
- OpenAPI specification: [doc/openapi.yml](./doc/openapi.yml)

## 🏗️ Project Structure

```text
backend/
├── app/
│   ├── main.py              # Application entry point
│   ├── models.py            # SQLModel data models and schemas
│   ├── api/
│   │   ├── main.py          # API router aggregation
│   │   └── routes/
│   │       └── health.py    # Health check endpoints
│   ├── core/
│   │   ├── config.py        # Application settings & environment configuration
│   │   ├── db.py            # Database engine and session management
│   │   └── logging.py       # Logging configuration
│   ├── repositories/        # Data access layer
│   │   ├── model.py         # Model repository
│   │   ├── chat.py          # Chat repository
│   │   └── message.py       # Message repository
│   ├── services/            # Business logic layer
│   │   ├── model.py         # Model service
│   │   ├── chat.py          # Chat service
│   │   └── message.py       # Message service
│   ├── logs/                # Application logs directory
│   └── tests/               # Test suite
│       ├── conftest.py      # Pytest configuration
│       ├── routes/
│       │   └── test_health.py
│       ├── repositories/    # Repository layer tests
│       │   ├── test_model.py
│       │   ├── test_chat.py
│       │   └── test_message.py
│       └── services/        # Service layer tests
│           ├── test_modelservice.py
│           ├── test_chatservice.py
│           └── test_messageservice.py
├── alembic/
│   ├── env.py               # Alembic environment configuration
│   └── versions/            # Database migration files
├── doc/
│   ├── db.dbml              # Database schema definition
│   └── openapi.yml          # OpenAPI specification
├── alembic.ini              # Alembic configuration
├── pyproject.toml           # Project dependencies
├── Makefile                 # Development commands
└── README.md                # This file
```

## 🛠️ Technology Stack

- **Framework:** FastAPI 0.119.1+
- **ORM:** SQLModel 0.0.27+
- **Database:** PostgreSQL (via psycopg 3.2.11+)
- **Migrations:** Alembic 1.17.0+
- **Validation:** Pydantic 2.12.3+
- **Settings:** Pydantic Settings 2.11.0+
- **Testing:** pytest 8.4.2+ with coverage 7.11.0+
- **Code Quality:** Ruff 0.14.1+
- **Package Manager:** uv

## 🏛️ Architecture

The application follows a **layered architecture** pattern:

- **API Layer** (`app/api/routes/`) - HTTP endpoints and request/response handling
- **Service Layer** (`app/services/`) - Business logic and orchestration
- **Repository Layer** (`app/repositories/`) - Data access and database operations
- **Models** (`app/models.py`) - SQLModel tables and Pydantic schemas
- **Core** (`app/core/`) - Configuration, database, and logging infrastructure

This separation ensures clean code organization, testability, and maintainability.

## 📝 Available Make Commands

To check make commands:

```bash
make help              # Show all available commands
```

### Development Commands

```bash
make dev               # Start development server
make test              # Run all tests
make test-cov          # Run tests with coverage report
make lint              # Run code quality checks
make format            # Format code with ruff
```

### Database Migration Commands

```bash
make migrate-create MSG="description"  # Create a new migration
make migrate-upgrade                   # Apply all pending migrations
make migrate-downgrade                 # Rollback one migration
make migrate-current                   # Show current migration
make migrate-history                   # Show migration history
make migrate-reset                     # Reset to base migration (WARNING: destructive)
```

## 🗄️ Database Schema

The application uses PostgreSQL with the following main tables:

- **models** - AI model configurations (name, provider, pricing)
- **chats** - User chat sessions (title, summary, user association)
- **messages** - Chat messages with AI model associations (type, content, tokens, feedback)

### Key Features

- **Repository Pattern**: Clean data access layer for each entity
- **Service Layer**: Business logic with validation and error handling
- **Comprehensive Testing**: Full test coverage for repositories and services
- **Type Safety**: SQLModel integration with Pydantic validation

See [doc/db.dbml](./doc/db.dbml) for the complete database schema.

## 🤝 Contributing

See [DEVELOPER.md](./DEVELOPER.md) for detailed development guidelines and architecture information.

## 📄 License

See [LICENSE](./LICENSE) file for details.
