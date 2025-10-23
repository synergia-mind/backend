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
# Modify as you need 
cp .env.sample .env
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
│   ├── models.py            # Pydantic/SQLModel data models
│   ├── api/
│   │   ├── main.py          # API router aggregation
│   │   └── routes/
│   │       └── health.py    # Health check endpoints
│   ├── core/
│   │   ├── config.py        # Application settings
│   │   └── logging.py       # Logging configuration
│   └── logs/                # Application logs directory
├── doc/
│   ├── db.dbml              # Database schema definition
│   └── openapi.yml          # OpenAPI specification
├── pyproject.toml           # Project dependencies
├── Makefile                 # Development commands
└── README.md                # This file
```

## 🛠️ Technology Stack

- **Framework:** FastAPI 0.119.1+
- **Validation:** Pydantic 2.12.3+
- **Settings:** Pydantic Settings 2.11.0+
- **ORM:** SQLModel 0.0.27+
- **Package Manager:** uv

## 📝 Available Make Commands

There are make commands to make the setup process easier. you can check those using:

```bash
make help          # Show all available commands
```

## 🤝 Contributing

See [DEVELOPER.md](./DEVELOPER.md) for detailed development guidelines and architecture information.

## 📄 License

See [LICENSE](./LICENSE) file for details.
