"""The viewer's wording (TCW-77 criterion 18).

3.0 calls a TCW project a project, never a node. No Python string literal
under `tcw/serve/`, and no line of the viewer's guide, matches the
case-sensitive `\\bnodes?\\b`; "Node.js" is still allowed where it names the
JavaScript runtime. The guide says TCW "never changes git state", not that it
never runs git, which it does to read the repository. That the release
entries start with a `##` heading is `tests/test_upcoming_entries.py`'s check,
over every entry, since a version cut deletes them.
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


# -- the guide ------------------------------------------------------------------

REPO = Path(tcw.__file__).resolve().parent.parent
GUIDE = REPO / "docs" / "guide" / "web-viewer.md"


def test_no_guide_line_says_node():
    hits = [f"{number}: {line}"
            for number, line in enumerate(GUIDE.read_text().splitlines(), 1)
            if NODE.search(line)]
    assert not hits, "\n".join(hits)


def test_the_guide_says_git_state_is_never_changed():
    text = " ".join(GUIDE.read_text().split())
    assert "never changes git state" in text
    assert "never runs git" not in text

