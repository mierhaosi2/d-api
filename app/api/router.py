from fastapi import APIRouter

from app.api.endpoints import health, spotify

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(spotify.router, prefix="/spotify", tags=["spotify"])
