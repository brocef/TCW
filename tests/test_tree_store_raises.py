"""The tree stores raise the exit classes, never a bare `ValueError` (TCW-73
Design 4; AC 25).

Read from the source with `ast` rather than by provoking each failure: a
failure no test provokes is exactly the one that would slip back to
`ValueError` and exit 1 where Design 4's table says 2, 3 or 4.

The region checked runs from `_revision` to the end of `FsCapabilitiesStore`:
the shared tree-store code, both stores and the module functions between
them. Besides the four exit classes it allows the reference errors (which are
`NotFound` and `UsageError` themselves), `StaleRevision` (a conflict the web
viewer answers with its own status, not a CLI exit) and
`StoreLocationUnusable` (a store-opening error, raised before any operation).
"""

import ast
from pathlib import Path

import tcw

FS = Path(tcw.__file__).resolve().parent / "store" / "fs.py"

ALLOWED = {"NotFound", "UsageError", "Refused", "BackendError", "RefError",
           "AmbiguousRef", "StaleRevision", "StoreLocationUnusable"}


def _region(tree: ast.Module) -> list[ast.stmt]:
    names = [getattr(node, "name", None) for node in tree.body]
    start = names.index("_revision")
    end = names.index("FsCapabilitiesStore")
    return tree.body[start:end + 1]


def _raised(node: ast.Raise) -> str | None:
    """The class a `raise` names, or None for a bare re-raise."""
    if node.exc is None:
        return None
    target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return ast.unparse(target)


def offenders(source: str) -> list[str]:
    tree = ast.parse(source)
    found = []
    for top in _region(tree):
        for node in ast.walk(top):
            if isinstance(node, ast.Raise):
                name = _raised(node)
                if name is not None and name not in ALLOWED:
                    found.append(f"fs.py:{node.lineno}: raise {name}")
    return found


def test_the_region_is_found():
    region = _region(ast.parse(FS.read_text(encoding="utf-8")))
    names = {getattr(node, "name", None) for node in region}
    assert {"FsTreeStore", "FsTaxonomyStore", "FsCapabilitiesStore"} <= names


def test_every_raise_is_an_exit_class():
    assert offenders(FS.read_text(encoding="utf-8")) == []


def test_the_check_sees_a_value_error():
    """The guard itself: a `ValueError` put back is reported."""
    source = FS.read_text(encoding="utf-8").replace(
        'raise NotFound(f"no such capability: {path}")',
        'raise ValueError(f"no such capability: {path}")', 1)
    assert len(offenders(source)) == 1
