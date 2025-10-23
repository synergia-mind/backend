from core.config import Settings
from core.logging import get_logger
from sqlmodel import Session, SQLModel, create_engine, select

settings = Settings()
logger = get_logger(__name__)


# Postgres engine
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

def get_session():
    """
    Get a new SQLModel session.
    """
    logger.debug("Creating new database session")
    with Session(engine) as session:
        yield session