# CareBot

An emotional support chatbot for students. CareBot tracks a student's emotional state over a conversation with its Emotional Vector Core (EVC) engine, adapts its replies with an LLM, and raises an alert for teachers when the state reaches a crisis level.

> **CareBot is not a medical device and does not replace a counselor or emergency service.** It handles sensitive student data. Review its safety behavior, privacy practices and consent process with qualified people before any real use.

## How it works

```text
Message → emotion extraction → hormone model → zone and forces → LLM reply
                                     └─ crisis level (E ≤ -6) → teacher alert
```

- **Emotion extraction:** a fast LLM returns structured emotion features, with Thai and English keyword rules as a fallback.
- **Hormone model:** eight simulated hormones (serotonin, dopamine, cortisol, oxytocin, adrenaline, endorphin, GABA and norepinephrine) rise, interact and decay to produce an emotional score.
- **Mirroring:** the bot paces with the student and then gently leads toward recovery.
- **Reply generation:** the LLM writes the response using the current EVC state.
- **Channels:** an OpenClaw agent connects LINE and Discord through the skills in `openclaw/skills/`.

## Tech stack

Python 3.11, FastAPI, Groq (Llama models), JWT and Google sign-in, in-memory storage or Azure Cosmos DB, Docker, and OpenClaw.

## Getting started

The project is in [`NDLP_project/carebot`](NDLP_project/carebot).

```bash
cd NDLP_project/carebot
cp .env.example .env
```

Fill in `.env`. The LLM client reads `GROQ_API_KEY`, so add that name even though `.env.example` currently lists `GROK_API_KEY`.

With Docker (FastAPI and OpenClaw):

```bash
docker compose up --build
```

Without Docker (API only):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8000
```

Interactive API docs are at <http://localhost:8000/docs>.

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/auth/register`, `/auth/login` | Username and password accounts |
| `POST` | `/auth/google` | Google sign-in |
| `POST` | `/auth/guest` | Guest session |
| `GET` | `/auth/me` | Current user |
| `POST` | `/auth/link-platform` | Link a LINE or Discord ID |
| `POST` | `/evc/process` | Run the full pipeline for a message |
| `GET` | `/evc/state` | Current EVC state |
| `POST` | `/evc/reset/{user_id}` | Reset a user's state |

## Tests

```bash
pytest tests/test_auth.py tests/test_evc_engine.py
```

`tests/test_flow.py` is a manual multi-turn script that needs the API running on port 8000.

## Project structure

```text
NDLP_project/carebot/
  api/        FastAPI app, routes and auth middleware
  evc/        Emotion extraction, hormones, scoring, rules and mirroring
  models/     Pydantic models
  services/   Auth, LLM client and memory store
  openclaw/   Agent configuration and channel skills
  tests/      Automated tests and flow script
```
