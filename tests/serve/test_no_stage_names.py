"""The viewer names no stage (TCW-77 Design 13; criterion 14).

Stage names, their order, and which stage keeps which files come from the
project's stage table, which the server reads from TCW-69's model and the
client from `/api/project`. A literal stage name in either half would make the
viewer follow its own idea of the lifecycle instead of the project's, so no
string literal in `tcw/serve/` or in the client's source may equal a name in
`STAGES` or hold one as a path segment (`"plan/plan.md"`).

Tests, docstrings and comments are not read. The client is scanned with a
small tokenizer for string and template literals rather than a TypeScript
parser, so the check needs no Node; `test_scanner_*` below plant literals to
show it finds what it should and passes what it should.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import tcw
from tcw.work.model import STAGES

PACKAGE = Path(tcw.__file__).resolve().parent
SERVE = PACKAGE / "serve"
CLIENT = PACKAGE.parent / "web" / "client" / "src"
NAMES = frozenset(stage.name for stage in STAGES)


def names_a_stage(text: str) -> bool:
    """True when `text` is a stage name or holds one as a `/` segment."""
    return any(segment in NAMES for segment in text.split("/"))


# -- the server: Python string constants, docstrings excepted ------------------

def _docstrings(tree: ast.AST) -> set[int]:
    return {id(node.body[0].value) for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef))
            and node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)}


def python_literals(source: str) -> list[tuple[int, str]]:
    tree = ast.parse(source)
    docs = _docstrings(tree)
    return [(node.lineno, node.value) for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and id(node) not in docs]


# -- the client: string and template literals, comments skipped ----------------

# After one of these (or at the start), a `/` begins a regular expression.
# `<` is left out so that a JSX closing tag, `</Text>`, is not read as one.
_REGEX_AFTER = set("(,=:[!&|?{};+-*%~^")
_WORD = re.compile(r"[A-Za-z0-9_$]")


def client_literals(source: str) -> list[tuple[int, str]]:
    """`(line, text)` for each quoted and template literal in TypeScript
    source. A template's `${...}` parts are left out and each fixed part
    between them is a literal of its own. A quote straight
    after a word character is JSX text's apostrophe ("project's"), not a
    string; a quoted literal ends at a newline, which also resynchronises
    the scan after any text it misread."""
    found: list[tuple[int, str]] = []
    i, line, n = 0, 1, len(source)
    last = ""  # the last character that was not white space, outside literals
    while i < n:
        c = source[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if source.startswith("//", i):
            while i < n and source[i] != "\n":
                i += 1
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            end = n if end == -1 else end + 2
            line += source.count("\n", i, end)
            i = end
            continue
        if c in "'\"" and not (i and _WORD.match(source[i - 1])):
            j, text = i + 1, []
            while j < n and source[j] not in (c, "\n"):
                if source[j] == "\\" and j + 1 < n:
                    text.append(source[j + 1])
                    j += 2
                    continue
                text.append(source[j])
                j += 1
            if j < n and source[j] == c:
                found.append((line, "".join(text)))
                i = j + 1
                last = c
            else:
                i = j
            continue
        if c == "`":
            j, part, start = i + 1, [], line
            while j < n and source[j] != "`":
                if source[j] == "\\" and j + 1 < n:
                    part.append(source[j + 1])
                    j += 2
                    continue
                if source.startswith("${", j):
                    found.append((start, "".join(part)))
                    part, depth, j = [], 1, j + 2
                    while j < n and depth:
                        depth += {"{": 1, "}": -1}.get(source[j], 0)
                        line += source[j] == "\n"
                        j += 1
                    start = line
                    continue
                line += source[j] == "\n"
                part.append(source[j])
                j += 1
            found.append((start, "".join(part)))
            i, last = j + 1, "`"
            continue
        if c == "/" and (last in _REGEX_AFTER or last == ""):
            j, in_class = i + 1, False
            while j < n and source[j] != "\n":
                if source[j] == "\\":
                    j += 2
                    continue
                if source[j] == "[":
                    in_class = True
                elif source[j] == "]":
                    in_class = False
                elif source[j] == "/" and not in_class:
                    break
                j += 1
            # A regular expression ends on its line; stopping at a newline
            # leaves the newline to be counted.
            i, last = (j + 1 if j < n and source[j] == "/" else j), "/"
            continue
        if not c.isspace():
            last = c
        i += 1
    return [(at, text) for at, text in found if text]


def _client_sources() -> list[Path]:
    return sorted(p for p in CLIENT.rglob("*")
                  if p.suffix in (".ts", ".tsx")
                  and not re.search(r"\.test\.tsx?$", p.name)
                  and p.name != "test-fixtures.ts")


# -- the checks ----------------------------------------------------------------

def test_the_scan_reads_both_halves():
    assert len(list(SERVE.glob("*.py"))) >= 5
    assert len(_client_sources()) >= 10


@pytest.mark.parametrize("path", sorted(SERVE.rglob("*.py")),
                         ids=lambda p: str(p.relative_to(PACKAGE)))
def test_no_server_literal_names_a_stage(path):
    hits = [f"{path.name}:{line}: {text!r}"
            for line, text in python_literals(path.read_text())
            if names_a_stage(text)]
    assert not hits, "\n".join(hits)


@pytest.mark.parametrize("path", _client_sources(),
                         ids=lambda p: str(p.relative_to(CLIENT)))
def test_no_client_literal_names_a_stage(path):
    hits = [f"{path.name}:{line}: {text!r}"
            for line, text in client_literals(path.read_text())
            if names_a_stage(text)]
    assert not hits, "\n".join(hits)


# -- the scanners against planted literals -------------------------------------

@pytest.mark.parametrize("planted", ['"review"', '"plan/plan.md"'])
def test_scanner_finds_a_planted_python_literal(planted):
    source = f'"""A docstring naming review and plan/plan.md."""\nX = {planted}\n'
    assert [t for _, t in python_literals(source) if names_a_stage(t)]


def test_scanner_passes_a_sentence_holding_a_stage_word():
    assert not [t for _, t in python_literals('X = "request body too large"\n')
                if names_a_stage(t)]
    assert not [t for _, t in client_literals('const x = "request body too large"\n')
                if names_a_stage(t)]


@pytest.mark.parametrize("planted", [
    'const a = "review"',
    "const a = 'review'",
    "const a = `plan/plan.md`",
    "const a = `${folder}/plan/plan.md`",
    'f(x, "plan/plan.md")',
])
def test_scanner_finds_a_planted_client_literal(planted):
    assert [t for _, t in client_literals(planted + "\n") if names_a_stage(t)]


def test_client_scanner_skips_comments_and_reads_past_jsx_and_regexes():
    source = "\n".join([
        "// the review stage",
        "/* plan/plan.md */",
        "const r = /tcw:\\/\\/[^\\s\"']*$/.exec(x)",
        "const e = <Text>This project's backend keeps it</Text>",
        'const after = "review"',
    ])
    assert client_literals(source) == [(5, "review")]
