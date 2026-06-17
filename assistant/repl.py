"""CLI REPL for the weather-aware personal assistant."""

from __future__ import annotations

import sys
from typing import Callable, TextIO

from assistant.advice import AdviceError, generate_advice
from assistant.calendar import Event
from assistant.weather import WeatherError, fetch_weather

PROMPT = "assistant> "
UNKNOWN_COMMAND = "Unknown command. Type 'help' for available commands."
WEATHER_ERROR = "Unable to retrieve weather information for this event."
ADVICE_ERROR = "Unable to generate advice at this time."


def format_help() -> str:
    return """Available commands:
  help            Show this help message
  list            List upcoming events
  advise          Generate advice for all events
  advise <index>  Generate advice for a single event
  exit            Exit the application"""


def format_event_context(event: Event) -> str:
    """Format activity, date, time, and location for an event."""
    date_str = event.start.strftime("%Y-%m-%d")
    time_str = event.start.strftime("%H:%M")
    return (
        f"Activity: {event.activity}\n"
        f"Date: {date_str}\n"
        f"Time: {time_str}\n"
        f"Location: {event.location.name}"
    )


def format_event_list(events: list[Event]) -> str:
    blocks: list[str] = []
    for index, event in enumerate(events, start=1):
        date_str = event.start.strftime("%Y-%m-%d")
        time_str = event.start.strftime("%H:%M")
        blocks.append(
            f"{index}. {event.title}\n"
            f"   Activity: {event.activity}\n"
            f"   Date: {date_str}\n"
            f"   Time: {time_str}\n"
            f"   Location: {event.location.name}"
        )
    return "\n".join(blocks)


def _process_advice_for_event(
    event: Event,
    index: int,
    weather_fetcher: Callable[[Event], object],
    advice_generator: Callable[[Event, object], str],
    output: TextIO,
    *,
    include_event_context: bool = False,
) -> None:
    output.write(f"\n--- Advice for event {index}: {event.title} ---\n")
    if include_event_context:
        output.write(f"{format_event_context(event)}\n\n")
    try:
        forecast = weather_fetcher(event)
    except WeatherError as exc:
        output.write(f"Error: {exc}\n")
        output.write(f"{WEATHER_ERROR}\n")
        output.write("Advice generation skipped.\n")
        return

    try:
        if include_event_context:
            advice = advice_generator(event, forecast, include_event_in_response=True)
        else:
            advice = advice_generator(event, forecast)
    except AdviceError as exc:
        output.write(f"Error: {exc}\n")
        output.write(f"{ADVICE_ERROR}\n")
        return

    output.write(f"{advice}\n")


def handle_command(
    command_line: str,
    events: list[Event],
    output: TextIO,
    weather_fetcher: Callable[[Event], object] | None = None,
    advice_generator: Callable[[Event, object], str] | None = None,
) -> bool:
    """
    Process a single REPL command.

    Returns False if the REPL should exit, True otherwise.
    """
    weather_fetcher = weather_fetcher or fetch_weather
    advice_generator = advice_generator or generate_advice

    parts = command_line.strip().split()
    if not parts:
        return True

    command = parts[0].lower()

    if command == "help":
        output.write(format_help() + "\n")
        return True

    if command == "list":
        output.write(format_event_list(events) + "\n")
        return True

    if command == "exit":
        return False

    if command == "advise":
        if len(parts) == 1:
            for index, event in enumerate(events, start=1):
                _process_advice_for_event(
                    event, index, weather_fetcher, advice_generator, output
                )
            return True

        if len(parts) == 2:
            try:
                event_index = int(parts[1])
            except ValueError:
                output.write(UNKNOWN_COMMAND + "\n")
                return True

            if event_index < 1 or event_index > len(events):
                output.write(f"Invalid event index. Choose 1–{len(events)}.\n")
                return True

            _process_advice_for_event(
                events[event_index - 1],
                event_index,
                weather_fetcher,
                advice_generator,
                output,
                include_event_context=True,
            )
            return True

    output.write(UNKNOWN_COMMAND + "\n")
    return True


def run_repl(
    events: list[Event],
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    weather_fetcher: Callable[[Event], object] | None = None,
    advice_generator: Callable[[Event, object], str] | None = None,
) -> None:
    """Run the interactive REPL loop."""
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout

    output_stream.write(format_help() + "\n\n")

    while True:
        try:
            output_stream.write(PROMPT)
            output_stream.flush()
            line = input_stream.readline()
            if line == "":
                break
        except EOFError:
            break

        if not handle_command(
            line, events, output_stream, weather_fetcher, advice_generator
        ):
            break
