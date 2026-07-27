"""
天气服务：Open-Meteo 拉取 + 内存 TTL 缓存 + WMO code → mood 映射
"""

import time
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings

# ── WMO Weather Interpretation Code → mood ────────────────────────────────────
# 参考 https://open-meteo.com/en/docs#weathervariables
# Frontend FX moods: clear | cloud | rain | snow | fog
_WMO_MOOD: dict[int, str] = {
    0:  "clear",
    1:  "clear",
    2:  "cloud",
    3:  "cloud",
    45: "fog",
    48: "fog",
    51: "rain",
    53: "rain",
    55: "rain",
    56: "rain",
    57: "rain",
    61: "rain",
    63: "rain",
    65: "rain",
    66: "rain",
    67: "rain",
    71: "snow",
    73: "snow",
    75: "snow",
    77: "snow",
    80: "rain",
    81: "rain",
    82: "rain",
    85: "snow",
    86: "snow",
    95: "rain",
    96: "rain",
    99: "rain",
}

CACHE_TTL_SECONDS = 15 * 60  # 15 分钟
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# ── 简单内存缓存 ───────────────────────────────────────────────────────────────
_cache: dict[str, Any] = {}
_cache_ts: float = 0.0


def _wmo_to_mood(code: int) -> str:
    """WMO 天气代码转 mood 字符串，未知代码返回 'unknown'。"""
    return _WMO_MOOD.get(code, "cloud")


async def get_weather() -> dict:
    """
    返回天气数据，15 分钟内命中缓存直接返回。
    数据结构：
    {
        "mood": str,
        "is_day": bool,
        "temperature_c": float,
        "weather_code": int,
        "updated_at": str,   # ISO 8601 UTC
    }
    """
    global _cache, _cache_ts

    now = time.monotonic()
    if _cache and (now - _cache_ts) < CACHE_TTL_SECONDS:
        logger.debug("天气缓存命中，距下次刷新 {:.0f}s", CACHE_TTL_SECONDS - (now - _cache_ts))
        return _cache

    logger.info("请求 Open-Meteo 天气数据 lat={} lon={}", settings.WEATHER_LAT, settings.WEATHER_LON)

    params = {
        "latitude":           settings.WEATHER_LAT,
        "longitude":          settings.WEATHER_LON,
        "current":            "temperature_2m,weather_code,is_day",
        "temperature_unit":   "celsius",
        "timezone":           "auto",
        "forecast_days":      1,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        raw = resp.json()

    current = raw["current"]
    weather_code: int = int(current["weather_code"])
    is_day: bool = bool(current["is_day"])
    temperature_c: float = float(current["temperature_2m"])

    result = {
        "mood":          _wmo_to_mood(weather_code),
        "is_day":        is_day,
        "temperature_c": temperature_c,
        "weather_code":  weather_code,
        "updated_at":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    _cache = result
    _cache_ts = now
    logger.info("天气已刷新: code={} mood={} temp={}°C", weather_code, result["mood"], temperature_c)

    return result
