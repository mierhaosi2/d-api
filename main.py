from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException
from loguru import logger

from app.core.config import settings
from app.api.router import api_router
from app.services import spotify as spotify_svc


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.PROJECT_NAME} 启动中...")
    yield
    logger.info(f"👋 {settings.PROJECT_NAME} 已关闭")


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


# Spotify Dashboard 里配置的 Redirect URI 是 /callback，这里直接接住
@app.get("/callback", tags=["spotify"], summary="Spotify OAuth 回调")
async def spotify_callback_root(
    code: str = Query(None),
    error: str = Query(None),
):
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify 授权失败: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="缺少授权码 code")

    token_data = await spotify_svc.exchange_code_for_token(code)
    return {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_in": token_data.get("expires_in"),
        "token_type": token_data.get("token_type"),
        "scope": token_data.get("scope"),
    }
