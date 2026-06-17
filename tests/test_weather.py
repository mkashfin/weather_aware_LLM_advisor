"""Tests for weather retrieval and forecast selection."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from assistant.calendar import Event, Location
from assistant.weather import (
    WeatherError,
    celsius_to_fahrenheit,
    fetch_weather,
    parse_forecast_response,
    select_nearest_forecast,
    weather_code_to_condition,
)

SAMPLE_EVENT = Event(
    title="Morning Commute",
    start=datetime(2026, 6, 17, 8, 15),
    end=datetime(2026, 6, 17, 9, 0),
    activity="Work",
    location=Location("Downtown Houston", 29.7604, -95.3698),
)

SAMPLE_API_RESPONSE = {
    "hourly": {
        "time": [
            "2026-06-17T07:00:00",
            "2026-06-17T08:00:00",
            "2026-06-17T09:00:00",
        ],
        "temperature_2m": [22.0, 24.0, 26.0],
        "precipitation_probability": [10, 55, 30],
        "weather_code": [1, 63, 2],
        "wind_speed_10m": [8.0, 12.5, 10.0],
        "relative_humidity_2m": [70, 85, 75],
        "precipitation": [0.0, 1.2, 0.3],
    }
}


def test_celsius_to_fahrenheit() -> None:
    assert celsius_to_fahrenheit(0) == 32.0
    assert celsius_to_fahrenheit(100) == 212.0


def test_weather_code_mapping() -> None:
    assert weather_code_to_condition(0) == "Clear sky"
    assert weather_code_to_condition(63) == "Moderate rain"


def test_nearest_forecast_selection() -> None:
    times = [datetime(2026, 6, 17, 8, 0), datetime(2026, 6, 17, 9, 0)]
    forecast = select_nearest_forecast(
        SAMPLE_EVENT.start,
        times,
        [24.0, 26.0],
        [55, 30],
        [63, 2],
        [12.5, 10.0],
        [85, 75],
        [1.2, 0.3],
    )
    assert forecast.forecast_time == datetime(2026, 6, 17, 8, 0)
    assert forecast.temperature_c == 24.0
    assert forecast.precipitation_probability == 55
    assert forecast.wind_speed_kmh == 12.5
    assert forecast.humidity_percent == 85
    assert forecast.precipitation_mm == 1.2
    assert forecast.condition == "Moderate rain"
    assert forecast.deviation_minutes == 15
    assert forecast.used_fallback is False


def test_forecast_outside_deviation_uses_fallback() -> None:
    times = [datetime(2026, 6, 17, 6, 0), datetime(2026, 6, 17, 10, 0)]
    forecast = select_nearest_forecast(
        SAMPLE_EVENT.start,
        times,
        [20.0, 28.0],
        [5, 10],
        [1, 1],
        [6.0, 8.0],
        [60, 65],
        [0.0, 0.0],
    )
    assert forecast.used_fallback is True
    assert "No forecast within" in forecast.fallback_note


def test_parse_forecast_response() -> None:
    forecast = parse_forecast_response(SAMPLE_API_RESPONSE, SAMPLE_EVENT)
    assert forecast.forecast_time == datetime(2026, 6, 17, 8, 0)
    assert forecast.temperature_f == pytest.approx(celsius_to_fahrenheit(24.0))


def test_missing_hourly_values_raises() -> None:
    with pytest.raises(WeatherError, match="missing hourly data"):
        parse_forecast_response({}, SAMPLE_EVENT)

    with pytest.raises(WeatherError, match="No hourly forecast times"):
        parse_forecast_response(
            {
                "hourly": {
                    "time": [],
                    "temperature_2m": [],
                    "precipitation_probability": [],
                    "weather_code": [],
                    "wind_speed_10m": [],
                    "relative_humidity_2m": [],
                    "precipitation": [],
                }
            },
            SAMPLE_EVENT,
        )


@patch("assistant.weather.requests.get")
def test_fetch_weather_success(mock_get: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_API_RESPONSE
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    forecast = fetch_weather(SAMPLE_EVENT)
    assert forecast.condition == "Moderate rain"
    mock_get.assert_called_once()


@patch("assistant.weather.requests.get")
def test_fetch_weather_http_error(mock_get: MagicMock) -> None:
    mock_get.side_effect = requests.RequestException("Connection failed")
    with pytest.raises(WeatherError, match="HTTP error"):
        fetch_weather(SAMPLE_EVENT)


@patch("assistant.weather.requests.get")
def test_fetch_weather_timeout(mock_get: MagicMock) -> None:
    mock_get.side_effect = requests.Timeout("timed out")
    with pytest.raises(WeatherError, match="API timeout"):
        fetch_weather(SAMPLE_EVENT)
