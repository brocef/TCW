"""Guards read from the source with `ast` (TCW-73 Design 1.4, 9.1, 9.2; AC 5,
13; plan choice 10).

- No git word in a message a user can see, outside the functions Design 9.2
  exempts: TCW may still read git, and a message about that read says what it
  read.
- Nothing prompts: only `tcw/stdin.py` reads standard input.
- In `tcw/work/open.py`'s messages a name is in single quotes; backticks are
  for a command the user can run.

A string a user can see is approximated as any string constant holding a
space, docstrings excluded. `tcw/serve/` is not read: TCW-77 rewrites it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import tcw

PACKAGE = Path(tcw.__file__).resolve().parent
SOURCES = sorted(p for p in PACKAGE.rglob("*.py") if "serve" not in
                 p.relative_to(PACKAGE).parts)

GIT_WORDS = re.compile(r"\b(git|commit(?:s|ted|ting)?|push(?:es|ed|ing)?|"
                       r"pull(?:s|ed|ing)?|worktrees?|trunks?|"
                       r"branch(?:es|ed|ing)?)\b", re.IGNORECASE)

# (module, qualified name): the functions whose messages may name git.
EXEMPT = {
    ("store/fs.py", "git_root"),                      # finding the repository root
    ("store/fs.py", "FsStoreProvisioner"),            # `tcw provision` clones
    ("cli.py", "run_provision"),
    ("cli.py", "_provision_projects"),
    ("work/open.py", "uncommitted_changes"),          # TCW-70's read-only check
    ("work/open.py", "_check_target"),                # the delegation condition using it
    ("store/project.py", "FsProjectRegistry._other_branch_warning"),
}

WORKTREE_SENTENCE = ("while this worktree has its own at",
                     "is read from another branch than the rest of the graph")


def _docstrings(tree: ast.AST) -> set[int]:
    return {id(node.body[0].value) for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef))
            and node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)}


def _strings(tree: ast.AST):
    """`(qualified scope, line, text)` for each visible string constant."""
    docs = _docstrings(tree)

    def visit(node, scope):
        for child in ast.iter_child_nodes(node):
            here = scope
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                here = (*scope, child.name)
            if isinstance(child, ast.Constant) and isinstance(child.value, str) \
                    and id(child) not in docs and " " in child.value:
                yield ".".join(here), child.lineno, child.value
            yield from visit(child, here)
    yield from visit(tree, ())


def _scopes(tree: ast.AST) -> set[str]:
    found = set()

    def visit(node, scope):
        for child in ast.iter_child_nodes(node):
            here = scope
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                here = (*scope, child.name)
                found.add(".".join(here))
            visit(child, here)
    visit(tree, ())
    return found


def git_word_offenders(module: str, source: str) -> list[str]:
    exempt = [name for mod, name in EXEMPT if mod == module]
    found = []
    for scope, line, text in _strings(ast.parse(source)):
        if any(scope == name or scope.startswith(name + ".") for name in exempt):
            continue
        if GIT_WORDS.search(text):
            found.append(f"{module}:{line} [{scope}] {text!r}")
    return found


def _module(path: Path) -> str:
    return path.relative_to(PACKAGE).as_posix()


def test_no_git_word_outside_the_exempt_functions():
    found = []
    for path in SOURCES:
        found += git_word_offenders(_module(path), path.read_text(encoding="utf-8"))
    assert not found, "\n".join(found)


@pytest.mark.parametrize("module, name", sorted(EXEMPT))
def test_every_exempt_function_still_exists(module, name):
    assert name in _scopes(ast.parse((PACKAGE / module).read_text(encoding="utf-8")))


def test_the_linked_worktree_message_keeps_its_sentence():
    tree = ast.parse((PACKAGE / "store/project.py").read_text(encoding="utf-8"))
    text = " ".join(t for scope, _, t in _strings(tree)
                    if scope == "FsProjectRegistry._other_branch_warning")
    for part in WORKTREE_SENTENCE:
        assert part in text


def test_the_guard_sees_a_git_word_in_the_taxonomy_commands():
    """Mutation check (AC 5): `"run git commit first"` in any `tcw/taxonomy/`
    function is reported."""
    source = (PACKAGE / "taxonomy/cli.py").read_text(encoding="utf-8")
    broken = source.replace("        st.remove(args.path)\n",
                            "        print(\"run git commit first\")\n"
                            "        st.remove(args.path)\n", 1)
    assert broken != source
    assert git_word_offenders("taxonomy/cli.py", broken)


def _reads_stdin(tree: ast.AST) -> list[int]:
    """Lines that call `input()` or reach `sys.stdin`, however `sys` or
    `stdin` was imported (`import sys as s`, `from sys import stdin as x`)."""
    sys_names = {"sys"} | {alias.asname for node in ast.walk(tree)
                           if isinstance(node, ast.Import)
                           for alias in node.names
                           if alias.name == "sys" and alias.asname}
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "input":
            lines.append(node.lineno)
        if isinstance(node, ast.Attribute) and node.attr == "stdin" \
                and isinstance(node.value, ast.Name) and node.value.id in sys_names:
            lines.append(node.lineno)
        if isinstance(node, ast.ImportFrom) and node.module == "sys" \
                and any(alias.name in ("stdin", "*") for alias in node.names):
            lines.append(node.lineno)
    return lines


def test_nothing_but_the_stdin_module_reads_standard_input():
    found = [f"{_module(p)}:{line}" for p in PACKAGE.rglob("*.py")
             if p != PACKAGE / "stdin.py"
             for line in _reads_stdin(ast.parse(p.read_text(encoding="utf-8")))]
    assert not found, found


def test_the_stdin_guard_sees_a_prompt():
    assert _reads_stdin(ast.parse("x = input('name? ')\n"))
    assert _reads_stdin(ast.parse("import sys\nsys.stdin.read()\n"))
    assert _reads_stdin(ast.parse("from sys import stdin\nstdin.read()\n"))
    assert _reads_stdin(ast.parse("from sys import stdin as s\ns.read()\n"))
    assert _reads_stdin(ast.parse("import sys as y\ny.stdin.read()\n"))
    assert not _reads_stdin(ast.parse("proc.stdin.write(b'x')\n"))


def test_the_guard_sees_an_ing_form_of_a_git_word():
    """Review fix S4: "-ing" forms are git words too."""
    for word in ("committing", "pushing", "pulling", "branching"):
        assert git_word_offenders("x.py", f"x = 'do this before {word}'\n"), word


def _backticked_values(source: str) -> list[int]:
    """Lines of f-strings that put a formatted value straight between
    backticks, as a name, where the rule wants single quotes."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.JoinedStr):
            continue
        parts = node.values
        for i, part in enumerate(parts):
            if isinstance(part, ast.FormattedValue) and 0 < i < len(parts) - 1:
                before, after = parts[i - 1], parts[i + 1]
                if isinstance(before, ast.Constant) and str(before.value).endswith("`") \
                        and isinstance(after, ast.Constant) \
                        and str(after.value).startswith("`"):
                    lines.append(node.lineno)
    return lines


def test_names_in_open_py_are_in_single_quotes():
    source = (PACKAGE / "work/open.py").read_text(encoding="utf-8")
    assert _backticked_values(source) == []
    assert _backticked_values('x = f"a `{name}` b"\n')
