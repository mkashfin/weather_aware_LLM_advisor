# Weather-Aware Personal Assistant (CLI)
A terminal-based assistant that reads your local schedule from `calendar.json`, fetches weather forecasts from [Open-Meteo](https://open-meteo.com/), and uses a local LLM ([Ollama](https://ollama.com/) with `llama3.2`) to generate practical travel and preparation advice.

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| **Python 3.10+** | Run the application and tests |
| **Internet access** | Fetch weather data from Open-Meteo |
| **Ollama** | Local LLM for advice generation |
| **llama3.2 model** | The model used for recommendations |

### Install Ollama and the model

1. Download and install Ollama from [https://ollama.com](https://ollama.com).
2. Pull the required model:

```bash
ollama pull llama3.2
```

3. Verify Ollama is running:

```bash
ollama list
```
You should see `llama3.2` in the list. Ollama starts automatically when you run a model or can be started manually.

---

## Installation

1. Open a terminal in the project folder.

2. (Recommended) Create and activate a virtual environment:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```
---

## Running the App

Start the assistant from the project root:

```bash
python main.py
```

On startup, the app loads `calendar.json` and displays all available commands. You will then see the prompt:

```
assistant>
```

### Example session

```
Available commands:
  help            Show this help message
  list            List upcoming events
  advise          Generate advice for all events
  advise <index>  Generate advice for a single event
  exit            Exit the application

assistant> list
1. Morning Commute
   Activity: Work
   Date: 2026-06-17
   Time: 08:00
   Location: Downtown Houston
...

assistant> advise 1

--- Advice for event 1: Morning Commute ---
Activity: Work
Date: 2026-06-17
Time: 08:00
Location: Downtown Houston

[5–7 lines of weather-aware advice from the LLM]

assistant> exit
```

---

## REPL Commands

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `list` | List all events with activity, date, time, and location |
| `advise` | Generate advice for **every** event |
| `advise <index>` | Generate advice for a **single** event (e.g. `advise 2`) |
| `exit` | Quit the application |

Unknown commands return:

```
Unknown command. Type 'help' for available commands.
```

---

## Adding and Editing Events

Events are stored in `calendar.json` at the project root. **Edit this file, save your changes, then restart the app** (`python main.py`) for updates to take effect.

### Calendar schema

The file must be a JSON **array** of event objects. Each event requires:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Event name |
| `start` | string | Start time in ISO format (`YYYY-MM-DDTHH:MM:SS`) |
| `end` | string | End time in ISO format |
| `activity` | string | Activity type (e.g. `Work`, `Sports`, `Social`, `Travel`, `Outdoor`) |
| `location` | object | See below |

**Location object:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable place name |
| `latitude` | number | -90 to 90 |
| `longitude` | number | -180 to 180 |

### Example event

```json
{
  "title": "Morning Commute",
  "start": "2026-06-17T08:00:00",
  "end": "2026-06-17T09:00:00",
  "activity": "Work",
  "location": {
    "name": "Downtown Houston",
    "latitude": 29.7604,
    "longitude": -95.3698
  }
}
```

### Tips for new inputs

- Use valid ISO datetime strings (no timezone suffix required).
- Ensure `end` is not before `start`.
- Use accurate latitude/longitude for the event location so weather forecasts are correct.
- You can find coordinates via Google Maps (right-click a location → coordinates) or similar tools.
- Keep the file as valid JSON (commas between objects, no trailing comma on the last item).

### Validate your calendar before running

If `calendar.json` is invalid, the app exits at startup with an error message. Common issues:

- Missing `calendar.json` file
- Malformed JSON (missing quotes, extra commas)
- Missing required fields (`title`, `start`, `end`, `activity`, `location`)
- Invalid coordinates or datetime format

---

## Diagnosing Issues

### Calendar errors

**Symptom:** App exits immediately on startup.

```
Error: ...
Unable to load calendar data.
```

**What to check:**
- `calendar.json` exists in the same folder as `main.py`
- File is valid JSON (use a JSON validator or editor)
- Every event has all required fields
- Latitude is between -90 and 90; longitude between -180 and 180
- Datetimes use format like `2026-06-17T08:00:00`

---

### Weather errors

**Symptom:** Advice is skipped for an event.

```
Error: ...
Unable to retrieve weather information for this event.
Advice generation skipped.
```

**What to check:**
- Internet connection is active
- Open-Meteo is reachable: [https://api.open-meteo.com/v1/forecast](https://api.open-meteo.com/v1/forecast)
- Event coordinates are correct
- Event date is within the forecast range (Open-Meteo provides limited future/historical coverage)

If no hourly forecast is within ±60 minutes of the event start, the app uses the nearest available hour and notes the deviation in the advice prompt.

---

### Ollama / LLM errors

**Symptom:**

```
Error: ...
Unable to generate advice at this time.
```

**What to check:**

| Check | Command / action |
|-------|------------------|
| Ollama installed | Visit [ollama.com](https://ollama.com) |
| Ollama running | Run `ollama list` — should not error |
| Model available | Run `ollama pull llama3.2` |
| API reachable | Ollama serves at `http://localhost:11434` by default |

**Quick Ollama test:**

```bash
ollama run llama3.2 "Say hello in one sentence."
```

If that works, the assistant should be able to generate advice.

---

### Slow or hanging advice

- First model load can take longer; subsequent requests are faster.
- `advise` (all events) calls the LLM once per event — use `advise <index>` for a single event when testing.
- Ensure your machine has enough RAM for `llama3.2`.

---

### Invalid event index

```
Invalid event index. Choose 1–N.
```

Run `list` first to see valid index numbers (1-based).

---

## Testing

Automated tests use `pytest` and **mock** external APIs (Open-Meteo and Ollama), so tests do not require internet or a running Ollama instance.

### Run all tests

```bash
python -m pytest tests/ -v
```

### Run a specific test file

```bash
python -m pytest tests/test_calendar.py -v
python -m pytest tests/test_weather.py -v
python -m pytest tests/test_advice.py -v
python -m pytest tests/test_repl.py -v
python -m pytest tests/test_integration.py -v
```

### Run a single test

```bash
python -m pytest tests/test_repl.py::test_list_command -v
```

### Test coverage overview

| Test file | What it validates |
|-----------|-------------------|
| `test_calendar.py` | Valid/invalid JSON, missing fields, bad coordinates, bad timestamps |
| `test_weather.py` | API response parsing, nearest forecast selection, error handling |
| `test_advice.py` | Prompt construction, rule hints, Ollama integration (mocked) |
| `test_repl.py` | REPL commands, list format, startup help, advise output |
| `test_integration.py` | End-to-end flow with mocked weather and LLM |

### Manual smoke test (live services)

1. Ensure Ollama is running with `llama3.2` pulled.
2. Start the app: `python main.py`
3. Run `list` — events should display with activity, date, time, location.
4. Run `advise 1` — weather should be fetched and LLM advice printed.
5. Run `exit` to quit.

---

## Project Structure

```
main/
├── main.py              # Application entry point
├── calendar.json        # Your schedule (edit this file)
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── assistant/
│   ├── calendar.py      # Load and validate calendar.json
│   ├── weather.py       # Open-Meteo API and forecast selection
│   ├── advice.py        # Rule hints + Ollama advice generation
│   └── repl.py          # CLI command loop
├── tests/               # Automated test suite
└── docs/                # Assistant rules
    rules.md
└── specs/               # Product requirements
    PRD.md
```

---


For requirements and behavior details, see `specs/PRD.md` and `docs/rules.md`.

