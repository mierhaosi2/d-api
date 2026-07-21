from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.services import spotify as spotify_svc

router = APIRouter()


# ── 自动 token 接口（无需手动传 access_token）──────────────────────────────

@router.get("/auto/dashboard", summary="聚合接口：一次返回所有首页数据（推荐前端使用）")
async def auto_dashboard(
    top_limit: int = Query(20, ge=1, le=50, description="Top Tracks 数量"),
    top_range: str = Query("medium_term", description="short_term / medium_term / long_term"),
    recent_limit: int = Query(6, ge=1, le=50, description="最近播放数量"),
):
    """
    按顺序请求 Spotify，避免并发触发限流。
    返回 me / playing / top_tracks / recently_played 全部数据。
    """
    token = await spotify_svc.get_auto_access_token()

    me = await spotify_svc.get_current_user(token)
    playing = await spotify_svc.get_current_playing_cached(token)
    top_tracks = await spotify_svc.get_top_tracks(token, top_range, top_limit)
    recently_played = await spotify_svc.get_recently_played(token, recent_limit)

    return {
        "me": me,
        "playing": playing or {"playing": False, "item": None},
        "top_tracks": top_tracks,
        "recently_played": recently_played,
    }


@router.get("/auto/me", summary="自动获取用户信息（用配置的 refresh_token）")
async def auto_me():
    token = await spotify_svc.get_auto_access_token()
    return await spotify_svc.get_current_user(token)


@router.get("/auto/playing", summary="自动获取正在播放")
async def auto_playing():
    token = await spotify_svc.get_auto_access_token()
    data = await spotify_svc.get_current_playing(token)
    if data is None:
        return {"playing": False, "item": None}
    return data


@router.get("/auto/top-tracks", summary="自动获取 Top Tracks")
async def auto_top_tracks(
    time_range: str = Query("medium_term", description="short_term / medium_term / long_term"),
    limit: int = Query(20, ge=1, le=50),
):
    token = await spotify_svc.get_auto_access_token()
    return await spotify_svc.get_top_tracks(token, time_range, limit)


@router.get("/auto/recently-played", summary="自动获取最近播放")
async def auto_recently_played(limit: int = Query(20, ge=1, le=50)):
    token = await spotify_svc.get_auto_access_token()
    return await spotify_svc.get_recently_played(token, limit)


# ── 手动传 token 接口 ──────────────────────────────────────────────────────


@router.get("/login")
async def spotify_login():
    """跳转到 Spotify 授权页面"""
    auth_url = spotify_svc.build_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def spotify_callback(
    code: str = Query(None),
    error: str = Query(None),
    state: str = Query(None),
):
    """Spotify 授权回调，用 code 换取 token"""
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify 授权失败: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="缺少授权码 code")

    token_data = await spotify_svc.exchange_code_for_token(code)

    # 这里直接返回 token 数据，实际项目中应存入数据库/Session/Redis
    return {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_in": token_data.get("expires_in"),
        "token_type": token_data.get("token_type"),
        "scope": token_data.get("scope"),
    }


@router.get("/refresh")
async def spotify_refresh(refresh_token: str = Query(..., description="Spotify refresh_token")):
    """用 refresh_token 换取新的 access_token"""
    try:
        token_data = await spotify_svc.refresh_access_token(refresh_token)
        return {
            "access_token": token_data.get("access_token"),
            "expires_in": token_data.get("expires_in"),
            "token_type": token_data.get("token_type"),
            "scope": token_data.get("scope"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
async def spotify_me(access_token: str = Query(..., description="Spotify access_token")):
    """获取当前用户信息"""
    try:
        return await spotify_svc.get_current_user(access_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me/playing")
async def spotify_current_playing(access_token: str = Query(..., description="Spotify access_token")):
    """获取当前正在播放的曲目"""
    try:
        data = await spotify_svc.get_current_playing(access_token)
        if data is None:
            return {"playing": False, "item": None}
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me/top-tracks")
async def spotify_top_tracks(
    access_token: str = Query(..., description="Spotify access_token"),
    time_range: str = Query("medium_term", description="short_term / medium_term / long_term"),
    limit: int = Query(20, ge=1, le=50),
):
    """获取用户最常听的曲目"""
    try:
        return await spotify_svc.get_top_tracks(access_token, time_range, limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me/recently-played")
async def spotify_recently_played(
    access_token: str = Query(..., description="Spotify access_token"),
    limit: int = Query(20, ge=1, le=50),
):
    """获取最近播放记录"""
    try:
        return await spotify_svc.get_recently_played(access_token, limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
