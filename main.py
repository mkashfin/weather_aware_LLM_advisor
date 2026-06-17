#!/usr/bin/env python3
"""Entry point for the weather-aware personal assistant CLI."""

from __future__ import annotations

import sys
from pathlib import Path

from assistant.calendar import CalendarError, load_calendar
from assistant.repl import run_repl

CALENDAR_FILE = Path(__file__).parent / "calendar.json"
CALENDAR_ERROR = "Unable to load calendar data."


def main() -> int:
    try:
        events = load_calendar(CALENDAR_FILE)
    except CalendarError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(CALENDAR_ERROR, file=sys.stderr)
        return 1

    run_repl(events)
    return 0


if __name__ == "__main__":
    sys.exit(main())
