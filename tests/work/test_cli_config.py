"""Configuration through the `tcw work` commands (TCW-70 AC 20, AC 21, and
`lifecycle` listing the enabled stages with their bindings)."""

import io
import json
import sys
from dataclasses import dataclass
from datetime import date

import pytest

from tcw.cli import main
from tcw.work.resolve import BODY_CAP, packaged_text
from tests.doc_allowance import REMOVED_COMMANDS
from tests.work.projects import make_project

TODAY = date.today().isoformat()
GUIDE = "docs/migration-guide-2.8-to-3.0.0.md"


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def tcw(monkeypatch, capsys):
    def run(argv, cwd, stdin=""):
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(["work", *argv])
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run


def packaged_lines(name):
    return [line for line in packaged_text("prompts", name).splitlines()
            if line.strip() and "{{" not in line]


def spec_prompt(tmp_path, prompt=None):
    config = {} if prompt is None else {"stages": {"spec": {"prompt": prompt}}}
    root = make_project(tmp_path, "p", config=config)
    (root / "house.md").write_text("HOUSE RULES\n")
    return root


# -- AC 20 -------------------------------------------------------------------------------

def test_a_removed_key_refuses_every_command(tcw, tmp_path):
    root = make_project(tmp_path, "p", config={"tracker": {"provider": "jira"}})
    r = tcw(["list"], root)
    assert r.code == 1
    assert "work.tracker" in r.err and GUIDE in r.err


# -- AC 21: which bindings compose --------------------------------------------------------

def test_builtin_then_a_file(tcw, tmp_path):
    root = spec_prompt(tmp_path, [{"builtin": True}, {"file": "house.md"}])
    tcw(["new", "X"], root)
    r = tcw(["stage", "prompt", "spec", f"{TODAY}-x"], root)
    assert r.code == 0, r.err
    assert all(line in r.out for line in packaged_lines("spec"))
    assert r.out.index(packaged_lines("spec")[-1]) < r.out.index("HOUSE RULES")


def test_a_list_without_builtin_replaces_the_packaged_text(tcw, tmp_path):
    root = spec_prompt(tmp_path, [{"file": "house.md"}])
    r = tcw(["stage", "prompt", "spec"], root)
    assert "HOUSE RULES" in r.out
    assert not any(line in r.out for line in packaged_lines("spec"))


def test_an_empty_list_composes_to_nothing(tcw, tmp_path):
    root = spec_prompt(tmp_path, [])
    r = tcw(["stage", "prompt", "spec"], root)
    assert r.code == 0
    assert "HOUSE RULES" not in r.out
    assert not any(line in r.out for line in packaged_lines("spec"))


def test_no_prompt_key_is_the_packaged_text(tcw, tmp_path):
    root = spec_prompt(tmp_path)
    r = tcw(["stage", "prompt", "spec"], root)
    assert all(line in r.out for line in packaged_lines("spec"))


# -- AC 21: the request span ---------------------------------------------------------------

def test_the_request_fills_the_span(tcw, tmp_path):
    root = spec_prompt(tmp_path)
    tcw(["new", "X"], root, stdin="line one\n")
    r = tcw(["stage", "prompt", "spec", f"{TODAY}-x"], root)
    assert "line one" in r.out
    assert "{{tcw:request}}" not in r.out and "{{tcw:body}}" not in r.out


def test_no_request_shows_the_span_text(tcw, tmp_path):
    root = spec_prompt(tmp_path)
    tcw(["new", "X"], root)
    r = tcw(["stage", "prompt", "spec", f"{TODAY}-x"], root)
    assert "the item's body artifact" in r.out
    assert "{{tcw:request}}" not in r.out


def test_a_stage_whose_text_is_missing_fails(tcw, tmp_path):
    root = spec_prompt(tmp_path)
    r = tcw(["stage", "prompt", "review"], root)
    assert r.code == 1
    assert "tcw/work/prompts/review.md" in r.err


def test_the_output_names_no_removed_command(tcw, tmp_path):
    root = spec_prompt(tmp_path)
    tcw(["new", "X"], root)
    r = tcw(["stage", "prompt", "spec", f"{TODAY}-x"], root)
    assert r.code == 0
    named = [c for c in REMOVED_COMMANDS if c in r.out]
    assert named == []


# -- AC 21: what a generate binding receives --------------------------------------------

GENERATOR = """\
import json, os, sys
from pathlib import Path
Path("seen.json").write_text(json.dumps({
    "stdin": sys.stdin.read(), "cwd": os.getcwd(),
    "slug": os.environ.get("TCW_SLUG"),
    "role": os.environ.get("TCW_HOOK_ROLE")}))
print("GENERATED")
"""


@pytest.fixture
def generated(tcw, tmp_path):
    root = spec_prompt(tmp_path, [{"generate": f"{sys.executable} gen.py"}])
    (root / "gen.py").write_text(GENERATOR)

    def run(request):
        tcw(["new", "X"], root, stdin=request)
        r = tcw(["stage", "prompt", "spec", f"{TODAY}-x"], root)
        assert r.code == 0, r.err
        assert "GENERATED" in r.out
        seen = json.loads((root / "seen.json").read_text())
        return root, seen, json.loads(seen["stdin"])
    return run


def test_a_generate_binding_gets_one_record(generated):
    root, seen, payload = generated("line one\n")
    assert set(payload) == {"schema", "item", "request", "hook"}
    assert payload["schema"] == 1
    assert payload["item"]["slug"] == f"p/{TODAY}-x"
    assert payload["request"] == "line one\n"
    assert set(payload["hook"]) == {"role", "kind", "id", "phase",
                                    "body_truncated"}
    assert payload["hook"]["body_truncated"] is False
    assert seen["cwd"] == str(root.resolve())
    assert seen["slug"] == f"p/{TODAY}-x"
    assert seen["role"]


def test_no_request_is_null(generated):
    _, _, payload = generated("")
    assert payload["request"] is None


def test_a_long_request_arrives_cut(generated):
    _, _, payload = generated("x" * (BODY_CAP + 10))
    assert payload["hook"]["body_truncated"] is True
    assert len(payload["request"].encode()) <= BODY_CAP


# -- lifecycle -------------------------------------------------------------------------

def test_lifecycle_lists_the_enabled_stages_with_their_bindings(tcw, tmp_path):
    root = make_project(tmp_path, "p", config={"stages": {
        "plan": {"enabled": False},
        "spec": {"pre": [{"command": "true"}], "post": [{"skill": "tidy"}]}}})
    r = tcw(["lifecycle", "--json"], root)
    assert r.code == 0, r.err
    stages = {s["name"]: s for s in json.loads(r.out)["stages"]}
    assert "plan" not in stages and "spec" in stages and "request" in stages
    assert stages["spec"]["bindings"]["pre"] == [{"command": "true"}]
    assert stages["spec"]["bindings"]["post"] == [{"skill": "tidy"}]
    assert stages["spec"]["bindings"]["prompt"] == [{"builtin": True}]
    r = tcw(["lifecycle", "--stage", "spec", "--directive"], root)
    assert "tidy" in r.out and "`true`" in r.out
