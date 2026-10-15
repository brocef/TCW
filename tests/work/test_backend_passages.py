"""Backend passages (TCW-74 Design 3; criterion 4).

A passage is text for one backend only. The filter keeps it, without its
markers, for that backend and removes it for any other; with no backend at
all (outside a TCW project) it removes every passage.
"""

import io
import sys

import pytest

from tcw.cli import main
from tcw.errors import BackendError
from tcw.work.config import BACKENDS, parse_work_config
from tcw.work.passages import filter_backend
from tcw.work.resolve import load_builtins, stage_prompt
from tests.work.projects import make_project

TEXT = """\
Before.
<!-- backend: jira -->
Only in Jira.
<!-- /backend -->
<!-- backend: filesystem -->
Only on files.
<!-- /backend -->
After.
"""


def test_a_passage_is_kept_for_its_backend_and_removed_for_another():
    assert filter_backend(TEXT, "jira") == "Before.\nOnly in Jira.\nAfter.\n"
    assert filter_backend(TEXT, "filesystem") == "Before.\nOnly on files.\nAfter.\n"


def test_with_no_backend_every_passage_goes_and_the_rest_stays():
    assert filter_backend(TEXT, None) == "Before.\nAfter.\n"


def test_text_with_no_passage_is_unchanged():
    assert filter_backend("a\n\nb", "jira") == "a\n\nb"


def test_a_passage_can_sit_inside_a_list_item():
    text = ("1. First.\n"
            "   <!-- backend: jira -->\n"
            "   In Jira, ask a person.\n"
            "   <!-- /backend -->\n"
            "2. Second.\n")
    assert filter_backend(text, "jira") == \
        "1. First.\n   In Jira, ask a person.\n2. Second.\n"
    assert filter_backend(text, "filesystem") == "1. First.\n2. Second.\n"


def test_a_marker_inside_a_sentence_is_not_a_marker():
    text = "Write `<!-- backend: jira -->` on a line of its own.\n"
    assert filter_backend(text, "filesystem") == text


@pytest.mark.parametrize("comment", [
    "<!-- This prompt is shared by every backend. -->",
    "  <!-- TODO backend-specific wording -->",
    "<!-- Bound to the review stage; the jira backend posts findings instead.",
])
def test_a_comment_that_only_mentions_a_backend_is_kept(comment):
    text = f"a\n{comment}\nb\n"
    for backend in (*BACKENDS, None):
        assert filter_backend(text, backend) == text


@pytest.mark.parametrize("text, words", [
    ("<!-- backend: trello -->\nx\n<!-- /backend -->\n", "unknown backend 'trello'"),
    ("<!-- backend: jira -->\n<!-- backend: filesystem -->\nx\n<!-- /backend -->\n"
     "<!-- /backend -->\n", "inside the one opened at line 1"),
    ("a\n<!-- backend: jira -->\nx\n", "never closed"),
    ("a\n<!-- /backend -->\n", "closes no open backend passage"),
    ("<!-- backend:jira -->\nx\n<!--/backend -->\n", "looks like a backend passage"),
    ("<!-- Backend: jira -->\nx\n", "looks like a backend passage"),
    ("<!-- backend: jira-->\nx\n<!-- /backend -->\n", "looks like a backend passage"),
])
def test_a_malformed_passage_is_an_error_naming_the_line(text, words):
    for backend in (*BACKENDS, None):
        with pytest.raises(BackendError) as error:
            filter_backend(text, backend)
        assert words in str(error.value)
        assert str(error.value).startswith("line ")


@pytest.mark.parametrize("backend", (*BACKENDS, None))
def test_every_built_in_text_filters_cleanly(backend):
    builtins = load_builtins()
    for text in (*builtins.stage_prompts.values(), *builtins.procedures.values()):
        filter_backend(text, backend)


@pytest.mark.parametrize("backend", (*BACKENDS, None))
def test_no_built_in_text_keeps_a_marker_after_filtering(backend):
    """Every marker line is consumed, so none reaches the agent as a comment."""
    builtins = load_builtins()
    texts = {**{f"prompt {k}": v for k, v in builtins.stage_prompts.items()},
             **{f"procedure {k}": v for k, v in builtins.procedures.items()}}
    for name, text in texts.items():
        left = [line for line in filter_backend(text, backend).splitlines()
                if line.strip().startswith("<!--") and "backend" in line.lower()]
        assert left == [], f"{name} under {backend}: {left}"


def test_the_documentation_span_inside_a_passage_still_resolves(tmp_path):
    """Filtering runs before documentation substitution (Design 3.5)."""
    config, problems = parse_work_config({
        "documentation": [{"path": "README.md", "trigger": "Public-API",
                           "description": "the overview"}],
        "stages": {"plan": {"prompt": [{"blob": (
            "<!-- backend: filesystem -->\n"
            "{{tcw:documentation}}nothing{{/tcw:documentation}}\n"
            "<!-- /backend -->\n")}]}}})
    assert problems == []
    text = stage_prompt(config, "plan", project_root=tmp_path).text
    assert "`README.md`" in text and "<!--" not in text and "nothing" not in text


def _run(argv, cwd, monkeypatch, capsys):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    try:
        code = main(argv)
    except SystemExit as stop:
        code = stop.code if isinstance(stop.code, int) else 1
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _project_with_file(tmp_path, body: str):
    root = make_project(tmp_path, "p", config={
        "stages": {"spec": {"prompt": [{"file": "prompts/spec.md"}]}}})
    (root / "prompts").mkdir()
    (root / "prompts" / "spec.md").write_text(body)
    return root


def test_a_project_file_binding_is_filtered_for_the_project(tmp_path, monkeypatch,
                                                           capsys):
    root = _project_with_file(tmp_path, TEXT)
    code, out, _ = _run(["work", "stage", "prompt", "spec"], root, monkeypatch, capsys)
    assert code == 0
    assert "Only on files." in out
    assert "Only in Jira." not in out and "<!--" not in out


def test_a_broken_passage_in_a_project_file_exits_1_naming_it(tmp_path, monkeypatch,
                                                             capsys):
    root = _project_with_file(tmp_path, "a\n<!-- backend: jira -->\nnever closed\n")
    code, out, err = _run(["work", "stage", "prompt", "spec"], root, monkeypatch,
                          capsys)
    assert code == 1
    assert out == ""
    assert "prompts/spec.md" in err and "never closed" in err


def test_a_procedure_outside_a_project_has_no_passage(tmp_path, monkeypatch, capsys):
    """Outside a project there is no backend, so every passage is removed."""
    import tcw.work.resolve as resolve
    monkeypatch.setattr(resolve, "packaged_text", lambda kind, name: TEXT)
    code, out, _ = _run(["work", "procedure", "search"], tmp_path, monkeypatch, capsys)
    assert code == 0
    assert out == "Before.\nAfter.\n"
