"""The sweep of TCW-111 (AC 21), kept swept: the TCW 3.x state file names
appear only where `tcw/object_folders.py` keeps them, and every directory
listing in TCW's own code is one whose reason is written down here, so the
walk stays the only code that lists a store to find its objects (Design 2.5).

The scan is one function of a root folder, `offenders(root)`, so a later
change can run it over a copy of the repository; `MIGRATION_FOLDERS` names
the folders the 3.x-name check leaves out, and is empty until `tcw migrate`
(TCW-116), which reads 3.x files by their names, arrives.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: The folders scanned, and the file suffixes in them.
SCANNED = ("tcw", "web/client/src", "scripts", "evals")
SUFFIXES = (".py", ".ts", ".tsx", ".mjs")
#: Never scanned: the built web client, and test files.
EXCEPTED = ("tcw/serve/dist",)

#: The 3.x names, which only `tcw/object_folders.py` spells.
THREE_X = re.compile(r"(?<![\w-])(?:meta|item)\.yaml|ITEM_FILE")
NAMES_KEPT_IN = "tcw/object_folders.py"
#: Folders the 3.x-name check leaves out. Empty: TCW-116 adds `tcw migrate`'s.
MIGRATION_FOLDERS: tuple[str, ...] = ()

#: The directory listings, by the method or function called.
LISTING_METHODS = {"iterdir", "rglob", "glob", "scandir", "listdir", "walk"}
LISTING_TEXT = re.compile(r"\.iterdir\(|\.rglob\(|\.glob\(|os\.listdir\(|os\.scandir\(|"
                          r"os\.walk\(|readdirSync\(|readdir\(")

#: Every listing allowed, as `(file, enclosing function)`, with the reason it
#: is not a listing of a store's objects.
ALLOWED = {
    ("tcw/object_folders.py", "_entries"):
        "the walk's own listing of one folder: the one code that finds objects",
    ("tcw/object_folders.py", "exact_child"):
        "TCW-110's listing of one folder, to compare a name's spelling",
    ("tcw/object_folders.py", "removal_blockers"):
        "the checks before a removal search everything it would delete",
    ("tcw/validate.py", "_iter"):
        "the YAML and link scans read every file, whatever object holds it",
    ("tcw/work/resolve.py", "_load_texts"):
        "the package's own prompt files",
    ("tcw/work/fs_backend.py", "report_mentions"):
        "every file's text after a rename, for mentions, not objects",
    ("tcw/work/fs_backend.py", "create"):
        "create's rollback of the one folder it made",
    ("tcw/work/fs_backend.py", "read_comments"):
        "one item's comments/ folder",
    ("tcw/work/layout.py", "rounds"):
        "one stage folder's round files",
    ("tcw/work/layout.py", "latest_handoff"):
        "one stage folder's handoff files",
    ("tcw/serve/files.py", "_handoffs"):
        "one stage folder's handoff files",
    ("tcw/store/project.py", "_list_folder"):
        "the project registry's search for project folders, not store objects",
    ("tcw/store/fs.py", "init"):
        "whether a default store folder is empty before init scaffolds one",
    ("tcw/store/fs.py", "_rm"):
        "the files a removal deletes, to name each one",
    ("tcw/store/fs.py", "_resource_files"):
        "one object's resources/ folder: its attachments",
    ("evals/coverage.py", "shipped_skills"):
        "the plugin's skill folders",
    ("evals/grade.py", "rounds"):
        "an eval run's own output folders",
    ("evals/grade.py", "main"):
        "an eval run's own output folders",
    ("evals/seed_fixture.py", "seed"):
        "whether a destination folder is empty",
    ("scripts/cut_version.py", "combine_upcoming"):
        "the upcoming/ release-note entry files",
}


def _files(root: Path):
    for top in SCANNED:
        for path in sorted((root / top).rglob("*")):
            rel = path.relative_to(root).as_posix()
            if path.suffix not in SUFFIXES or not path.is_file():
                continue
            if any(rel.startswith(e + "/") for e in EXCEPTED):
                continue
            if "/tests/" in f"/{rel}" or path.name.startswith("test_") \
                    or ".test." in path.name:
                continue
            yield rel, path


def _listings(source: str) -> list[tuple[int, str]]:
    """`(line, enclosing function)` of each directory listing in a Python
    source: a call of one of `LISTING_METHODS` as an attribute."""
    tree = ast.parse(source)
    found = []

    def visit(node: ast.AST, function: str) -> None:
        for child in ast.iter_child_nodes(node):
            inner = child.name if isinstance(child, (ast.FunctionDef,
                                                     ast.AsyncFunctionDef)) else function
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) \
                    and child.func.attr in LISTING_METHODS:
                found.append((child.lineno, function))
            visit(child, inner)
    visit(tree, "<module>")
    return found


def offenders(root: Path) -> list[str]:
    """Every 3.x name outside its one place, and every directory listing not
    in `ALLOWED`, under `root`, as `<file>:<line>: <what>`."""
    found = []
    for rel, path in _files(root):
        text = path.read_text(encoding="utf-8")
        if rel != NAMES_KEPT_IN and not any(rel.startswith(m + "/")
                                            for m in MIGRATION_FOLDERS):
            for number, line in enumerate(text.splitlines(), start=1):
                if THREE_X.search(line):
                    found.append(f"{rel}:{number}: names a TCW 3.x state file")
        if path.suffix == ".py":
            for number, function in _listings(text):
                if (rel, function) not in ALLOWED:
                    found.append(f"{rel}:{number}: lists a folder in {function}")
        else:
            for number, line in enumerate(text.splitlines(), start=1):
                if LISTING_TEXT.search(line):
                    found.append(f"{rel}:{number}: lists a folder")
    return found


def test_the_tree_is_swept():
    assert offenders(REPO) == []


def test_every_allowed_listing_still_exists():
    """An entry whose listing has gone is removed, so the list stays a list
    of reasons for code that is there."""
    seen = set()
    for rel, path in _files(REPO):
        if path.suffix == ".py":
            seen |= {(rel, function) for _, function in
                     _listings(path.read_text(encoding="utf-8"))}
    assert set(ALLOWED) - seen == set()


def test_the_3x_names_are_kept_only_as_legacy_names():
    from tcw.object_folders import LEGACY_STATE_FILES
    text = (REPO / NAMES_KEPT_IN).read_text(encoding="utf-8")
    lines = text.splitlines()
    named = [n for n, line in enumerate(lines) if THREE_X.search(line)]
    start = next(n for n, line in enumerate(lines)
                 if line.startswith("LEGACY_STATE_FILES = {"))
    assert named == [start, start + 1]
    assert set(LEGACY_STATE_FILES.values()) == {"meta.yaml", "item.yaml"}
