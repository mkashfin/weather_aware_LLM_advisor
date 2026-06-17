"""Calendar loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Location:
    name: str
    latitude: float
    longitude: float


@dataclass
class Event:
    title: str
    start: datetime
    end: datetime
    activity: str
    location: Location


class CalendarError(Exception):
    """Raised when calendar data is invalid or missing."""


def _validate_coordinate(value: Any, name: str, low: float, high: float) -> float:
    if not isinstance(value, (int, float)):
        raise CalendarError(f"Invalid {name}: must be a number.")
    if not low <= value <= high:
        raise CalendarError(f"Invalid {name}: must be between {low} and {high}.")
    return float(value)


def _parse_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise CalendarError(f"Invalid {field}: must be an ISO datetime string.")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise CalendarError(f"Invalid {field}: '{value}' is not a valid ISO datetime.") from exc


def _parse_event(raw: Any, index: int) -> Event:
    if not isinstance(raw, dict):
        raise CalendarError(f"Event at index {index} must be an object.")

    required = ("title", "start", "end", "activity", "location")
    for field in required:
        if field not in raw:
            raise CalendarError(f"Event at index {index} is missing required field '{field}'.")

    location_raw = raw["location"]
    if not isinstance(location_raw, dict):
        raise CalendarError(f"Event at index {index} has invalid location: must be an object.")

    for loc_field in ("name", "latitude", "longitude"):
        if loc_field not in location_raw:
            raise CalendarError(
                f"Event at index {index} location is missing required field '{loc_field}'."
            )

    start = _parse_datetime(raw["start"], "start")
    end = _parse_datetime(raw["end"], "end")
    if end < start:
        raise CalendarError(f"Event at index {index} has end time before start time.")

    return Event(
        title=str(raw["title"]),
        start=start,
        end=end,
        activity=str(raw["activity"]),
        location=Location(
            name=str(location_raw["name"]),
            latitude=_validate_coordinate(location_raw["latitude"], "latitude", -90, 90),
            longitude=_validate_coordinate(location_raw["longitude"], "longitude", -180, 180),
        ),
    )


def load_calendar(path: str | Path) -> list[Event]:
    """Load and validate events from a calendar JSON file."""
    calendar_path = Path(path)
    if not calendar_path.exists():
        raise CalendarError(f"Calendar file not found: {calendar_path}")

    try:
        raw_text = calendar_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CalendarError(f"Unable to read calendar file: {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CalendarError(f"Malformed JSON in calendar file: {exc.msg}") from exc

    if not isinstance(data, list):
        raise CalendarError("Calendar file must contain a JSON array of events.")

    if not data:
        raise CalendarError("Calendar file contains no events.")

    return [_parse_event(item, index) for index, item in enumerate(data)]
