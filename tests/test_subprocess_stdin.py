"""Every subprocess TCW launches must say what its stdin is.

An inherited file descriptor is how a child ends up reading input nobody gave
it — the caller's piped intake, or an open pipe it will wait on forever. The
five intake commands were fixed by `tcw/stdin.py`, and lifecycle hooks by
`stdin=DEVNULL`; this is the check that keeps the twenty-second call site from
reintroducing it.

It asserts **explicitness**, not one particular value: `tcw/work/generate.py`
passes `stdin=subprocess.PIPE` on purpose, because writing the payload is the
`generate:` contract. What is banned is saying nothing and inheriting.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "tcw"
SOURCES = sorted(PACKAGE.rglob("*.py"))


def _spawning_calls(path: Path):
    """(line, rendered-first-arg, sets_stdin) for each subprocess spawn."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if ast.unparse(node.func) not in ("subprocess.run", "subprocess.Popen"):
            continue
        yield (node.lineno,
               ast.unparse(node.args[0])[:60] if node.args else "?",
               any(k.arg == "stdin" for k in node.keywords))


def test_the_walk_actually_finds_the_spawns_it_should():
    """Guards the guard. An AST walk that silently matched nothing would make
    every assertion below pass while checking nothing — so this pins both a
    floor and two call sites known to exist by name.

    The floor is deliberately low: `tcw/store/fs.py` routes nineteen git calls
    through one `_git` helper, so a high count would fail for a good reason."""
    found = {p.name: list(_spawning_calls(p)) for p in SOURCES}
    assert sum(len(v) for v in found.values()) >= 5
    assert found.get("generate.py"), "the generate hook spawns a process"
    assert found.get("hooks.py"), "lifecycle command hooks spawn a process"


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_every_subprocess_declares_its_stdin(path):
    inherited = [f"{path.name}:{line} {arg}"
                 for line, arg, sets in _spawning_calls(path) if not sets]
    assert not inherited, (
        "these inherit the caller's stdin — pass stdin=subprocess.DEVNULL "
        "(or PIPE where the payload is written):\n  " + "\n  ".join(inherited))
