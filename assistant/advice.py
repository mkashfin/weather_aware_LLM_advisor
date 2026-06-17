"""Advice prompt construction and Ollama integration."""

from __future__ import annotations

from typing import Any

import requests

from assistant.calendar import Event
from assistant.weather import WeatherForecast

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
REQUEST_TIMEOUT = 60

PROMPT_TEMPLATE = """You are a practical personal planning assistant.

Event:
Title: {title}
Activity: {activity}
Location: {location}
Time: {time}

Weather:
Temperature: {temperature}°F
Precipitation Probability: {precipitation}%
Condition: {condition}

{rule_hints}
{fallback_note}

Provide a 5–7 line recommendation that:
- suggests transportation options,
- advises what to bring,
- considers comfort and safety,
- adapts to the activity,
- avoids unnecessary verbosity.
"""


class AdviceError(Exception):
    """Raised when advice cannot be generated."""


def build_rule_hints(forecast: WeatherForecast, activity: str) -> str:
    """Deterministic rule-based hints before LLM invocation."""
    hints: list[str] = []
    temp_c = forecast.temperature_c
    precip = forecast.precipitation_probability
    condition_lower = forecast.condition.lower()
    activity_lower = activity.lower()

    is_rain = precip >= 50 or "rain" in condition_lower or "drizzle" in condition_lower
    is_storm = "thunder" in condition_lower or "hail" in condition_lower or precip >= 80
    is_heavy_rain = "heavy" in condition_lower or precip >= 70

    if is_storm or is_heavy_rain:
        hints.append(
            "Safety priority: emphasize extra travel time, indoor waiting options, "
            "and avoid walking long distances or outdoor exposure without caution."
        )
        hints.append(
            "Transportation: prefer bus, train, driving, or ride-share. "
            "Carry an umbrella and waterproof footwear."
        )
    elif is_rain:
        hints.append(
            "Transportation: prefer bus, train, driving, or ride-share over cycling or long walks."
        )
        hints.append("Preparation: carry an umbrella and wear waterproof footwear.")
    elif temp_c > 30:
        hints.append(
            "Hot weather: recommend hydration, lightweight clothing, and sun protection. "
            "Avoid extended outdoor exposure."
        )
    elif temp_c < 5:
        hints.append(
            "Cold weather: recommend layered clothing, gloves, and warm transportation options."
        )
    else:
        hints.append(
            "Moderate conditions: walking and cycling are reasonable when suitable for the activity."
        )

    if activity_lower == "work":
        hints.append("Activity focus: prioritize reliability, timeliness, and professional appearance.")
    elif activity_lower == "sports":
        hints.append("Activity focus: prioritize comfort, hydration, and appropriate gear.")
    elif activity_lower == "social":
        hints.append("Activity focus: prioritize convenience and flexibility.")
    elif activity_lower == "travel":
        hints.append("Activity focus: prioritize buffer time and luggage considerations.")
    elif "outdoor" in activity_lower:
        hints.append("Activity focus: prioritize weather preparedness and contingency planning.")

    return "Rule-based guidance:\n" + "\n".join(f"- {hint}" for hint in hints)


def build_prompt(
    event: Event,
    forecast: WeatherForecast,
    *,
    include_event_in_response: bool = False,
) -> str:
    """Build the LLM prompt from event and weather data."""
    date_str = event.start.strftime("%Y-%m-%d")
    time_str = event.start.strftime("%H:%M")
    rule_hints = build_rule_hints(forecast, event.activity)
    fallback_note = forecast.fallback_note

    prompt = PROMPT_TEMPLATE.format(
        title=event.title,
        activity=event.activity,
        location=event.location.name,
        time=f"{date_str} {time_str}",
        temperature=f"{forecast.temperature_f:.1f}",
        precipitation=f"{forecast.precipitation_probability:.0f}",
        condition=forecast.condition,
        rule_hints=rule_hints,
        fallback_note=fallback_note,
    )

    if include_event_in_response:
        prompt += (
            "\nYour response must begin by stating the activity, location, date, and time "
            f"({event.activity}, {event.location.name}, {date_str}, {time_str}), "
            "then provide your 5–7 line recommendation."
        )

    return prompt


def count_advice_lines(text: str) -> int:
    """Count non-empty lines in advice output."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return len(lines)


def validate_advice_length(text: str, min_lines: int = 5, max_lines: int = 7) -> bool:
    """Check whether advice meets the 5–7 line requirement."""
    count = count_advice_lines(text)
    return min_lines <= count <= max_lines


def generate_advice(
    event: Event,
    forecast: WeatherForecast,
    session: requests.Session | None = None,
    *,
    include_event_in_response: bool = False,
) -> str:
    """Generate advice using Ollama."""
    prompt = build_prompt(event, forecast, include_event_in_response=include_event_in_response)
    http = session or requests

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = http.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.ConnectionError as exc:
        raise AdviceError(f"Ollama daemon unavailable: {exc}") from exc
    except requests.Timeout as exc:
        raise AdviceError(f"Ollama request timed out: {exc}") from exc
    except requests.RequestException as exc:
        raise AdviceError(f"Ollama HTTP error: {exc}") from exc

    try:
        data: dict[str, Any] = response.json()
    except ValueError as exc:
        raise AdviceError(f"Invalid Ollama response: {exc}") from exc

    advice = data.get("response", "").strip()
    if not advice:
        raise AdviceError("Ollama returned an empty response.")

    if "error" in data:
        raise AdviceError(f"Ollama error: {data['error']}")

    return advice
