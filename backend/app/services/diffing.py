"""Spec + code diffing for the versioning flow.

"Add reviews to books" patches the stored spec rather than regenerating it.
This module diffs old vs new spec (as structured JSON changes) and old vs
new rendered files (as unified diffs) for the frontend's git-style diff view.
"""

import difflib


def _walk(old, new, path: str, changes: list[dict]) -> None:
    if isinstance(old, dict) and isinstance(new, dict):
        for key in old:
            child = f"{path}.{key}" if path else str(key)
            if key not in new:
                changes.append(
                    {"path": child, "old_value": old[key], "new_value": None}
                )
            else:
                _walk(old[key], new[key], child, changes)
        for key in new:
            if key not in old:
                child = f"{path}.{key}" if path else str(key)
                changes.append(
                    {"path": child, "old_value": None, "new_value": new[key]}
                )
    elif isinstance(old, list) and isinstance(new, list):
        for i, (a, b) in enumerate(zip(old, new)):
            _walk(a, b, f"{path}[{i}]", changes)
        if len(old) > len(new):
            for i in range(len(new), len(old)):
                changes.append(
                    {"path": f"{path}[{i}]", "old_value": old[i], "new_value": None}
                )
        elif len(new) > len(old):
            for i in range(len(old), len(new)):
                changes.append(
                    {"path": f"{path}[{i}]", "old_value": None, "new_value": new[i]}
                )
    elif old != new:
        changes.append({"path": path, "old_value": old, "new_value": new})


def diff_specs(old: dict, new: dict) -> list[dict]:
    """List {path, old_value, new_value} for every changed key between specs.

    Paths are dotted with [n] for list indices. A None value means the key
    was absent on that side. Leaf-only: a changed subtree reports every
    changed leaf, not the whole subtree.
    """
    changes: list[dict] = []
    _walk(old or {}, new or {}, "", changes)
    return changes


def diff_files(old: dict[str, str], new: dict[str, str]) -> dict[str, str]:
    """Return {relative_path: unified_diff} for added, removed, changed files.

    Identical files are skipped, so an empty dict means nothing changed.
    """
    diffs: dict[str, str] = {}
    for path in sorted(set(old) | set(new)):
        a, b = old.get(path), new.get(path)
        if a == b:
            continue
        lines = difflib.unified_diff(
            [] if a is None else a.splitlines(),
            [] if b is None else b.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
        diffs[path] = "\n".join(lines)
    return diffs
