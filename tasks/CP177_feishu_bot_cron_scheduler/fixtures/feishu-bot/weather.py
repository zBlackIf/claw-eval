"""Feishu Bot - Weather data provider."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WeatherProvider:
    """Fetches weather data for a given city."""

    BASE_URL = "https://api.weatherapi.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_current(self, city: str) -> dict[str, Any]:
        """Get current weather for a city."""
        resp = httpx.get(
            f"{self.BASE_URL}/current.json",
            params={"key": self.api_key, "q": city, "lang": "zh"},
        )
        return resp.json()

    def get_forecast(self, city: str, days: int = 1) -> dict[str, Any]:
        """Get weather forecast for a city."""
        resp = httpx.get(
            f"{self.BASE_URL}/forecast.json",
            params={"key": self.api_key, "q": city, "days": days, "lang": "zh"},
        )
        return resp.json()

    def format_daily_report(self, city: str) -> str:
        """Format a full-day weather report for the city."""
        data = self.get_forecast(city, days=1)
        if "error" in data:
            return f"天气获取失败: {data['error'].get('message', '未知错误')}"

        forecast_day = data.get("forecast", {}).get("forecastday", [{}])[0]
        day_info = forecast_day.get("day", {})

        return (
            f"城市: {city}\n"
            f"日期: {forecast_day.get('date', '未知')}\n"
            f"最高温度: {day_info.get('maxtemp_c', '?')}°C\n"
            f"最低温度: {day_info.get('mintemp_c', '?')}°C\n"
            f"天气状况: {day_info.get('condition', {}).get('text', '未知')}\n"
            f"降雨概率: {day_info.get('daily_chance_of_rain', '?')}%\n"
            f"风速: {day_info.get('maxwind_kph', '?')} km/h"
        )
