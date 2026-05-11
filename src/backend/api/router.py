from fastapi import APIRouter
from api.endpoints import chat, models

api_router = APIRouter()
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(models.router, tags=["models"])
