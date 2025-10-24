from app.api.routes.health import router as health_router
from app.api.routes.model import router as model_router
from app.api.routes.chat import router as chat_router
from app.api.auth import verify_clerk_session
from fastapi import APIRouter, Depends

router = APIRouter()

router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(model_router, prefix="/models", tags=["models"], dependencies=[Depends(verify_clerk_session)])
router.include_router(chat_router, prefix="/chats", tags=["chats"], dependencies=[Depends(verify_clerk_session)])
