import logging
import logging.handlers

from app.core.config import Settings

settings = Settings()

# Global logger instance - initialized once
_logger = None


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up logging for the entire application.
    Call this once at startup.

    Args:
        level: Log level ("DEBUG", "INFO", "WARNING", "ERROR")

    Returns:
        Configured logger instance
    """
    global _logger

    if _logger is not None:
        return _logger

    # Create logs directory
    logs_dir = settings.LOG_DIR
    logs_dir.mkdir(exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.handlers.RotatingFileHandler(
                logs_dir / "app.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=3,
            ),
        ],
    )

    # Reduce noise from dependencies
    noisy_loggers = ["uvicorn", "watchfiles", "passlib", "azure"]
    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
        logger.propagate = False

    _logger = logging.getLogger("app")
    return _logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance. Call setup_logging() first.

    Args:
        name: Optional logger name (usually __name__)

    Returns:
        Logger instance
    """
    if _logger is None:
        setup_logging()

    if name:
        return logging.getLogger(f"app.{name}")
    return logging.getLogger("app")
