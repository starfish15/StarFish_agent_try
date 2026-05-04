import requests
from tools.base import BaseTool

class WeatherTool(BaseTool):
    @property
    def name(self):
        return "get_weather"

    @property
    def description(self):
        return "查询指定城市的当日天气，参数: city (城市英文名/拼音)"

    def run(self, city: str) -> dict:
        url = f"https://wttr.in/{city}?format=j1"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {"error": f"无法获取 {city} 天气"}
        data = resp.json()
        current = data["current_condition"][0]
        return {
            "city": city,
            "weather": current["weatherDesc"][0]["value"],
            "temperature": f"{current['temp_C']}°C",
            "feels_like": f"{current['FeelsLikeC']}°C",
            "humidity": f"{current['humidity']}%",
            "wind_speed": f"{current['windspeedKmph']} km/h"
        }