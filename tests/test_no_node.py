"""No "node" under `tcw/` (TCW-73 Design 9.3; AC 6).

3.0 calls a TCW project a project, and a term or capability folder an entry.
Every occurrence of `node`, in code, strings, comments and docstrings alike and
as part of any identifier, is reported unless it is one of the senses that are
not TCW's to rename: "inode", PyYAML's node classes, the phrase "YAML node",
or a line inside a function on `KEPT`. `tcw/serve/` is not read: TCW-77
rewrites it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import tcw

PACKAGE = Path(tcw.__file__).resolve().parent
SOURCES = sorted(p for p in PACKAGE.rglob("*.py")
                 if "serve" not in p.relative_to(PACKAGE).parts)

ALLOWED = re.compile(r"inodes?|ScalarNode|MappingNode|SequenceNode|YAML node",
                     re.IGNORECASE)
NODE = re.compile(r"node", re.IGNORECASE)

# (module, qualified function): the functions that hold a node in a sense that
# is not a project's. Each must exist and must show which sense it holds.
YAML_FUNCTIONS = {
    ("store/project.py", "_unique_mapping"),
    ("store/fs.py", "_no_dup_keys"),
    ("store/config_edit.py", "_Document.end_of"),
    ("store/config_edit.py", "_Document.is_null"),
}
JIRA_DOCUMENT_FUNCTIONS = {
    ("work/jira/mapping.py", name)
    for name in ("text_document", "_children", "_inline_text", "_block_text",
                 "document_text")
}
KEPT = YAML_FUNCTIONS | JIRA_DOCUMENT_FUNCTIONS
YAML_MARKS = ("ScalarNode", "MappingNode", "SequenceNode", "construct_object")


def _functions(tree: ast.AST) -> dict[str, ast.AST]:
    found = {}

    def visit(node, scope):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                here = (*scope, child.name)
                found[".".join(here)] = child
                visit(child, here)
            else:
                visit(child, scope)
    visit(tree, ())
    return found


def offenders(module: str, source: str) -> list[str]:
    kept_lines = set()
    for name, function in _functions(ast.parse(source)).items():
        if (module, name) in KEPT:
            start = min([d.lineno for d in getattr(function, "decorator_list", [])]
                        + [function.lineno])
            kept_lines.update(range(start, function.end_lineno + 1))
    return [f"{module}:{number}: {line.strip()}"
            for number, line in enumerate(source.splitlines(), 1)
            if number not in kept_lines and NODE.search(ALLOWED.sub("", line))]


def _module(path: Path) -> str:
    return path.relative_to(PACKAGE).as_posix()


def test_no_node_under_tcw():
    found = []
    for path in SOURCES:
        found += offenders(_module(path), path.read_text(encoding="utf-8"))
    assert not found, "\n".join(found)


@pytest.mark.parametrize("module, name", sorted(KEPT))
def test_each_kept_function_exists_and_shows_its_sense(module, name):
    source = (PACKAGE / module).read_text(encoding="utf-8")
    function = _functions(ast.parse(source)).get(name)
    assert function is not None, f"{module}: {name} is gone; take it off KEPT"
    if (module, name) in YAML_FUNCTIONS:
        text = ast.get_source_segment(source, function)
        assert any(mark in text for mark in YAML_MARKS), \
            f"{module}: {name} names no PyYAML node class; take it off KEPT"


def test_the_project_root_variable_is_gone():
    assert not any("TCW_NODE_ROOT" in p.read_text(encoding="utf-8")
                   for p in PACKAGE.rglob("*.py"))


def test_the_guard_sees_a_node():
    """Mutation check: the words the spec names fail the test."""
    for line in ("node_root = None\n", "x = find_node()\n",
                 "# the node's `tcw-config.yaml`\n", "NODE_TARGET = 'x'\n"):
        assert offenders("taxonomy/cli.py", line)
    for line in ("# an inode number\n", "x: yaml.ScalarNode\n", "# a YAML node\n"):
        assert not offenders("taxonomy/cli.py", line)
