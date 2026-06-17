"""Tests for advice prompt construction and generation."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from assistant.advice import (
    AdviceError,
    build_prompt,
    build_rule_hints,
    count_advice_lines,
    generate_advice,
    validate_advice_length,
)
from assistant.calendar import Event, Location
from assistant.weather import WeatherForecast

SAMPLE_EVENT = Event(
    title="Morning Commute",
    start=datetime(2026, 6, 17, 8, 0),
    end=datetime(2026, 6, 17, 9, 0),
    activity="Work",
    location=Location("Downtown Houston", 29.7604, -95.3698),
)

RAIN_FORECAST = WeatherForecast(
    temperature_c=22.0,
    temperature_f=71.6,
    precipitation_probability=60,
    condition="Moderate rain",
    forecast_time=datetime(2026, 6, 17, 8, 0),
    deviation_minutes=0,
)

HOT_FORECAST = WeatherForecast(
    temperature_c=35.0,
    temperature_f=95.0,
    precipitation_probability=5,
    condition="Clear sky",
    forecast_time=datetime(2026, 6, 17, 8, 0),
    deviation_minutes=0,
)

MOCK_ADVICE = """Line one about rain during commute.
Line two about public transit.
Line three about umbrella.
Line four about waterproof footwear.
Line five about extra travel time.
Line six about protecting electronics."""


def test_prompt_includes_weather_context() -> None:
    prompt = build_prompt(SAMPLE_EVENT, RAIN_FORECAST)
    assert "Morning Commute" in prompt
    assert "Work" in prompt
    assert "Downtown Houston" in prompt
    assert "71.6" in prompt
    assert "60" in prompt
    assert "Moderate rain" in prompt


def test_prompt_includes_activity() -> None:
    prompt = build_prompt(SAMPLE_EVENT, RAIN_FORECAST)
    assert "Activity: Work" in prompt


def test_rule_hints_for_rain() -> None:
    hints = build_rule_hints(RAIN_FORECAST, "Work")
    assert "umbrella" in hints.lower()
    assert "bus" in hints.lower() or "train" in hints.lower()


def test_rule_hints_for_hot_weather() -> None:
    hints = build_rule_hints(HOT_FORECAST, "Sports")
    assert "hydration" in hints.lower()


def test_prompt_includes_event_context_instruction_when_requested() -> None:
    prompt = build_prompt(SAMPLE_EVENT, RAIN_FORECAST, include_event_in_response=True)
    assert "Your response must begin by stating the activity, location, date, and time" in prompt
    assert "Work" in prompt
    assert "Downtown Houston" in prompt
    assert "2026-06-17" in prompt
    assert "08:00" in prompt


def test_output_length_enforcement() -> None:
    assert validate_advice_length(MOCK_ADVICE) is True
    assert count_advice_lines(MOCK_ADVICE) == 6
    assert validate_advice_length("Too short.") is False


@patch("assistant.advice.requests.post")
def test_generate_advice_success(mock_post: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": MOCK_ADVICE}
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    advice = generate_advice(SAMPLE_EVENT, RAIN_FORECAST)
    assert advice == MOCK_ADVICE
    call_args = mock_post.call_args
    payload = call_args.kwargs.get("json") or call_args[1].get("json")
    assert payload["model"] == "llama3.2"
    assert "Morning Commute" in payload["prompt"]


@patch("assistant.advice.requests.post")
def test_generate_advice_connection_error(mock_post: MagicMock) -> None:
    mock_post.side_effect = requests.ConnectionError("refused")
    with pytest.raises(AdviceError, match="Ollama daemon unavailable"):
        generate_advice(SAMPLE_EVENT, RAIN_FORECAST)


@patch("assistant.advice.requests.post")
def test_generate_advice_empty_response(mock_post: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": ""}
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response
    with pytest.raises(AdviceError, match="empty response"):
        generate_advice(SAMPLE_EVENT, RAIN_FORECAST)
