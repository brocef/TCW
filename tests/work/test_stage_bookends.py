"""The text around every stage prompt, and `<slug>` (TCW-74 Design 4;
criterion 5, filesystem half; the Jira half is in
`tests/work/jira/test_jira_stage_bookends.py`)."""

import ast
import inspect
import io
import re
import sys
import textwrap
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.work import resolve
from tcw.work.model import STAGES, stage as table_stage
from tcw.work.resolve import stage_footer, stage_header
from tests.work.projects import make_project

REPO = Path(__file__).resolve().parents[2]
SIDE_SENTENCE = "**Nothing follows this stage.**"
EXTERNAL_SENTENCE = "a person decides whether the item moves on"
FLOW_WITH_FILES = ("request", "spec", "plan", "implement", "review", "qa")


def run(argv, cwd, monkeypatch, capsys):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    try:
        code = main(argv)
    except SystemExit as stop:
        code = stop.code if isinstance(stop.code, int) else 1
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def project(tmp_path, monkeypatch, capsys):
    """A filesystem project with every optional stage enabled, and one item."""
    root = make_project(tmp_path, "p", config={"stages": {
        name: {"enabled": True} for name in ("spec", "plan", "review", "qa",
                                             "postmortem")}})
    code, out, _ = run(["work", "new", "Refund a payment"], root, monkeypatch, capsys)
    assert code == 0
    return root, out.strip()


def last_block(text: str) -> str:
    return text.rstrip().split("\n\n")[-1]


def test_postmortem_ends_with_the_side_stage_sentence(project, monkeypatch, capsys):
    root, slug = project
    code, out, _ = run(["work", "stage", "prompt", "postmortem", slug], root,
                       monkeypatch, capsys)
    assert code == 0
    assert SIDE_SENTENCE in last_block(out)
    assert "tcw work advance" not in last_block(out)


def test_inbox_has_no_footer(project, monkeypatch, capsys):
    root, _ = project
    code, out, _ = run(["work", "stage", "prompt", "inbox"], root, monkeypatch, capsys)
    assert code == 0
    tail = last_block(out)
    assert not tail.startswith(">"), tail
    assert stage_footer(table_stage("inbox"), frozenset(), "<slug>") is None


@pytest.mark.parametrize("name", FLOW_WITH_FILES)
def test_a_filesystem_footer_names_advance_for_the_item(name, project, monkeypatch,
                                                        capsys):
    root, slug = project
    code, out, _ = run(["work", "stage", "prompt", name, slug], root, monkeypatch,
                       capsys)
    assert code == 0
    footer = last_block(out)
    assert f"`tcw work advance {slug}`" in footer
    assert EXTERNAL_SENTENCE not in footer


@pytest.mark.parametrize("name", [s.name for s in STAGES if s.prompt])
def test_with_a_reference_no_literal_slug_is_left(name, project, monkeypatch, capsys):
    root, slug = project
    argv = ["work", "stage", "prompt", name] + ([] if name == "inbox" else [slug])
    code, out, _ = run(argv, root, monkeypatch, capsys)
    assert code == 0
    if name != "inbox":
        assert "<slug>" not in out
        assert slug in out.splitlines()[0]          # the header names it too


def test_without_a_reference_slug_stays_literal(project, monkeypatch, capsys):
    root, _ = project
    code, out, _ = run(["work", "stage", "prompt", "spec"], root, monkeypatch, capsys)
    assert code == 0
    assert "`tcw work advance <slug>`" in last_block(out)


def test_the_header_says_no_checks_ran():
    header = stage_header("p/x")
    assert "ran no checks" in header and "`tcw work advance p/x --dry-run`" in header


def test_a_stand_in_backend_keeps_its_own_external_stages():
    """A third backend that keeps spec itself: spec gets the external sentence
    and request the `advance` one, so a footer keyed on stage names rather
    than on `external` fails here."""
    external = frozenset({"spec"})
    spec = stage_footer(table_stage("spec"), external, "<slug>")
    request = stage_footer(table_stage("request"), external, "<slug>")
    assert EXTERNAL_SENTENCE in spec and "`tcw work advance <slug>`" not in spec
    assert "`tcw work advance <slug>`" in request and EXTERNAL_SENTENCE not in request


def test_a_verdict_stage_says_the_round_comes_first():
    for name in ("review", "qa"):
        assert "write the round first" in stage_footer(table_stage(name), frozenset(),
                                                       "<slug>")
    assert "The verdict is that move." in stage_footer(
        table_stage("qa"), frozenset({"qa"}), "<slug>")


@pytest.mark.parametrize("name", ["request", "qa"])
def test_an_external_footer_moves_the_item_only_when_the_person_says_so(name):
    """A stage the backend keeps: a person decides, and once that person says
    to move the item, the agent moves it with `advance` (TCW-100). A verdict
    stage needs `--to` and a `--reason`, which `advance` refuses without."""
    footer = " ".join(stage_footer(table_stage(name), frozenset({name}),
                                   "<slug>").split())
    assert EXTERNAL_SENTENCE in footer
    assert "only when that person tells you to" in footer
    assert "Do not move it yourself" not in footer
    assert "`tcw work advance <slug> " in footer and "--reason" in footer
    assert ("--to <stage>" in footer) == bool(table_stage(name).verdict)


def _source(function) -> str:
    """The function's code with its docstring and comments removed."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    body = tree.body[0].body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    return "\n".join(ast.unparse(node) for node in body)


@pytest.mark.parametrize("function", [stage_header, stage_footer])
def test_the_generated_text_names_no_stage_and_no_backend(function):
    """Derived from the table's columns and `external_stages`, never from a
    stage's or a backend's name (Design 4.1, R18)."""
    code = _source(function)
    names = [s.name for s in STAGES] + ["filesystem", "jira"]
    found = [name for name in names
             if re.search(rf"\b{re.escape(name)}\b", code, re.IGNORECASE)]
    assert found == [], f"{function.__name__} names {found}"


def test_no_shipped_file_uses_the_body_token_and_templates_are_gone():
    shipped = [*REPO.glob("tcw/work/prompts/*.md"), *REPO.glob("tcw/work/procedures/*.md"),
               *REPO.glob("skills/**/*.md"), *REPO.glob("agents/*.md")]
    assert [str(p) for p in shipped if "{{tcw:body}}" in p.read_text(encoding="utf-8")] == []
    for name in ("spec", "plan"):
        assert "{{tcw:request}}" in (REPO / "tcw" / "work" / "prompts" / f"{name}.md"
                                     ).read_text(encoding="utf-8")
    assert not (REPO / "tcw" / "work" / "templates.py").exists()
    assert not hasattr(resolve, "resolve_artifact")
