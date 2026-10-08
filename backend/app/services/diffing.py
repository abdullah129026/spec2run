"""Spec + code diffing for the versioning flow.

"Add reviews to books" produces a JSON patch against the stored spec, not a
regeneration. This module diffs old vs new spec (as structured JSON diffs)
and old vs new rendered files (as unified diffs) for the frontend's
git-style diff view.
"""


def diff_specs(old: dict, new: dict) -> list[dict]:
    """Return a list of {path, old_value, new_value} changes between specs."""
    raise NotImplementedError  # week 2


def diff_files(old: dict[str, str], new: dict[str, str]) -> dict[str, str]:
    """Return {relative_path: unified_diff} for changed rendered files."""
    raise NotImplementedError  # week 2
