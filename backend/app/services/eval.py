"""Eval harness: does Spec2Run actually work? Measured, not claimed.

Corpus: backend/eval/prompts.jsonl (target: 50 prompts).
For each prompt: generate the spec -> validate the OpenAPI structurally ->
render the code -> boot a sandbox -> smoke-test every endpoint, including
the auth flow when the spec asks for it. Results go to docs/EVAL.md as a
markdown table, failures included with reasons. Runs on demand, not per
push, to spare Groq quota.
"""


def run_eval(corpus: str = "eval/prompts.jsonl") -> dict:
    """Run the full corpus; returns {passed, failed, failures: [...]}."""
    raise NotImplementedError  # week 3
