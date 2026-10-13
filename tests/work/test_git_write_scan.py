"""TCW never runs a git command that writes (TCW-70 AC 12, the scan).

Looks at git invocations, not at words: a list or tuple literal whose first
element is `"git"`. Options (`-C <path>`, `--no-optional-locks`, any `-x`) and
values that are not string literals (a path) are skipped, and the first string
literal left is the verb. When the verb arrives through `*args`, the calls to
the enclosing function in the same file supply it. The moved Jira client is
not scanned: its text says "add" and "comment" about HTTP calls.

Allowances name the class or function the literal sits in, never a file:

- `FsStoreProvisioner`, for `tcw provision`: `clone`, and `checkout` of the
  declared ref in the fresh clone. Since TCW-73 it never fetches into or
  merges an existing checkout (its Design 8.4: `--refresh` is gone).

Nothing else: since TCW-73 the taxonomy and capabilities stores write files
and stage nothing, and the scan covers their CLI modules too.
"""

import ast
from pathlib import Path

import pytest

import tcw

PACKAGE = Path(tcw.__file__).resolve().parent
SCANNED = sorted([*(PACKAGE / "work").rglob("*.py"), PACKAGE / "validate.py",
                  PACKAGE / "refs.py", PACKAGE / "capabilities" / "cli.py",
                  PACKAGE / "taxonomy" / "cli.py", PACKAGE / "cli.py",
                  *(PACKAGE / "store").rglob("*.py")])
SCANNED = [p for p in SCANNED if (PACKAGE / "work" / "jira") not in p.parents]

WRITERS = {"add", "commit", "mv", "rm", "reset", "checkout", "merge", "push",
           "pull", "fetch", "stash", "tag", "clone", "worktree add",
           "worktree remove"}
ALLOWED = {
    "FsStoreProvisioner": {"clone", "checkout"},
}


def _verb(elements):
    """The verb in what follows `"git"`, `"*"` for a `*args` tail, or None."""
    rest = list(elements)
    i = 0
    while i < len(rest):
        e = rest[i]
        if isinstance(e, ast.Starred):
            return "*"
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            if e.value == "-C":
                i += 2
                continue
            if e.value.startswith("-"):
                i += 1
                continue
            verb = e.value
            nxt = rest[i + 1] if i + 1 < len(rest) else None
            if verb == "worktree" and isinstance(nxt, ast.Constant):
                return f"worktree {nxt.value}"
            return verb
        i += 1                     # a path or other computed value
    return None


def _parents(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _owners(node, parents):
    """The names of every class and function enclosing `node`."""
    out = []
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(node.name)
    return out


def git_writes(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents = _parents(tree)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple)) or not node.elts:
            continue
        head = node.elts[0]
        if not (isinstance(head, ast.Constant) and head.value == "git"):
            continue
        owners = _owners(node, parents)
        verb = _verb(node.elts[1:])
        verbs = [verb]
        if verb == "*" and owners:
            # The verb comes from the enclosing function's callers.
            function = owners[0]
            verbs = [_verb(call.args[1:]) for call in ast.walk(tree)
                     if isinstance(call, ast.Call)
                     and isinstance(call.func, ast.Name) and call.func.id == function]
        for v in verbs:
            if v in WRITERS and not any(v in ALLOWED.get(o, ()) for o in owners):
                found.append(f"{path.relative_to(PACKAGE)}:{node.lineno}: git {v} "
                             f"(in {' < '.join(owners) or 'module'})")
    return found


def test_the_scan_reads_every_spelling():
    """Guards the reader: each spelling the code uses resolves to its verb."""
    cases = {
        '["git", "-C", str(r), "add", "x"]': "add",
        '["git", "--no-optional-locks", "-C", str(r), "status"]': "status",
        '["git", "--git-dir", str(r), "config", "--get", "x"]': "config",
        '["git", "worktree", "add", p]': "worktree add",
    }
    for source, verb in cases.items():
        literal = ast.parse(source).body[0].value
        assert _verb(literal.elts[1:]) == verb, source


def test_the_scan_sees_the_allowed_writes():
    """If the scan stopped finding git literals, the test below would pass by
    seeing nothing. With the allowances emptied it must find the known ones."""
    saved = dict(ALLOWED)
    ALLOWED.clear()
    try:
        found = git_writes(PACKAGE / "store" / "fs.py")
    finally:
        ALLOWED.update(saved)
    assert any("git clone" in f and "FsStoreProvisioner" in f for f in found)


@pytest.mark.parametrize("path", SCANNED, ids=lambda p: str(p.relative_to(PACKAGE)))
def test_no_git_write(path):
    assert git_writes(path) == []
