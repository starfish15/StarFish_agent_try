from datetime import datetime

import requests
from tools.base import BaseTool

class WeatherTool(BaseTool):
    @property
    def name(self):
        return "get_weather"

    @property
    def description(self):
        return (
            "查询指定城市天气。参数: city (城市英文名/拼音), "
            "day_offset (可选: 0=今天, 1=明天), days (可选: 1-3)."
        )

    def run(self, city: str, day_offset: int | None = None, days: int | None = None) -> dict:
        if not isinstance(city, str) or not city.strip():
            return {"error": "city 不能为空"}
        url = f"https://wttr.in/{city}?format=j1"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {"error": f"无法获取 {city} 天气"}
        data = resp.json()
        if days is not None:
            try:
                days_int = _coerce_int(days)
            except ValueError as exc:
                return {"error": f"days 无效: {exc}"}
            if days_int <= 0:
                return {"error": "days 必须大于 0"}
            return _build_multi_day_forecast(city, data, days_int)

        if day_offset is not None:
            try:
                offset = _coerce_int(day_offset)
            except ValueError as exc:
                return {"error": f"day_offset 无效: {exc}"}
            return _build_forecast_day(city, data, offset)

        current = data.get("current_condition", [{}])[0]
        today = data.get("weather", [{}])[0]
        summary = _build_day_summary(today)
        return {
            "city": city,
            "weather": _safe_desc(current.get("weatherDesc")),
            "temperature": _format_temp(current.get("temp_C")),
            "feels_like": _format_temp(current.get("FeelsLikeC")),
            "humidity": _format_percent(current.get("humidity")),
            "wind_speed": _format_wind(current.get("windspeedKmph")),
            "temperature_range": summary.get("temperature_range"),
            "temperature_fluctuation": summary.get("temperature_fluctuation"),
        }


def _build_multi_day_forecast(city: str, data: dict, days: int) -> dict:
    weather_list = data.get("weather", [])
    if not weather_list:
        return {"error": "没有可用的预报数据"}
    days = min(days, len(weather_list))
    forecast = []
    for idx in range(days):
        forecast.append(_build_day_summary(weather_list[idx]))
    return {"city": city, "forecast": forecast}


def _build_forecast_day(city: str, data: dict, offset: int) -> dict:
    weather_list = data.get("weather", [])
    if not weather_list:
        return {"error": "没有可用的预报数据"}
    if offset < 0 or offset >= len(weather_list):
        return {"error": f"day_offset 超出范围 (0-{len(weather_list) - 1})"}
    summary = _build_day_summary(weather_list[offset])
    summary["city"] = city
    return summary


def _build_day_summary(day: dict) -> dict:
    min_temp = _parse_int(day.get("mintempC"))
    max_temp = _parse_int(day.get("maxtempC"))
    fluctuation = None
    if min_temp is not None and max_temp is not None:
        fluctuation = max_temp - min_temp

    hourly = day.get("hourly", []) if isinstance(day.get("hourly"), list) else []
    humidity_avg = _avg_int([_parse_int(h.get("humidity")) for h in hourly])
    wind_avg = _avg_int([_parse_int(h.get("windspeedKmph")) for h in hourly])
    rain_max = _max_int([_parse_int(h.get("chanceofrain")) for h in hourly])
    weather_desc = _pick_weather_desc(hourly)

    return {
        "date": _format_date(day.get("date")),
        "weather": weather_desc,
        "temperature_min": min_temp,
        "temperature_max": max_temp,
        "temperature_range": _format_range(min_temp, max_temp),
        "temperature_fluctuation": _format_temp(fluctuation),
        "humidity": _format_percent(humidity_avg),
        "wind_speed": _format_wind(wind_avg),
        "chance_of_rain": _format_percent(rain_max),
    }


def _pick_weather_desc(hourly: list[dict]) -> str:
    for hour in hourly:
        time_str = str(hour.get("time", "")).zfill(4)
        if time_str == "1200":
            return _safe_desc(hour.get("weatherDesc"))
    if hourly:
        return _safe_desc(hourly[len(hourly) // 2].get("weatherDesc"))
    return ""


def _safe_desc(raw) -> str:
    if isinstance(raw, list) and raw:
        return str(raw[0].get("value", "")).strip()
    return ""


def _coerce_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        raise ValueError("必须是数字")


def _parse_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _avg_int(values: list[int | None]) -> int | None:
    cleaned = [v for v in values if isinstance(v, int)]
    if not cleaned:
        return None
    return int(round(sum(cleaned) / len(cleaned)))


def _max_int(values: list[int | None]) -> int | None:
    cleaned = [v for v in values if isinstance(v, int)]
    if not cleaned:
        return None
    return max(cleaned)


def _format_temp(value: int | None) -> str | None:
    if value is None:
        return None
    return f"{value}°C"


def _format_range(min_temp: int | None, max_temp: int | None) -> str | None:
    if min_temp is None or max_temp is None:
        return None
    return f"{min_temp}~{max_temp}°C"


def _format_percent(value: int | None) -> str | None:
    if value is None:
        return None
    return f"{value}%"


def _format_wind(value: int | None) -> str | None:
    if value is None:
        return None
    return f"{value} km/h"


def _format_date(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d")
            return f"{parsed.year}/{parsed.month}/{parsed.day}"
        except ValueError:
            return raw
    return str(value)