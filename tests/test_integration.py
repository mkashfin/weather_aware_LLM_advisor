"""End-to-end integration tests with mocked external services."""

from __future__ import annotations

import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from assistant.advice import generate_advice
from assistant.calendar import load_calendar
from assistant.repl import handle_command
from assistant.weather import WeatherForecast, fetch_weather

VALID_EVENT = {
    "title": "Morning Commute",
    "start": "2026-06-17T08:00:00",
    "end": "2026-06-17T09:00:00",
    "activity": "Work",
    "location": {
        "name": "Downtown Houston",
        "latitude": 29.7604,
        "longitude": -95.3698,
    },
}

SAMPLE_API_RESPONSE = {
    "hourly": {
        "time": ["2026-06-17T08:00:00", "2026-06-17T09:00:00"],
        "temperature_2m": [24.0, 26.0],
        "precipitation_probability": [55, 30],
        "weather_code": [63, 2],
    }
}

MOCK_ADVICE = (
    "Expect moderate rain during your commute.\n"
    "Take public transit or drive instead of walking.\n"
    "Bring an umbrella and waterproof footwear.\n"
    "Allow extra travel time for slower roads.\n"
    "Keep electronics protected from moisture.\n"
    "Mild temperatures mean light layers are sufficient."
)


def test_end_to_end_advise_flow(tmp_path: Path) -> None:
    calendar_path = tmp_path / "calendar.json"
    calendar_path.write_text(json.dumps([VALID_EVENT]), encoding="utf-8")

    events = load_calendar(calendar_path)
    assert len(events) == 1

    mock_forecast = WeatherForecast(
        temperature_c=24.0,
        temperature_f=75.2,
        precipitation_probability=55,
        condition="Moderate rain",
        forecast_time=datetime(2026, 6, 17, 8, 0),
        deviation_minutes=0,
    )

    output = StringIO()

    def mock_weather(event):
        return mock_forecast

    def mock_advice(event, forecast, **kwargs):
        return MOCK_ADVICE

    handle_command(
        "advise 1",
        events,
        output,
        weather_fetcher=mock_weather,
        advice_generator=mock_advice,
    )

    result = output.getvalue()
    assert "Morning Commute" in result
    assert "moderate rain" in result.lower()
    assert "umbrella" in result.lower()


@patch("assistant.weather.requests.get")
@patch("assistant.advice.requests.post")
def test_full_pipeline_with_mocked_services(
    mock_post: MagicMock, mock_get: MagicMock, tmp_path: Path
) -> None:
    calendar_path = tmp_path / "calendar.json"
    calendar_path.write_text(json.dumps([VALID_EVENT]), encoding="utf-8")
    events = load_calendar(calendar_path)

    mock_weather_response = MagicMock()
    mock_weather_response.json.return_value = SAMPLE_API_RESPONSE
    mock_weather_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_weather_response

    mock_advice_response = MagicMock()
    mock_advice_response.json.return_value = {"response": MOCK_ADVICE}
    mock_advice_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_advice_response

    forecast = fetch_weather(events[0])
    assert forecast.condition == "Moderate rain"

    advice = generate_advice(events[0], forecast)
    assert "umbrella" in advice.lower()

    output = StringIO()
    handle_command(
        "advise 1",
        events,
        output,
        weather_fetcher=fetch_weather,
        advice_generator=generate_advice,
    )
    assert "Morning Commute" in output.getvalue()
