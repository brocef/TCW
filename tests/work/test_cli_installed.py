"""The `tcw work` commands as a shell sees them (TCW-70 AC 2's first line and
AC 11, the (installed) criteria).

Each run is `sys.executable -c` calling `tcw.cli.main` with this checkout first
on `sys.path`, never the `tcw` on `PATH`: in a git worktree the editable
install's console script runs the primary checkout's code. Stdin is
`subprocess.DEVNULL` unless a case pipes text.
"""

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest
import yaml

from tests.work.projects import make_project, write_item

REPO = Path(__file__).resolve().parents[2]
TODAY = date.today().isoformat()


@dataclass
class Result:
    code: int
    out: str
    err: str


def tcw(argv, cwd, stdin=None) -> Result:
    script = (f"import sys; sys.path.insert(0, {str(REPO)!r}); "
              f"from tcw.cli import main; sys.exit(main({['work', *argv]!r}))")
    r = subprocess.run([sys.executable, "-c", script], cwd=cwd, text=True,
                       capture_output=True,
                       input=stdin, stdin=None if stdin is not None
                       else subprocess.DEVNULL)
    return Result(r.returncode, r.stdout, r.stderr)


@pytest.fixture
def p(tmp_path):
    return make_project(tmp_path, "p")


def stage_of(root, folder):
    return yaml.safe_load(
        (root / "docs/work" / folder / "item.yaml").read_text())["stage"]


def test_new_prints_exactly_the_slug(p):
    r = tcw(["new", "Add a widget"], p)
    assert (r.code, r.out) == (0, f"p/{TODAY}-add-a-widget\n"), r.err
    assert not (p / "docs/work" / f"{TODAY}-add-a-widget" / "request").exists()


def test_piped_text_is_the_request(p):
    r = tcw(["new", "X"], p, stdin="line one\n")
    assert r.code == 0, r.err
    request = p / "docs/work" / f"{TODAY}-x" / "request" / "request.md"
    assert request.read_text() == "line one\n"


def test_edit_and_comment_print_nothing(p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "spec"})
    r = tcw(["edit", "2026-10-01-a", "--priority", "high"], p)
    assert (r.code, r.out) == (0, ""), r.err
    r = tcw(["comment", "2026-10-01-a"], p, stdin="hi\n")
    assert (r.code, r.out) == (0, ""), r.err


def test_advance_and_discard_print_the_stage(p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "request"})
    r = tcw(["advance", "2026-10-01-a", "--to", "plan", "--force",
             "--reason", "skip"], p)
    assert (r.code, r.out) == (0, "plan\n"), r.err
    r = tcw(["discard", "2026-10-01-a", "--reason", "not needed"], p)
    assert (r.code, r.out) == (0, "discarded\n"), r.err


def test_paths(p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "review"})
    r = tcw(["path", "2026-10-01-a", "review", "--next"], p)
    assert (r.code, r.err) == (0, "")
    assert r.out.endswith("review/round-1.md\n") and r.out.count("\n") == 1
    assert os.path.isabs(r.out.strip())
    r = tcw(["path", "2026-10-01-a", "spec", "--handoff"], p)
    assert r.code == 0, r.err
    assert f"{os.sep}2026-10-01-a{os.sep}spec{os.sep}" in r.out
    assert not (p / "docs/work/2026-10-01-a/spec").exists()
    assert tcw(["path", "2026-10-01-a", "spec", "--next", "--handoff"], p).code == 2


def test_an_unknown_slug_is_four(p):
    assert tcw(["show", "2026-10-01-nothing"], p).code == 4


def test_a_refused_advance_is_three_with_nothing_on_stdout(p):
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "request"})
    r = tcw(["advance", "2026-10-01-a", "--to", "plan"], p)
    assert (r.code, r.out) == (3, "")
    assert stage_of(p, "2026-10-01-a") == "request"


def test_dry_run(p):
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "request"})
    before = sorted(str(x) for x in folder.rglob("*"))
    r = tcw(["advance", "2026-10-01-a", "--dry-run"], p)
    assert (r.code, r.out) == (0, "spec\n"), r.err
    r = tcw(["advance", "2026-10-01-a", "--to", "plan", "--dry-run"], p)
    assert (r.code, r.out) == (3, "")
    assert stage_of(p, "2026-10-01-a") == "request"
    assert sorted(str(x) for x in folder.rglob("*")) == before
