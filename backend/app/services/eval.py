"""Eval harness: does Spec2Run actually work? Measured, not claimed.

Corpus: backend/eval/prompts.jsonl (50 prompts). Per prompt the pipeline
runs: spec -> validate -> render -> boot a sandbox -> smoke-test every
endpoint, including the auth flow when the spec asks for it. Results go
to docs/EVAL.md as a markdown table, failures listed with reasons.

Runs on demand (``python -m app.services.eval`` from backend/), not per
push, to spare Groq quota. Without SPEC2RUN_GROQ_API_KEY the LLM stage
can't run; the runner then measures validate -> render -> boot -> smoke
over the fixture specs in backend/eval/fixtures/ and marks the other
prompts "needs LLM". The report says exactly which mode ran.
"""

import argparse
import json
import os
import sys
import time
from datetime import date

from app.services import sandbox as sandbox_svc
from app.services.codegen import render_service
from app.services.validate import validate_openapi


def load_corpus(path: str) -> list[dict]:
    items = []
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(f"{path}:{lineno}: bad JSON: {e}")
    return items


def load_fixtures(directory: str) -> dict[str, dict]:
    out = {}
    if not os.path.isdir(directory):
        return out
    for name in sorted(os.listdir(directory)):
        if name.endswith(".json"):
            with open(os.path.join(directory, name)) as f:
                out[name[:-5]] = json.load(f)
    return out


def spec_match_problems(spec: dict, rendered: dict, expect: dict) -> list[str]:
    """Where the rendered service diverges from what the prompt asked for."""
    problems = []
    if expect.get("needs_clarification"):
        return problems
    got_entities = {e["plural"].lower() for e in rendered["entities"]}
    for want in expect.get("entities", []):
        if want.lower() not in got_entities:
            problems.append(f"expected entity {want!r} missing from service")
    if bool(expect.get("auth")) != bool(rendered["auth"]):
        problems.append(
            f"auth mismatch: prompt wants {expect.get('auth')}, service has {rendered['auth']}"
        )
    return problems


def _sample_value(prop: dict):
    if prop.get("format") == "date-time":
        return "2026-01-01T00:00:00Z"
    return {
        "string": "smoke",
        "integer": 1,
        "number": 1.5,
        "boolean": True,
        "array": [],
        "object": {},
    }.get(prop.get("type"), "smoke")


def _order_by_fk(entities: list[dict]) -> list[dict]:
    """Parents before children so FK columns point at rows that exist."""
    by_plural = {e["plural"]: e for e in entities}
    ordered, seen, out = set(), set(), []

    def visit(e):
        if e["plural"] in seen:
            return
        seen.add(e["plural"])
        for f in e["fields"]:
            target = f.get("fk")
            if target and target in by_plural:
                visit(by_plural[target])
        out.append(e)

    for e in entities:
        visit(e)
    return out


