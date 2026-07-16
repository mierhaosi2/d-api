import httpx

LRCLIB_API = "https://lrclib.net/api"


async def get_lyrics(
    track_name: str,
    artist_name: str,
    album_name: str = "",
    duration_ms: int = 0,
) -> dict | None:
    """
    从 LRCLIB 获取歌词。
    返回 dict 包含 plainLyrics（纯文本）和 syncedLyrics（LRC 时间轴格式），
    找不到返回 None。
    """
    params = {
        "track_name": track_name,
        "artist_name": artist_name,
    }
    if album_name:
        params["album_name"] = album_name
    if duration_ms:
        params["duration"] = duration_ms // 1000  # LRCLIB 用秒

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{LRCLIB_API}/get", params=params, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

    return {
        "track_name": data.get("trackName"),
        "artist_name": data.get("artistName"),
        "album_name": data.get("albumName"),
        "duration": data.get("duration"),
        "has_synced": bool(data.get("syncedLyrics")),
        "plain_lyrics": data.get("plainLyrics"),
        "synced_lyrics": data.get("syncedLyrics"),  # LRC 格式，含时间轴
    }


async def search_lyrics(query: str, limit: int = 5) -> list:
    """按关键词搜索歌词"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{LRCLIB_API}/search",
            params={"q": query},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()

    return [
        {
            "id": item.get("id"),
            "track_name": item.get("trackName"),
            "artist_name": item.get("artistName"),
            "album_name": item.get("albumName"),
            "duration": item.get("duration"),
            "has_synced": bool(item.get("syncedLyrics")),
        }
        for item in results[:limit]
    ]
