from fastapi import APIRouter

from app.api.endpoints import health, spotify, lyrics

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(spotify.router, prefix="/spotify", tags=["spotify"])
api_router.include_router(lyrics.router, prefix="/lyrics", tags=["lyrics"])
