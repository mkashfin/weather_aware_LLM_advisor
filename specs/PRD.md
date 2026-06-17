# Product Requirements Document (PRD)

# Project Name
Weather-Aware Personal Assistant (CLI / REPL)

## Vision

Build a terminal-based personal assistant that reads a user's local calendar.json file as events schedule, enriches each event with weather information from Open-Meteo, and uses a local LLM (Ollama running Llama 3.2) to synthesize practical recommendations for the user.

The assistant should help answer questions such as:

- "How should I travel to my meeting tomorrow?"
- "Will I need an umbrella?"
- "Should I drive, take public transit, or walk?"
- "What should I prepare before attending this activity?"
- "What clothes I should wear for this particular activity in particular time and location"


The system must run locally through a CLI REPL experience. The app must be delivered in A modular folder structure with small and focused on the number of folders and files.


---

# Goals

The assistant must:

1. Read schedule data from a local `calendar.json`.
2. Parse and validate calendar events.
3. Retrieve weather forecasts from Open-Meteo for event locations and times.
4. Generate practical recommendations using Ollama Llama 3.2.
5. Provide a conversational REPL interface.
6. Operate without requiring cloud LLM services.


# Functional Requirements

## FR-1: Calendar Loading

The system shall read a local file:

```
calendar.json
```

at startup.

If the file does not exist:

- display an informative error,
- exit gracefully.

If malformed JSON is detected:

- display validation errors,
- exit gracefully.

---

## FR-2: Calendar Schema

The calendar file shall contain an array of events.


# Example calendar.json

```json
[
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
  },
  {
    "title": "Evening Tennis",
    "start": "2026-06-17T18:00:00",
    "end": "2026-06-17T20:00:00",
    "activity": "Sports",
    "location": {
      "name": "Memorial Park",
      "latitude": 29.7674,
      "longitude": -95.4410
    }
  }
]
```

---

## FR-3: Weather Retrieval

For each event, the system shall fetch weather information from Open-Meteo.

API:

```
https://api.open-meteo.com/v1/forecast
```

Parameters Example:

```
https://api.open-meteo.com/v1/forecast
?latitude=29.7604
&longitude=-95.3698
&hourly=temperature_2m,precipitation_probability,weather_code
&timezone=auto
```

---

## FR-4: Weather Selection Logic

The assistant shall select the hourly forecast nearest to the event start time.

Example:

Event:
08:15

Forecast hours:
08:00
09:00

Selected:
08:00

Maximum allowed deviation:
±60 minutes.

If no suitable forecast exists:

- inform the user,
- provide advice generation using available forecast for that event and mention it properly
- 

---

## FR-5: Advice Generation

The system shall invoke Ollama using:

```
llama3.2
```

Example:

```bash
ollama run llama3.2
```

The assistant shall provide the LLM with:

- event title,
- activity,
- event time,
- location,
- temperature,
- precipitation probability,
- weather condition.

The assistant shall request:

- practical recommendations,
- transportation suggestions,
- preparation tips,
- concise explanations.

---

## FR-6: Advice Output Format

Generated advice must:

- contain 5–7 lines,
- be actionable,
- avoid generic motivational language,
- prioritize safety,
- mention weather implications,
- recommend transportation when appropriate.

Example:

```
The forecast suggests moderate rain during your commute.
Using public transit or driving would be more comfortable than walking.
Carry an umbrella and wear waterproof footwear.
Allow extra travel time because roads may be slower than usual.
Keep essential electronics protected from moisture.
The temperature remains mild, so heavy outerwear is unnecessary.
```

---

## FR-7: REPL Interface

The application shall expose a command loop.

Example:

```
assistant>
```

Supported commands:

### help

Displays available commands.

---

### list

Displays upcoming events.

Example:

```
assistant> list

1. Morning Commute
2. Evening Tennis
```

---

### advise

Generate advice for all events.

Example:

```
assistant> advise
```

---

### advise <index>

Generate advice for a single event.

Example:

```
assistant> advise 2
```

---

### exit

Terminate the application.

---

# LLM Prompt Template

The following prompt template shall be used.

```
You are a practical personal planning assistant.

Event:
Title: {title}
Activity: {activity}
Location: {location}
Time: {time}

Weather:
Temperature: {temperature}°F
Precipitation Probability: {precipitation}%
Condition: {condition}

Provide a 5–7 line recommendation that:
- suggests transportation options,
- advises what to bring,
- considers comfort and safety,
- adapts to the activity,
- avoids unnecessary verbosity.
```

---

# Error Handling

## Calendar Errors

Handle:

- Missing file
- Invalid JSON
- Missing required fields
- Invalid coordinates
- Invalid datetime format

---

## Weather Errors

Handle:

- API timeout
- HTTP errors
- Unexpected API schema
- Missing hourly forecast

Fallback:

```
Unable to retrieve weather information for this event.
Write the error log properly for any type of error in the terminal
Advice generation skipped.
```

---

## Ollama Errors

Handle:

- Ollama not installed
- Ollama daemon unavailable
- llama3.2 model missing
- model inference failures

Fallback:

```
Unable to generate advice at this time.
Write the error log properly for any type of error in the terminal
```

---

# Architecture

```
calendar.json
      ↓
Calendar Loader
      ↓
Schema Validator
      ↓
Weather Service (Open-Meteo)
      ↓
Forecast Selector
      ↓
Advice Generator (Ollama llama3.2)
      ↓
CLI REPL
```


# Acceptance Criteria

The implementation is complete when:

- Calendar events load successfully.
- Weather is retrieved from Open-Meteo.
- Forecasts align with event times.
- Ollama llama3.2 generates recommendations.
- REPL commands function correctly.
- Automated tests pass.
- Errors are handled gracefully.

---

# Test Guardrails

The following automated tests MUST exist.

## tests/test_calendar.py

Validate:

- valid calendar loads,
- malformed JSON fails,
- missing fields fail,
- invalid coordinates fail,
- invalid timestamps fail.

---

## tests/test_weather.py

Validate:

- Open-Meteo response parsing,
- nearest forecast selection,
- missing hourly values,
- weather service failures.

---

## tests/test_advice.py

Validate:

- prompt construction,
- weather context inclusion,
- activity inclusion,
- output length enforcement.

Mock Ollama responses.

---

## tests/test_repl.py

Validate:

- help command,
- list command,
- advise command,
- advise index command,
- exit command.

---

## tests/test_integration.py

Validate end-to-end execution:

calendar.json
→ weather retrieval (mocked)
→ advice generation (mocked)
→ CLI output.

---
