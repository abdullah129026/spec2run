# Spec2Run — 3-Week Build Roadmap

Project: Spec2Run — Voice to Microservice. "Talk your API into existence."
Window: 2026-10-08 → 2026-10-29. Public repo, deployed, $0 stack.
Bar: 9/10. That means measured evals, working auth, visible diffs, real Postgres
per sandbox, and real users — not just features.

## Week 1 — Spec engine (Days 1–7)

- [x] Groq LLM client (JSON mode) + config wiring (`backend/app/services/llm.py`;
      `SPEC2RUN_GROQ_API_KEY`, `SPEC2RUN_MODEL` default `openai/gpt-oss-120b`)
- [x] Prompt → OpenAPI 3.0 generator (system prompt forces valid JSON only;
      `backend/app/services/specgen.py`, endpoint `POST /specs/generate`)
- [x] OpenAPI structural validator (paths, schemas, refs;
      `backend/app/services/validate.py`; invalid drafts rejected, never rendered)
- [x] Vague-prompt guardrail (clarifying questions, never guesses; model returns
      `needs_clarification` shape, answered via `POST /specs/refine`)
- [ ] **OpenAPI import** — paste a Swagger URL or file, get an editable project
      (no LLM involved; second demo path that can't fail on model quality)
- [ ] Prompt Studio UI (textarea, option buttons, example prompts)
- [ ] Swagger preview tab (swagger-ui-react rendered from the spec)

## Week 2 — Code generation (Days 8–14)

- [ ] Jinja2 template engine + FastAPI/SQLAlchemy templates
- [ ] Entity/field/relation slot filling from the spec
- [ ] **Working JWT auth in the template** — register, login, protected routes
      with real token verification (the thing every competitor fakes)
- [ ] Generated code syntax check before showing it
- [ ] Monaco editor tab (editable code)
- [ ] **Spec + code diff view** — "add reviews to books" shows exactly what
      changed, git-style, in spec JSON and rendered files
- [ ] Download ZIP
- [ ] Push to GitHub (user supplies a token in the UI)

## Week 3 — Voice, sandbox, eval, launch (Days 15–21)

- [ ] Voice input (Web Speech API; Groq Whisper as fallback)
- [ ] Live sandbox — supervised subprocess, proxied URL, TTL cleanup
- [ ] **Neon Postgres per sandbox** — branch via API on boot, delete on expiry
      (SQLite fallback when `NEON_API_KEY` is unset)
- [ ] **Eval harness** — 50-prompt corpus; spec → validate → render → boot →
      smoke-test (incl. auth flow); results to `docs/EVAL.md` with failures
      listed honestly
- [ ] Deploy: Vercel frontend + Render backend (`NEON_API_KEY`,
      `SPEC2RUN_GROQ_API_KEY` in Render env)
- [ ] **Real users** — post in hackathon/student Discords, watch 10 people
      generate APIs, fix what breaks, collect quotes
- [ ] README polish (eval table, architecture diagram), demo script
- [ ] v1.0 tag

## Deferred — honest cuts for the 3-week window

- Express/Prisma templates (FastAPI first; depth over breadth)
- MongoDB option (Postgres via Neon first)
- One-click Railway deploy of generated services (sandbox instead)
- Pro billing and custom domains for generated APIs
