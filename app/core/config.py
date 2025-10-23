import secrets
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (AnyUrl, BeforeValidator, EmailStr, PostgresDsn,
                      computed_field)
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

    API_V1_STR: str = "/api/v1"
    FRONTEND_HOST: str = "http://localhost:5173"

    # Path to the data directory
    BASE_DIR: Path = Path().resolve() / "app"
    LOG_DIR: Path = BASE_DIR / "logs"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

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
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]
