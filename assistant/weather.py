"""Open-Meteo weather retrieval and forecast selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from assistant.calendar import Event

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
MAX_DEVIATION_MINUTES = 60
REQUEST_TIMEOUT = 10

WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherError(Exception):
    """Raised when weather data cannot be retrieved or parsed."""


@dataclass
class WeatherForecast:
    temperature_c: float
    temperature_f: float
    precipitation_probability: float
    precipitation_mm: float
    wind_speed_kmh: float
    humidity_percent: float
    condition: str
    forecast_time: datetime
    deviation_minutes: int
    used_fallback: bool = False
    fallback_note: str = ""


def celsius_to_fahrenheit(celsius: float) -> float:
    return celsius * 9 / 5 + 32


def weather_code_to_condition(code: int) -> str:
    return WMO_CODES.get(code, f"Unknown conditions (code {code})")


def _parse_api_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def select_nearest_forecast(
    event_start: datetime,
    times: list[datetime],
    temperatures: list[float],
    precipitation_probs: list[float],
    weather_codes: list[int],
    wind_speeds: list[float],
    humidities: list[float],
    precipitation_mm: list[float],
) -> WeatherForecast:
    """Select the hourly forecast nearest to the event start time."""
    if not times:
        raise WeatherError("No hourly forecast times available.")

    paired = list(
        zip(
            times,
            temperatures,
            precipitation_probs,
            weather_codes,
            wind_speeds,
            humidities,
            precipitation_mm,
            strict=True,
        )
    )
    (
        best_time,
        best_temp,
        best_precip,
        best_code,
        best_wind,
        best_humidity,
        best_precip_mm,
    ) = min(paired, key=lambda item: abs((item[0] - event_start).total_seconds()))
    deviation = int(abs((best_time - event_start).total_seconds()) // 60)
    used_fallback = deviation > MAX_DEVIATION_MINUTES

    fallback_note = ""
    if used_fallback:
        fallback_note = (
            f"Note: No forecast within ±{MAX_DEVIATION_MINUTES} minutes of event start. "
            f"Using forecast for {best_time.strftime('%Y-%m-%d %H:%M')} "
            f"({deviation} minutes from event start)."
        )

    return WeatherForecast(
        temperature_c=best_temp,
        temperature_f=celsius_to_fahrenheit(best_temp),
        precipitation_probability=best_precip,
        precipitation_mm=best_precip_mm,
        wind_speed_kmh=best_wind,
        humidity_percent=best_humidity,
        condition=weather_code_to_condition(int(best_code)),
        forecast_time=best_time,
        deviation_minutes=deviation,
        used_fallback=used_fallback,
        fallback_note=fallback_note,
    )


def parse_forecast_response(data: dict[str, Any], event: Event) -> WeatherForecast:
    """Parse an Open-Meteo API response for a given event."""
    hourly = data.get("hourly")
    if not isinstance(hourly, dict):
        raise WeatherError("Unexpected API response: missing hourly data.")

    time_values = hourly.get("time")
    temperatures = hourly.get("temperature_2m")
    precipitation = hourly.get("precipitation_probability")
    weather_codes = hourly.get("weather_code")
    wind_speeds = hourly.get("wind_speed_10m")
    humidities = hourly.get("relative_humidity_2m")
    precipitation_mm = hourly.get("precipitation")

    required_arrays = (
        time_values,
        temperatures,
        precipitation,
        weather_codes,
        wind_speeds,
        humidities,
        precipitation_mm,
    )
    if not all(isinstance(values, list) for values in required_arrays):
        raise WeatherError("Unexpected API response: hourly arrays missing or invalid.")

    if not time_values:
        raise WeatherError("No hourly forecast times in API response.")

    times = [_parse_api_time(value) for value in time_values]
    return select_nearest_forecast(
        event.start,
        times,
        temperatures,
        precipitation,
        weather_codes,
        wind_speeds,
        humidities,
        precipitation_mm,
    )


def fetch_weather(event: Event, session: requests.Session | None = None) -> WeatherForecast:
    """Fetch weather forecast for an event from Open-Meteo."""
    http = session or requests
    params = {
        "latitude": event.location.latitude,
        "longitude": event.location.longitude,
        "hourly": (
            "temperature_2m,precipitation_probability,weather_code,"
            "wind_speed_10m,relative_humidity_2m,precipitation"
        ),
        "timezone": "auto",
    }

    try:
        response = http.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.Timeout as exc:
        raise WeatherError(f"API timeout: {exc}") from exc
    except requests.RequestException as exc:
        raise WeatherError(f"HTTP error: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise WeatherError(f"Invalid JSON response: {exc}") from exc

    return parse_forecast_response(data, event)
