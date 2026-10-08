# Spec2Run Architecture

## Pipeline

```
[Voice / text prompt] ─┬─→ [STT] → [LLM → OpenAPI 3.0 JSON] ─┐
                       │                                      ├→ [Validator] → [Template + LLM codegen]
[OpenAPI URL / file] ──┴→ [Importer → OpenAPI 3.0 JSON] ─────┘         │
                                                                       ↓
                                                              [Sandbox runner (Neon Postgres)]
                                                                       ↓
                                                              [Live URL + Swagger UI]
```

Two ways in: describe what you want (LLM drafts the spec), or paste an
existing Swagger URL (imported directly, no LLM involved).

## Modules

**A. Voice-to-spec engine.** Mic input uses the Web Speech API (browser-native,
free, no key). The prompt goes to Groq with JSON mode and a system prompt that
forces output to be OpenAPI 3.0 and nothing else. Vague prompts return
clarifying questions instead of a guess.

**B. Code generator (a core contribution).** The LLM never writes the service
freehand. It fills typed slots (entities, fields, relations, auth scheme) and
Jinja2 templates render runnable FastAPI + SQLAlchemy code. Template + LLM
hybrid generation: the template guarantees structure, the model supplies
content. The auth template ships **working JWT**: register, login, and
protected routes with real token verification, smoke-tested in the sandbox.

**C. Live sandbox.** The generated service runs as a supervised subprocess on
our backend. Each sandbox gets a **real Postgres database**: a Neon branch
(copy-on-write, ~1s to create) via the Neon API, connection string injected as
env, branch deleted on expiry. Falls back to SQLite when `NEON_API_KEY` is
unset (local dev). HTTP is proxied at `/sandbox/{id}`. The process is killed
after `SANDBOX_TTL_SECONDS` (default 3600) and temp files are removed. No
Docker-in-Docker, no per-user cloud accounts: the demo (a live URL with a real
database, seconds after generation) works on the $0 stack.

**D. Versioning with visible diffs.** "Add reviews to books" produces a JSON
patch against the stored spec, not a regeneration. The diffing module renders
old-vs-new as JSON diffs (spec) and unified diffs (code) for a git-style
diff view in the frontend. History is kept per project, like git log for the
API design.

**E. Eval harness (measured, not claimed).** `backend/eval/` holds a corpus of
50 prompts (`prompts.jsonl`). The runner, for each prompt: generates the spec,
validates the OpenAPI structurally, renders the code, boots a sandbox, and
smoke-tests every endpoint including the auth flow when the spec asks for it.
Results are written to `docs/EVAL.md` as a markdown table — pass rates *and*
failures with reasons. Runs on demand (not per push, to spare Groq quota).

## Key decisions

- **Sandbox over Railway.** Railway has no free tier, and deploying one service
  per user needs platform API keys and real spend. The sandbox gives the same
  observable result (a live URL seconds after generation) for $0.
- **Neon branching over provisioned Postgres.** One branch per sandbox, created
  and destroyed via API. Real Postgres semantics with zero idle cost.
- **Web Speech over Whisper API.** Free, no key, no upload latency. Groq's
  Whisper endpoint stays as a fallback for audio file uploads.
- **Template + LLM hybrid over pure LLM codegen.** Deterministic structure,
  unit-testable templates, and the model can't hallucinate an import.
- **Groq SDK**, same pattern as the PRISM backend (already proven).

## Security

- Generated code is never executed directly: only rendered templates with
  validated slots reach the sandbox.
- Sandbox subprocesses run with no network egress and CPU/memory limits;
  templates cannot import `os.system`, `subprocess`, or `socket`.
- Per-sandbox database credentials are generated per branch, injected as env,
  never logged, and revoked with the branch.
- `NEON_API_KEY` lives server-side only (Render env, never in chat or the repo).
- Sandbox TTL + kill on expiry; per-IP rate limits on the expensive endpoints
  (spec generation, sandbox boot).
- No secrets in generated code or logs.
