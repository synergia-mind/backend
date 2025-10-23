from app.core.config import Settings
from app.core.logging import setup_logging
from functools import lru_cache

@lru_cache(maxsize=1)
def get_settings():
    return Settings()

settings = get_settings()

setup_logging(settings.LOG_LEVEL)