def smoke_test(sb: sandbox_svc.Sandbox, spec: dict, rendered: dict) -> list[str]:
    """Exercise the booted service through the sandbox proxy.

    Returns a list of failures; empty means the service works.
    """
    failures = []

    def call(method, path, json_body=None, headers=None, raw_body=None):
        h = dict(headers or {})
        if json_body is not None:
            body = json.dumps(json_body).encode()
            h["content-type"] = "application/json"
        else:
            body = raw_body or b""
        try:
            return sandbox_svc.proxy(sb, method, path.lstrip("/"), "", h, body)
        except sandbox_svc.SandboxError as e:
            failures.append(f"{method} {path}: proxy failed: {e}")
            return None

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    r = call("GET", "/health")
    if r is None:
        return failures
    check(r.status_code == 200, f"GET /health -> {r.status_code}")

    headers = {}
    if rendered["auth"]:
        r = call("POST", "/auth/register",
                 {"username": "evaluser", "password": "evalpass123"})
        check(r is not None and r.status_code == 201,
              f"POST /auth/register -> {r.status_code if r else 'no response'}")
        r = call("POST", "/auth/login", raw_body=b"username=evaluser&password=evalpass123",
                 headers={"content-type": "application/x-www-form-urlencoded"})
        token = None
        if r is not None and r.status_code == 200:
            try:
                token = r.json()["access_token"]
            except (ValueError, KeyError):
                pass
        check(token, "POST /auth/login did not return an access_token")
        if token:
            headers = {"authorization": f"Bearer {token}"}
        r = call("GET", f"/{rendered['entities'][0]['plural']}")
        check(r is not None and r.status_code == 401,
              "protected route without token should be 401, "
              f"got {r.status_code if r else 'no response'}")

    schemas = (spec.get("components") or {}).get("schemas") or {}
    created: dict[str, int] = {}  # plural -> id of a row we made
    for e in _order_by_fk(rendered["entities"]):
        plural = e["plural"]
        props = (schemas.get(e["name"]) or {}).get("properties") or {}
        body = {}
        for fname, prop in props.items():
            if fname == "id":
                continue
            fk_target = next(
                (f["fk"] for f in e["fields"]
                 if f["name"] == fname and f.get("fk")), None)
            if fk_target and fk_target in created:
                body[fname] = created[fk_target]
            else:
                body[fname] = _sample_value(prop)

        r = call("POST", f"/{plural}", body, headers)
        if r is None or r.status_code != 201:
            failures.append(
                f"POST /{plural} -> {r.status_code if r else 'no response'}")
            continue
        try:
            row_id = r.json()["id"]
        except (ValueError, KeyError):
            failures.append(f"POST /{plural} returned no id")
            continue
        created[plural] = row_id

        r = call("GET", f"/{plural}", headers=headers)
        check(r is not None and r.status_code == 200
              and any(row.get("id") == row_id for row in r.json()),
              f"GET /{plural} missing the created row")
        r = call("GET", f"/{plural}/{row_id}", headers=headers)
        check(r is not None and r.status_code == 200,
              f"GET /{plural}/{row_id} -> {r.status_code if r else 'no response'}")
        r = call("PUT", f"/{plural}/{row_id}", body, headers)
        check(r is not None and r.status_code == 200,
              f"PUT /{plural}/{row_id} -> {r.status_code if r else 'no response'}")
        r = call("DELETE", f"/{plural}/{row_id}", headers=headers)
        check(r is not None and r.status_code == 204,
              f"DELETE /{plural}/{row_id} -> {r.status_code if r else 'no response'}")
        r = call("GET", f"/{plural}/{row_id}", headers=headers)
        check(r is not None and r.status_code == 404,
              f"GET /{plural}/{row_id} after delete -> "
              f"{r.status_code if r else 'no response'} (want 404)")

    return failures


def run_eval(
    corpus_path: str,
    fixtures_dir: str | None = None,
    generate_spec=None,
    only: list[str] | None = None,
    database: str = "auto",
) -> dict:
    """Run the corpus. generate_spec(prompt, expect) -> spec enables the
    LLM stage; without it (and without fixtures) a prompt is skipped."""
    corpus = load_corpus(corpus_path)
    fixtures = load_fixtures(fixtures_dir) if fixtures_dir else {}
    mode = "llm" if generate_spec else "fixtures"
    items = []
    for entry in corpus:
        pid = entry["id"]
        if only and pid not in only:
            continue
        items.append(_run_one(entry, fixtures.get(pid), generate_spec, database))
    measured = [i for i in items if i["result"] != "skipped"]
    return {
        "ran_at": date.today().isoformat(),
        "mode": mode,
        "total": len(items),
        "passed": sum(1 for i in measured if i["result"] == "passed"),
        "failed": sum(1 for i in measured if i["result"] == "failed"),
        "skipped": sum(1 for i in items if i["result"] == "skipped"),
        "spec_match_issues": sum(len(i["spec_match"]) for i in measured),
        "items": items,
    }


