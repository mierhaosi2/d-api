from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.services import weather as weather_svc

router = APIRouter()


class WeatherResponse(BaseModel):
    mood: str
    is_day: bool
    temperature_c: float
    weather_code: int
    updated_at: str


@router.get("", response_model=WeatherResponse, summary="获取当前天气与心情")
async def get_weather():
    """
    从 Open-Meteo 拉取当前天气，服务端缓存 15 分钟。

    - **mood**: clear | cloud | rain | snow | fog
    - **is_day**: 是否白天
    - **temperature_c**: 气温（摄氏度）
    - **weather_code**: WMO 天气代码
    - **updated_at**: 数据时间戳（UTC ISO 8601）
    """
    try:
        data = await weather_svc.get_weather()
    except Exception as exc:
        logger.exception("获取天气失败: {}", exc)
        raise HTTPException(status_code=502, detail=f"天气服务暂时不可用: {exc}")
    return data
