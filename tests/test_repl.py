"""Tests for the CLI REPL."""

from __future__ import annotations

from datetime import datetime
from io import StringIO

from assistant.calendar import Event, Location
from assistant.repl import (
    UNKNOWN_COMMAND,
    format_event_list,
    format_help,
    handle_command,
    run_repl,
)
from assistant.weather import WeatherForecast

SAMPLE_EVENTS = [
    Event(
        title="Morning Commute",
        start=datetime(2026, 6, 17, 8, 0),
        end=datetime(2026, 6, 17, 9, 0),
        activity="Work",
        location=Location("Downtown Houston", 29.7604, -95.3698),
    ),
    Event(
        title="Evening Tennis",
        start=datetime(2026, 6, 17, 18, 0),
        end=datetime(2026, 6, 17, 20, 0),
        activity="Sports",
        location=Location("Memorial Park", 29.7674, -95.4410),
    ),
]

MOCK_FORECAST = WeatherForecast(
    temperature_c=24.0,
    temperature_f=75.2,
    precipitation_probability=20,
    condition="Partly cloudy",
    forecast_time=datetime(2026, 6, 17, 8, 0),
    deviation_minutes=0,
)

MOCK_ADVICE = (
    "Line one.\nLine two.\nLine three.\nLine four.\nLine five."
)


def mock_weather_fetcher(event: Event) -> WeatherForecast:
    return MOCK_FORECAST


def mock_advice_generator(event: Event, forecast: WeatherForecast, **kwargs: object) -> str:
    return MOCK_ADVICE


def test_help_command() -> None:
    output = StringIO()
    assert handle_command("help", SAMPLE_EVENTS, output) is True
    result = output.getvalue()
    assert "help" in result
    assert "list" in result
    assert "advise" in result
    assert "exit" in result


def test_list_command() -> None:
    output = StringIO()
    handle_command("list", SAMPLE_EVENTS, output)
    result = output.getvalue()
    assert "1. Morning Commute" in result
    assert "Activity: Work" in result
    assert "Date: 2026-06-17" in result
    assert "Time: 08:00" in result
    assert "Location: Downtown Houston" in result
    assert "2. Evening Tennis" in result
    assert "Activity: Sports" in result
    assert "Location: Memorial Park" in result


def test_advise_all_command() -> None:
    output = StringIO()
    handle_command(
        "advise",
        SAMPLE_EVENTS,
        output,
        weather_fetcher=mock_weather_fetcher,
        advice_generator=mock_advice_generator,
    )
    result = output.getvalue()
    assert "Morning Commute" in result
    assert "Evening Tennis" in result
    assert "Line one." in result


def test_advise_index_command() -> None:
    output = StringIO()
    handle_command(
        "advise 2",
        SAMPLE_EVENTS,
        output,
        weather_fetcher=mock_weather_fetcher,
        advice_generator=mock_advice_generator,
    )
    result = output.getvalue()
    assert "Evening Tennis" in result
    assert "Activity: Sports" in result
    assert "Date: 2026-06-17" in result
    assert "Time: 18:00" in result
    assert "Location: Memorial Park" in result
    assert "Morning Commute" not in result


def test_advise_invalid_index() -> None:
    output = StringIO()
    handle_command("advise 99", SAMPLE_EVENTS, output)
    assert "Invalid event index" in output.getvalue()


def test_exit_command() -> None:
    output = StringIO()
    assert handle_command("exit", SAMPLE_EVENTS, output) is False


def test_unknown_command() -> None:
    output = StringIO()
    handle_command("foo", SAMPLE_EVENTS, output)
    assert output.getvalue().strip() == UNKNOWN_COMMAND


def test_format_helpers() -> None:
    listing = format_event_list(SAMPLE_EVENTS)
    assert "Morning Commute" in listing
    assert "Activity: Work" in listing
    assert "Location: Downtown Houston" in listing
    assert "advise" in format_help()


def test_run_repl_shows_help_on_startup() -> None:
    input_stream = StringIO("exit\n")
    output_stream = StringIO()
    run_repl(SAMPLE_EVENTS, input_stream=input_stream, output_stream=output_stream)
    result = output_stream.getvalue()
    assert "Available commands:" in result
    assert "help" in result
    assert "list" in result


def test_run_repl_exits_on_exit_command() -> None:
    input_stream = StringIO("list\nexit\n")
    output_stream = StringIO()
    run_repl(SAMPLE_EVENTS, input_stream=input_stream, output_stream=output_stream)
    result = output_stream.getvalue()
    assert "assistant>" in result
    assert "Morning Commute" in result
