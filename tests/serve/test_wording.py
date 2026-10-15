"""The viewer's wording (TCW-77 criterion 18).

3.0 calls a TCW project a project, never a node. No Python string literal
under `tcw/serve/` matches the case-sensitive `\\bnodes?\\b`, so a message the
server sends never says it; "Node.js" is still allowed where it names the
JavaScript runtime.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import tcw

SERVE = Path(tcw.__file__).resolve().parent / "serve"
NODE = re.compile(r"\bnodes?\b")


def literals(source: str) -> list[tuple[int, str]]:
    return [(node.lineno, node.value) for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)]


@pytest.mark.parametrize("path", sorted(SERVE.rglob("*.py")),
                         ids=lambda p: p.name)
def test_no_server_string_says_node(path):
    hits = [f"{path.name}:{line}: {text!r}"
            for line, text in literals(path.read_text()) if NODE.search(text)]
    assert not hits, "\n".join(hits)


def test_the_pattern_finds_node_and_passes_nodejs():
    assert NODE.search("each node of the graph")
    assert NODE.search("nodes")
    assert not NODE.search("Node.js 20 builds the client")
    assert not NODE.search("an inode")
