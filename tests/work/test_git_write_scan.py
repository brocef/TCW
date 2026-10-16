"""TCW never runs a git command that writes (TCW-70 AC 12, the scan).

Looks at git invocations, not at words: a list or tuple literal whose first
element is `"git"`. Options are skipped: any `-x` or `--x`, and, for the
options that take their value as the next element (`-C`, `-c`, `--git-dir`,
`--work-tree`, `--namespace`), that value too, so `-c key=value` is never
read as the verb. Values that are not string literals (a path) are skipped,
and the first string literal left is the verb. When the verb arrives through
`*args`, the calls to the enclosing function in the same file supply it. The
moved Jira client is not scanned: its text says "add" and "comment" about
HTTP calls.

Allowances name the method the literal sits in, as `Class.method`, never a
file or a whole class:

- `FsStoreProvisioner._obtain`, for `tcw provision`: `clone`, and `checkout`
  of the declared ref in the fresh clone. Since TCW-73 it never fetches into
  or merges an existing checkout (its Design 8.4: `--refresh` is gone).

Nothing else: since TCW-73 the taxonomy and capabilities stores write files
and stage nothing, and the scan covers their CLI modules too.

Every `status` call also keeps `--no-optional-locks` before the verb, so that
reading the state never refreshes the index or takes `index.lock`, which is a
write to someone else's repository.
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
           "worktree remove", "switch", "restore", "rebase", "cherry-pick",
           "update-ref", "update-index", "init", "branch"}
ALLOWED = {
    "FsStoreProvisioner._obtain": {"clone", "checkout"},
}
# git's options that take their value as the next element.
WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def _verb(elements):
    """The verb in what follows `"git"`, `"*"` for a `*args` tail, or None."""
    rest = list(elements)
    i = 0
    while i < len(rest):
        e = rest[i]
        if isinstance(e, ast.Starred):
            return "*"
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            if e.value in WITH_VALUE:
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


def _methods(node, parents):
    """`Class.method` for each function enclosing `node` whose own enclosing
    scope is a class: what an allowance is keyed on."""
    scopes = []
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            scopes.append(node)
    return {f"{outer.name}.{inner.name}" for inner, outer in zip(scopes, scopes[1:])
            if isinstance(outer, ast.ClassDef)
            and isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _git_literals(tree):
    """Every list or tuple literal whose first element is `"git"`."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)) and node.elts:
            head = node.elts[0]
            if isinstance(head, ast.Constant) and head.value == "git":
                yield node


def git_writes(path: Path, source: str | None = None) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8") if source is None else source)
    parents = _parents(tree)
    found = []
    for node in _git_literals(tree):
        owners = _owners(node, parents)
        methods = _methods(node, parents)
        verb = _verb(node.elts[1:])
        verbs = [verb]
        if verb == "*" and owners:
            # The verb comes from the enclosing function's callers.
            function = owners[0]
            verbs = [_verb(call.args[1:]) for call in ast.walk(tree)
                     if isinstance(call, ast.Call)
                     and isinstance(call.func, ast.Name) and call.func.id == function]
        for v in verbs:
            if v in WRITERS and not any(v in ALLOWED.get(m, ()) for m in methods):
                found.append(f"{_shown(path)}:{node.lineno}: git {v} "
                             f"(in {' < '.join(owners) or 'module'})")
    return found


def _shown(path: Path) -> str:
    return str(path.relative_to(PACKAGE)) if PACKAGE in path.parents else path.name


def status_without_optional_locks(path: Path, source: str | None = None) -> list[str]:
    """Each `git ... status` literal with no `--no-optional-locks` before the
    verb."""
    tree = ast.parse(path.read_text(encoding="utf-8") if source is None else source)
    found = []
    for node in _git_literals(tree):
        if _verb(node.elts[1:]) != "status":
            continue
        before = []
        for e in node.elts[1:]:
            if isinstance(e, ast.Constant) and e.value == "status":
                break
            before.append(e)
        if not any(isinstance(e, ast.Constant) and e.value == "--no-optional-locks"
                   for e in before):
            found.append(f"{_shown(path)}:{node.lineno}: git status without "
                         f"--no-optional-locks")
    return found


def test_the_scan_reads_every_spelling():
    """Guards the reader: each spelling the code uses resolves to its verb."""
    cases = {
        '["git", "-C", str(r), "add", "x"]': "add",
        '["git", "--no-optional-locks", "-C", str(r), "status"]': "status",
        '["git", "--git-dir", str(r), "config", "--get", "x"]': "config",
        '["git", "worktree", "add", p]': "worktree add",
        '["git", "-c", "a=b", "switch", "x"]': "switch",
        '["git", "--git-dir", "d", "--work-tree", "w", "restore", "x"]': "restore",
        '["git", "--namespace", "n", "-C", "r", "branch", "-D", "x"]': "branch",
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


# -- the pre-freeze clean-up's widening (C3) -------------------------------------------------


@pytest.mark.parametrize("verb", ["switch", "restore", "rebase", "cherry-pick",
                                  "update-ref", "update-index", "init", "branch"])
def test_each_added_verb_is_reported(verb):
    source = f'def f(r):\n    return ["git", "-C", r, "{verb}", "x"]\n'
    [found] = git_writes(Path("planted.py"), source)
    assert f"git {verb} (in f)" in found


def test_the_allowance_covers_only_the_one_method():
    """`clone` and `checkout` are allowed in `FsStoreProvisioner._obtain`, and
    nowhere else in the class."""
    source = (
        "class FsStoreProvisioner:\n"
        "    def _obtain(self, url, d):\n"
        "        self._run([\"git\", \"clone\", url, d])\n"
        "        self._run([\"git\", \"-C\", d, \"checkout\", \"main\"])\n"
        "    def other(self, url, d):\n"
        "        self._run([\"git\", \"clone\", url, d])\n")
    found = git_writes(Path("planted.py"), source)
    assert found == ["planted.py:6: git clone (in other < FsStoreProvisioner)"]


def test_the_real_allowance_is_where_the_clone_is():
    """`_obtain` is still the method that clones, so the allowance names a
    method that exists."""
    tree = ast.parse((PACKAGE / "store" / "fs.py").read_text(encoding="utf-8"))
    parents = _parents(tree)
    clones = [_methods(node, parents) for node in _git_literals(tree)
              if _verb(node.elts[1:]) == "clone"]
    assert clones == [{"FsStoreProvisioner._obtain"}]


def test_status_without_optional_locks_is_reported():
    source = 'def f(r):\n    return ["git", "-C", r, "status", "--porcelain"]\n'
    assert status_without_optional_locks(Path("planted.py"), source) == [
        "planted.py:2: git status without --no-optional-locks"]
    after = 'def f(r):\n    return ["git", "-C", r, "status", "--no-optional-locks"]\n'
    assert status_without_optional_locks(Path("planted.py"), after)


def test_the_status_check_sees_the_real_calls():
    """If it stopped finding `status` calls, the test below would pass by
    seeing nothing."""
    statuses = [node for path in SCANNED
                for node in _git_literals(ast.parse(path.read_text(encoding="utf-8")))
                if _verb(node.elts[1:]) == "status"]
    assert len(statuses) >= 2


@pytest.mark.parametrize("path", SCANNED, ids=lambda p: str(p.relative_to(PACKAGE)))
def test_every_status_keeps_no_optional_locks(path):
    assert status_without_optional_locks(path) == []
