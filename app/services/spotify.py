import base64
import time
import urllib.parse

import httpx

from app.core.config import settings

# 内存缓存当前 access_token，避免每次请求都去刷新
_token_cache: dict = {"access_token": None, "expires_at": 0}

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# 需要申请的权限范围，按需增减
DEFAULT_SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
    "playlist-read-collaborative",
    "user-top-read",
    "user-read-recently-played",
]


def build_auth_url(state: str = "") -> str:
    """生成 Spotify OAuth 授权跳转链接"""
    params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "scope": " ".join(DEFAULT_SCOPES),
        "show_dialog": "true",
    }
    if state:
        params["state"] = state
    return f"{SPOTIFY_AUTH_URL}?{urllib.parse.urlencode(params)}"


def _basic_auth_header() -> str:
    """生成 Basic Auth 头（client_id:client_secret 的 base64）"""
    credentials = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}"
    return base64.b64encode(credentials.encode()).decode()


async def exchange_code_for_token(code: str) -> dict:
    """用授权码换取 access_token 和 refresh_token"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {_basic_auth_header()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """用 refresh_token 刷新 access_token"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {_basic_auth_header()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_auto_access_token() -> str:
    """
    自动用 .env 里的 SPOTIFY_REFRESH_TOKEN 换取 access_token。
    带内存缓存，token 未过期时直接复用，无需每次刷新。
    """
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    if not settings.SPOTIFY_REFRESH_TOKEN:
        raise ValueError("SPOTIFY_REFRESH_TOKEN 未配置，请先通过 /api/v1/spotify/login 完成授权")

    token_data = await refresh_access_token(settings.SPOTIFY_REFRESH_TOKEN)
    _token_cache["access_token"] = token_data["access_token"]
    _token_cache["expires_at"] = now + token_data.get("expires_in", 3600)
    return _token_cache["access_token"]


async def get_current_user(access_token: str) -> dict:
    """获取当前登录用户的 Spotify 个人信息"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_current_playing(access_token: str) -> dict | None:
    """获取当前正在播放的曲目"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me/player/currently-playing",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        return resp.json()


async def get_top_tracks(access_token: str, time_range: str = "medium_term", limit: int = 20) -> dict:
    """获取用户最常听的曲目（time_range: short_term / medium_term / long_term）"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me/top/tracks",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"time_range": time_range, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()


async def get_recently_played(access_token: str, limit: int = 20) -> dict:
    """获取最近播放记录"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me/player/recently-played",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json()
