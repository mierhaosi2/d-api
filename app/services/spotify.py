import asyncio
import base64
import time
import urllib.parse

import httpx
from fastapi import HTTPException

from app.core.config import settings

# access_token 内存缓存
_token_cache: dict = {"access_token": None, "expires_at": 0}
# 防止并发请求同时触发 token 刷新
_token_lock = asyncio.Lock()

# 各接口响应缓存：{ cache_key: (data, expires_at) }
_response_cache: dict = {}

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

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

# 各接口缓存时长（秒）
_CACHE_TTL = {
    "playing": 5,           # 正在播放：5 秒（需要实时感）
    "recently_played": 60,  # 最近播放：60 秒
    "top_tracks": 3600,     # Top Tracks：1 小时（变化极慢）
    "me": 3600,             # 用户信息：1 小时
}


def _get_cache(key: str):
    entry = _response_cache.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _set_cache(key: str, data, ttl: int):
    _response_cache[key] = (data, time.time() + ttl)


def _handle_spotify_error(resp: httpx.Response):
    """统一处理 Spotify API 错误，转为 FastAPI HTTPException"""
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After", "30")
        raise HTTPException(
            status_code=429,
            detail=f"Spotify 请求过于频繁，请 {retry_after} 秒后重试",
            headers={"Retry-After": retry_after},
        )
    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Spotify Token 已过期，请重新授权")
    if resp.status_code == 403:
        raise HTTPException(status_code=403, detail="权限不足，请检查 Spotify 授权 Scope")
    resp.raise_for_status()


def build_auth_url(state: str = "") -> str:
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
    credentials = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}"
    return base64.b64encode(credentials.encode()).decode()


async def exchange_code_for_token(code: str) -> dict:
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
        _handle_spotify_error(resp)
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict:
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
        _handle_spotify_error(resp)
        return resp.json()


async def get_auto_access_token() -> str:
    now = time.time()
    # 先检查缓存，有效则直接返回，不用加锁
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    # 加锁：保证并发请求只有一个真正去刷 token，其余等待复用结果
    async with _token_lock:
        # 进锁后再检查一次，防止前一个请求已经刷好了
        now = time.time()
        if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
            return _token_cache["access_token"]

        if not settings.SPOTIFY_REFRESH_TOKEN:
            raise HTTPException(
                status_code=503,
                detail="SPOTIFY_REFRESH_TOKEN 未配置，请先通过 /api/v1/spotify/login 完成授权",
            )

        token_data = await refresh_access_token(settings.SPOTIFY_REFRESH_TOKEN)
        _token_cache["access_token"] = token_data["access_token"]
        _token_cache["expires_at"] = now + token_data.get("expires_in", 3600)
        return _token_cache["access_token"]


async def get_current_user(access_token: str) -> dict:
    cached = _get_cache("me")
    if cached:
        return cached

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        _handle_spotify_error(resp)
        data = resp.json()

    _set_cache("me", data, _CACHE_TTL["me"])
    return data


async def _fetch_current_playing(access_token: str) -> dict | None:
    """直接请求 Spotify，不走缓存"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me/player/currently-playing",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code == 204:
            return None
        _handle_spotify_error(resp)
        return resp.json()


async def get_current_playing(access_token: str) -> dict | None:
    """实时获取当前播放，不缓存"""
    return await _fetch_current_playing(access_token)


async def get_current_playing_cached(access_token: str) -> dict | None:
    """带缓存的播放信息，供 dashboard 聚合接口使用"""
    cached = _get_cache("playing")
    if cached is not None:
        return cached

    data = await _fetch_current_playing(access_token)
    _set_cache("playing", data if data is not None else {}, _CACHE_TTL["playing"])
    return data


async def get_top_tracks(access_token: str, time_range: str = "medium_term", limit: int = 20) -> dict:
    cache_key = f"top_tracks:{time_range}:{limit}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me/top/tracks",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"time_range": time_range, "limit": limit},
        )
        _handle_spotify_error(resp)
        data = resp.json()

    _set_cache(cache_key, data, _CACHE_TTL["top_tracks"])
    return data


async def get_recently_played(access_token: str, limit: int = 20) -> dict:
    cache_key = f"recently_played:{limit}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me/player/recently-played",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": limit},
        )
        _handle_spotify_error(resp)
        data = resp.json()

    _set_cache(cache_key, data, _CACHE_TTL["recently_played"])
    return data
