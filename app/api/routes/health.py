from fastapi import APIRouter
from models import Message

router = APIRouter()


@router.get("/", status_code=200, response_model=Message)
async def health_check():
    return Message(message="healthy")
