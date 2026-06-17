"""Tests for calendar loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant.calendar import CalendarError, load_calendar


def _write_calendar(tmp_path: Path, data: object) -> Path:
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


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


def test_valid_calendar_loads(tmp_path: Path) -> None:
    path = _write_calendar(tmp_path, [VALID_EVENT])
    events = load_calendar(path)
    assert len(events) == 1
    assert events[0].title == "Morning Commute"
    assert events[0].location.latitude == 29.7604


def test_malformed_json_fails(tmp_path: Path) -> None:
    path = tmp_path / "calendar.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(CalendarError, match="Malformed JSON"):
        load_calendar(path)


def test_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(CalendarError, match="not found"):
        load_calendar(tmp_path / "missing.json")


def test_missing_title_fails(tmp_path: Path) -> None:
    event = {**VALID_EVENT}
    del event["title"]
    path = _write_calendar(tmp_path, [event])
    with pytest.raises(CalendarError, match="missing required field 'title'"):
        load_calendar(path)


def test_missing_location_field_fails(tmp_path: Path) -> None:
    event = {
        **VALID_EVENT,
        "location": {"name": "Test", "latitude": 29.0},
    }
    path = _write_calendar(tmp_path, [event])
    with pytest.raises(CalendarError, match="missing required field 'longitude'"):
        load_calendar(path)


def test_invalid_coordinates_fail(tmp_path: Path) -> None:
    event = {
        **VALID_EVENT,
        "location": {**VALID_EVENT["location"], "latitude": 95.0},
    }
    path = _write_calendar(tmp_path, [event])
    with pytest.raises(CalendarError, match="Invalid latitude"):
        load_calendar(path)

    event = {
        **VALID_EVENT,
        "location": {**VALID_EVENT["location"], "longitude": 200.0},
    }
    path = _write_calendar(tmp_path, [event])
    with pytest.raises(CalendarError, match="Invalid longitude"):
        load_calendar(path)


def test_invalid_timestamps_fail(tmp_path: Path) -> None:
    event = {**VALID_EVENT, "start": "not-a-date"}
    path = _write_calendar(tmp_path, [event])
    with pytest.raises(CalendarError, match="Invalid start"):
        load_calendar(path)

    event = {
        **VALID_EVENT,
        "start": "2026-06-17T10:00:00",
        "end": "2026-06-17T09:00:00",
    }
    path = _write_calendar(tmp_path, [event])
    with pytest.raises(CalendarError, match="end time before start"):
        load_calendar(path)


def test_empty_calendar_fails(tmp_path: Path) -> None:
    path = _write_calendar(tmp_path, [])
    with pytest.raises(CalendarError, match="no events"):
        load_calendar(path)