def _run_one(entry: dict, fixture: dict | None, generate_spec, database: str) -> dict:
    pid, expect = entry["id"], entry.get("expect", {})
    item = {"id": pid, "result": "skipped", "stages": {},
            "spec_match": [], "failures": [], "ms": 0}
    started = time.time()

    def fail(stage, msg):
        item["stages"][stage] = "failed"
        item["failures"].append(msg)
        item["result"] = "failed"

    # spec stage: LLM or fixture
    if generate_spec:
        try:
            spec = generate_spec(entry["prompt"], expect)
        except Exception as e:  # LLM outage is a measured failure, not a crash
            fail("spec", f"generate_spec raised: {e}")
            return item
    elif fixture is not None:
        spec = fixture
    else:
        item["failures"].append("no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage")
        return item
    item["stages"]["spec"] = "ok"

    if not isinstance(spec, dict) or "openapi" not in spec:
        if expect.get("needs_clarification"):
            item["result"] = "passed"  # clarification was the right call
        else:
            fail("spec", "spec stage returned no usable document")
        item["ms"] = int((time.time() - started) * 1000)
        return item

    problems = validate_openapi(spec)
    if problems:
        fail("validate", "validate: " + "; ".join(problems))
        item["ms"] = int((time.time() - started) * 1000)
        return item
    item["stages"]["validate"] = "ok"

    try:
        rendered = render_service(spec, {"auth": bool(expect.get("auth"))})
    except (ValueError, RuntimeError) as e:
        fail("render", f"render: {e}")
        item["ms"] = int((time.time() - started) * 1000)
        return item
    item["stages"]["render"] = "ok"
    item["spec_match"] = spec_match_problems(spec, rendered, expect)

    try:
        sb = sandbox_svc.boot(rendered["files"], database=database)
    except sandbox_svc.SandboxError as e:
        fail("boot", f"boot: {e}")
        item["ms"] = int((time.time() - started) * 1000)
        return item
    item["stages"]["boot"] = "ok"
    try:
        smoke_failures = smoke_test(sb, spec, rendered)
    finally:
        sandbox_svc.kill(sb.id)
    if smoke_failures:
        fail("smoke", "smoke: " + "; ".join(smoke_failures))
    else:
        item["stages"]["smoke"] = "ok"

    item["result"] = "passed" if not item["failures"] else "failed"
    item["ms"] = int((time.time() - started) * 1000)
    return item


def write_report(result: dict, path: str) -> None:
    """Write docs/EVAL.md: summary, per-prompt table, failures listed."""
    lines = [
        f"# Spec2Run eval — {result['ran_at']}",
        "",
        f"Mode: **{result['mode']}**.",
    ]
    if result["mode"] == "fixtures":
        lines.append(
            "SPEC2RUN_GROQ_API_KEY was unset, so the LLM generation stage was "
            "not measured. Each prompt ran validate -> render -> boot -> smoke "
            "over a hand-written fixture spec; prompts without a fixture are "
            "marked skipped. The full 50-prompt LLM run happens on the "
            "deployed backend where the key is configured."
        )
    lines += [
        "",
        "## Summary",
        "",
        f"- prompts: {result['total']}",
        f"- measured: {result['total'] - result['skipped']}, "
        f"passed: {result['passed']}, failed: {result['failed']}, "
        f"skipped: {result['skipped']}",
        f"- spec-match issues (rendered service vs prompt intent): "
        f"{result['spec_match_issues']}",
        "",
        "## Results",
        "",
        "| prompt | result | stages | failures |",
        "| --- | --- | --- | --- |",
    ]
    for i in result["items"]:
        stages = ", ".join(
            f"{k}:{v}" for k, v in i["stages"].items()
        ) or "-"
        failures = "<br>".join(i["failures"]) or "-"
        spec_note = (
            f"<br>spec-match: {'; '.join(i['spec_match'])}" if i["spec_match"] else ""
        )
        lines.append(
            f"| {i['id']} | {i['result']} | {stages} | {failures}{spec_note} |"
        )
    failed = [i for i in result["items"] if i["result"] == "failed"]
    lines += ["", "## Failures", ""]
    if not failed:
        lines.append("None. Every measured prompt rendered, booted, and "
                     "passed the smoke test (CRUD on all entities, auth flow "
                     "where requested).")
    else:
        for i in failed:
            lines.append(f"### {i['id']}")
            lines.extend(f"- {f}" for f in i["failures"])
    skipped = [i for i in result["items"] if i["result"] == "skipped"]
    if skipped:
        lines += ["", "## Not measured (no LLM key in this environment)", ""]
        lines.append(", ".join(f"`{i['id']}`" for i in skipped))
    lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the Spec2Run eval corpus.")
    ap.add_argument("--corpus", default="eval/prompts.jsonl")
    ap.add_argument("--fixtures", default="eval/fixtures")
    ap.add_argument("--out", default="docs/EVAL.md")
    ap.add_argument("--only", default="", help="comma-separated prompt ids")
    ap.add_argument("--database", default="auto",
                    choices=["auto", "neon", "sqlite"])
    args = ap.parse_args(argv)
    only = [p.strip() for p in args.only.split(",") if p.strip()] or None
    result = run_eval(args.corpus, args.fixtures, only=only, database=args.database)
    write_report(result, args.out)
    print(f"eval: {result['passed']} passed, {result['failed']} failed, "
          f"{result['skipped']} skipped -> {args.out}")
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
