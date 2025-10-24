from app.api.routes.health import router as health_router
from app.api.routes.model import router as model_router
from app.core.auth import verify_clerk_session
from fastapi import APIRouter, Depends

router = APIRouter()

router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(model_router, prefix="/models", tags=["models"], dependencies=[Depends(verify_clerk_session)])
