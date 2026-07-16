from fastapi import APIRouter, HTTPException, Query

from app.services import lyrics as lyrics_svc
from app.services import spotify as spotify_svc

router = APIRouter()


@router.get("/now-playing", summary="获取当前播放歌曲的歌词")
async def lyrics_now_playing(
    synced: bool = Query(True, description="True=返回LRC时间轴歌词，False=返回纯文本"),
):
    """
    自动获取当前 Spotify 正在播放的曲目，并从 LRCLIB 匹配歌词。
    """
    token = await spotify_svc.get_auto_access_token()
    playing = await spotify_svc.get_current_playing(token)

    if not playing or not playing.get("item"):
        return {"playing": False, "lyrics": None}

    item = playing["item"]
    track_name = item["name"]
    artist_name = item["artists"][0]["name"]
    album_name = item["album"]["name"]
    duration_ms = item["duration_ms"]
    progress_ms = playing.get("progress_ms", 0)

    lyrics_data = await lyrics_svc.get_lyrics(
        track_name=track_name,
        artist_name=artist_name,
        album_name=album_name,
        duration_ms=duration_ms,
    )

    if not lyrics_data:
        return {
            "playing": True,
            "track": f"{artist_name} - {track_name}",
            "lyrics": None,
            "message": "未找到歌词",
        }

    return {
        "playing": True,
        "track": f"{artist_name} - {track_name}",
        "album": album_name,
        "progress_ms": progress_ms,
        "has_synced": lyrics_data["has_synced"],
        "lyrics": lyrics_data["synced_lyrics"] if synced and lyrics_data["has_synced"] else lyrics_data["plain_lyrics"],
    }


@router.get("/search", summary="搜索歌词")
async def lyrics_search(
    q: str = Query(..., description="歌名 / 歌手名等关键词"),
    limit: int = Query(5, ge=1, le=20),
):
    results = await lyrics_svc.search_lyrics(q, limit)
    if not results:
        raise HTTPException(status_code=404, detail="未找到匹配歌词")
    return results


@router.get("/track", summary="按歌名/歌手名获取歌词")
async def lyrics_by_track(
    track: str = Query(..., description="歌曲名"),
    artist: str = Query(..., description="歌手名"),
    album: str = Query("", description="专辑名（可选，提高匹配精度）"),
    synced: bool = Query(True, description="True=LRC时间轴，False=纯文本"),
):
    data = await lyrics_svc.get_lyrics(track, artist, album)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到「{artist} - {track}」的歌词")

    return {
        "track": f"{data['artist_name']} - {data['track_name']}",
        "album": data["album_name"],
        "has_synced": data["has_synced"],
        "lyrics": data["synced_lyrics"] if synced and data["has_synced"] else data["plain_lyrics"],
    }
