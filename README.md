# Spec2Run — Voice to Microservice

**"Talk your API into existence. Speak in English, get a live deployed microservice."**

Describe an API in plain English (or say it out loud) and Spec2Run generates a
validated OpenAPI 3.0 spec, renders runnable service code from templates, and
boots it in a live sandbox — real Postgres included — you can call immediately.
Or paste an existing Swagger URL and get an editable, runnable clone.

## How it works

1. **Prompt** — type or speak what you want ("a bookstore API with books,
   authors, and orders; books have title and price; JWT auth").
   Or **import** an existing OpenAPI document by URL.
2. **Spec** — an LLM drafts OpenAPI 3.0 JSON under a strict schema; vague
   prompts get clarifying questions instead of guesses.
3. **Code** — template + LLM hybrid: the model fills typed slots (entities,
   fields, auth), Jinja2 templates render runnable FastAPI code with **working
   JWT auth** (register, login, protected routes, real token verification).
4. **Live** — the service boots in an isolated sandbox with its own Postgres
   database (Neon branch, created and destroyed per sandbox) and a URL you can
   hit right away. Say "add reviews to books" and you get a git-style diff of
   exactly what changed. Download the ZIP or push it to GitHub.

## Evaluation

Measured, not claimed. `backend/eval/` runs 50 prompts through the full
pipeline (spec → validate → render → boot → smoke-test, including the auth
flow) and writes the results to `docs/EVAL.md`, failures included.

| Metric | Result |
|--------|--------|
| Prompts evaluated | 50 |
| Valid OpenAPI on first try | _pending first eval run_ |
| Sandbox boot success | _pending first eval run_ |
| Endpoints passing smoke tests | _pending first eval run_ |
| Auth flow passing (where requested) | _pending first eval run_ |
| Median generation time | _pending first eval run_ |

## Stack

| Layer    | Tech |
|----------|------|
| Frontend | Next.js 14, Tailwind, Monaco Editor, swagger-ui-react |
| Backend  | FastAPI, Jinja2 |
| AI       | Groq (spec generation), Web Speech API (voice input) |
| Data     | Neon Postgres (one branch per sandbox), SQLite fallback |
| Deploy   | Vercel (frontend), Render (backend) — $0 |

## Quick start

```bash
# backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

Or with Docker:

```bash
docker compose up --build
```

Set `SPEC2RUN_GROQ_API_KEY` for spec generation. Set `NEON_API_KEY` for real
Postgres per sandbox (falls back to SQLite without it).

## Roadmap

3-week build (2026-10-08 → 2026-10-29). See [docs/ROADMAP.md](docs/ROADMAP.md).

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

MIT
