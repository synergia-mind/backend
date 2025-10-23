from contextlib import asynccontextmanager

from app.api.main import router as api_router
from app.core import settings
from app.core.logging import get_logger
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

logger = get_logger(__name__)

def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    logger.info(
        f"Starting application in {settings.ENVIRONMENT} mode with log level {settings.LOG_LEVEL}"
        )
    yield
    logger.info("Ending application lifespan")

app = FastAPI(
    title=settings.TITLE,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url=f"{settings.API_V1_STR}/docs" if not settings.IS_PRODUCTION else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if not settings.IS_PRODUCTION else None,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if not settings.IS_PRODUCTION else None,
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)