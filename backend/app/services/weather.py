"""Weather service — uses open-meteo.com (free, no API key required).

Fetches current weather conditions and evaluates whether conditions are
notable enough to trigger a proactive message to an elder.

WMO Weather interpretation codes (used by open-meteo):
  0        = Clear sky
  1,2,3    = Mainly clear, partly cloudy, overcast
  45,48    = Fog
  51-55    = Drizzle (light to dense)
  61-65    = Rain (slight to heavy)
  71-77    = Snow
  80-82    = Rain showers (slight to violent)
  85,86    = Snow showers
  95       = Thunderstorm
  96,99    = Thunderstorm with hail
"""
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Open-meteo API endpoint
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO code ranges for precipitation
RAIN_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}
DRIZZLE_CODES = {51, 53, 55}
HEAVY_RAIN_CODES = {65, 82, 95, 96, 99}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
FOG_CODES = {45, 48}

# WMO code → Chinese description
WEATHER_DESCRIPTIONS: dict[int, str] = {
    0: "晴天",
    1: "晴间多云",
    2: "多云",
    3: "阴天",
    45: "有雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "较大毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "冰粒",
    80: "阵雨",
    81: "中阵雨",
    82: "强阵雨",
    85: "阵雪",
    86: "强阵雪",
    95: "雷阵雨",
    96: "雷阵雨伴冰雹",
    99: "强雷阵雨伴冰雹",
}


async def get_current_weather(lat: float, lon: float) -> Optional[dict]:
    """Fetch current weather from open-meteo.com.

    Args:
        lat: Latitude (e.g., 31.23 for Shanghai)
        lon: Longitude (e.g., 121.47 for Shanghai)

    Returns:
        Dict with keys:
            temp_c: float — current temperature in Celsius
            feels_like_c: float — apparent temperature in Celsius
            weather_code: int — WMO weather interpretation code
            description_zh: str — Chinese description of conditions
            is_rainy: bool — any precipitation
            is_heavy_rain: bool — heavy rain or thunderstorm
            is_cold: bool — feels_like < 10°C
            is_hot: bool — temp > 33°C
            is_fog: bool — foggy conditions
        Returns None on network error.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "apparent_temperature",
            "weather_code",
        ],
        "timezone": "Asia/Shanghai",
        "forecast_days": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data["current"]
        temp_c = float(current["temperature_2m"])
        feels_like_c = float(current["apparent_temperature"])
        weather_code = int(current["weather_code"])
        description_zh = WEATHER_DESCRIPTIONS.get(weather_code, "未知天气")

        return {
            "temp_c": temp_c,
            "feels_like_c": feels_like_c,
            "weather_code": weather_code,
            "description_zh": description_zh,
            "is_rainy": weather_code in RAIN_CODES,
            "is_heavy_rain": weather_code in HEAVY_RAIN_CODES,
            "is_cold": feels_like_c < 10.0,
            "is_hot": temp_c > 33.0,
            "is_fog": weather_code in FOG_CODES,
        }

    except httpx.TimeoutException:
        logger.warning("Weather API timeout for lat=%s lon=%s", lat, lon)
        return None
    except Exception as e:
        logger.warning("Weather API error: %s", e)
        return None


async def should_trigger_weather(lat: float, lon: float) -> tuple[bool, str]:
    """Evaluate whether current weather is notable enough to trigger a proactive message.

    Trigger conditions (in priority order):
    1. Heavy rain / thunderstorm → "外面下大雨了，记得不要出门"
    2. Any rain → "今天有雨，出门记得带伞"
    3. Very cold (feels_like < 5°C) → "今天特别冷，注意保暖"
    4. Cold (feels_like < 10°C, temp drop) → "今天有点冷，多穿件衣服"
    5. Heat wave (temp > 35°C) → "今天很热，注意防暑"
    6. Fog → "今天有雾，出门注意安全"

    Returns:
        (should_trigger: bool, reason_zh: str)
        reason_zh is empty string if should_trigger is False.
    """
    weather = await get_current_weather(lat, lon)
    if weather is None:
        return False, ""

    temp = weather["temp_c"]
    feels_like = weather["feels_like_c"]
    desc = weather["description_zh"]

    if weather["is_heavy_rain"]:
        return True, f"外面{desc}，今天别出门了，注意安全"

    if weather["is_rainy"]:
        return True, f"今天{desc}，出门记得带伞哦"

    if feels_like < 5.0:
        return True, f"今天气温只有{temp:.0f}度，感觉像{feels_like:.0f}度，特别冷，多穿点衣服"

    if weather["is_cold"]:
        return True, f"今天有些凉，气温{temp:.0f}度，记得多穿件外套"

    if temp > 35.0:
        return True, f"今天高温{temp:.0f}度，注意防暑，多喝水，少出门"

    if weather["is_fog"]:
        return True, f"今天有雾，能见度低，出门注意安全"

    return False, ""
