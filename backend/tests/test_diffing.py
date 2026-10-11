from app.services.diffing import diff_files, diff_specs

MINIMAL_OLD = {"openapi": "3.0.0", "info": {"title": "x", "version": "1"}}


def test_diff_specs_changed_leaf():
    old = {"info": {"title": "x", "version": "1"}, "paths": {}}
    new = {"info": {"title": "y", "version": "1"}, "paths": {}}
    changes = diff_specs(old, new)
    assert changes == [
        {"path": "info.title", "old_value": "x", "new_value": "y"}
    ]


def test_diff_specs_added_and_removed_keys():
    old = {"info": {"title": "x"}}
    new = {"info": {"version": "1"}}
    changes = diff_specs(old, new)
    assert {"path": "info.title", "old_value": "x", "new_value": None} in changes
    assert {"path": "info.version", "old_value": None, "new_value": "1"} in changes


def test_diff_specs_list_indices():
    old = {"tags": ["a", "b"]}
    new = {"tags": ["a", "c", "d"]}
    changes = diff_specs(old, new)
    assert {"path": "tags[1]", "old_value": "b", "new_value": "c"} in changes
    assert {"path": "tags[2]", "old_value": None, "new_value": "d"} in changes


def test_diff_specs_identical_is_empty():
    doc = {"info": {"title": "x"}, "paths": {"/a": {"get": {}}}}
    assert diff_specs(doc, doc) == []


def test_diff_files_unified_format():
    old = {"app.py": "a = 1\nb = 2\n"}
    new = {"app.py": "a = 1\nb = 3\n"}
    diffs = diff_files(old, new)
    assert list(diffs) == ["app.py"]
    d = diffs["app.py"]
    assert "--- a/app.py" in d and "+++ b/app.py" in d
    assert "-b = 2" in d and "+b = 3" in d


def test_diff_files_added_removed():
    diffs = diff_files({"a.py": "x"}, {"b.py": "y"})
    assert set(diffs) == {"a.py", "b.py"}
    assert "@@" in diffs["a.py"] and "@@" in diffs["b.py"]


def test_diff_files_identical_skipped():
    files = {"app.py": "print(1)\n", "requirements.txt": "fastapi\n"}
    assert diff_files(files, dict(files)) == {}
