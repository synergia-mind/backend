import secrets
from pathlib import Path
from typing import Annotated, Any, Literal
from datetime import datetime, timezone

from pydantic import (AnyUrl, BeforeValidator, EmailStr, PostgresDsn,
                      computed_field, Field)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)

class Settings(BaseSettings):
    """
    Settings for configuring logging in the application.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore any extra fields not defined in the model
    )

    LOG_LEVEL: str = "INFO"  # Default logging level

    TITLE: str = "Synergia-mind API"
    DESCRIPTION: str = "This is the backend API for Synergia-mind, providing various endpoints for development purposes."
    VERSION: str = "0.1.0"

    ENVIRONMENT: Literal["local", "production"] = "local"  # Default environment
    
    # Application start time for uptime tracking
    APP_START_TIME: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    API_V1_STR: str = "/api/v1"
    FRONTEND_HOST: str = "http://localhost:5173"

    # Path to the data directory
    BASE_DIR: Path = Path().resolve() / "app"
    LOG_DIR: Path = BASE_DIR / "logs"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "sampledb"

    # Clerk Authentication
    CLERK_SECRET_KEY: str = "your-clerk-secret-key"

    @property
    def IS_PRODUCTION(self) -> bool:
        """
        Check if the application is running in production environment.

        Returns:
            bool: True if in production, False otherwise.
        """
        return self.ENVIRONMENT.lower() == "production"
    
    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn(MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        ))
    
    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]
    
    def get_uptime_seconds(self) -> float:
        """
        Calculate application uptime in seconds.
        
        Returns:
            float: Uptime in seconds since application start.
        """
        return (datetime.now(timezone.utc) - self.APP_START_TIME).total_seconds()
