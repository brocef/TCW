"""The `tcw project` command group (TCW-115 Design 1, AC 1).

Its verbs replace `tcw init`, `tcw projects list`, `tcw config show` and
`tcw provision`, and add `path` and `info`.
"""

from __future__ import annotations

import pytest

from tests.projectfiles import write_config
from tests.test_cli_contract import run, snapshot


def test_the_group_lists_its_verbs(tmp_path):
    shown = run(tmp_path, "project", "--help")
    assert shown.code == 0
    for verb in ("new", "list", "config", "provision"):
        assert f"    {verb}" in shown.out, (verb, shown.out)


def test_the_group_alone_is_a_usage_error(tmp_path):
    assert run(tmp_path, "project").code == 2


def test_tcw_help_lists_project_after_work(tmp_path):
    names = [line.split()[0] for line in run(tmp_path, "--help").out.splitlines()
             if line.startswith("    ") and not line.startswith("     ")]
    assert "project" in names
    assert names.index("work") < names.index("project")


# -- Step 2's side by side: each new verb does what the command it replaces
#    does. Removed with the old commands.

def _fixture(root):
    write_config(root, "id: app\n")
    return root


@pytest.mark.parametrize("old, new", [
    (["projects", "list"], ["project", "list"]),
    (["config", "show"], ["project", "config"]),
    (["provision", "--dry-run"], ["project", "provision", "--dry-run"]),
])
def test_side_by_side_in_a_project(tmp_path, old, new):
    a = _fixture(tmp_path / "a")
    b = _fixture(tmp_path / "b")
    before, after = run(a, *old), run(b, *new)
    assert (before.code, before.out) == (after.code, after.out)
    assert before.err.replace(str(a), "<root>") == after.err.replace(str(b), "<root>")
    assert snapshot(a) == snapshot(b)


def test_side_by_side_new(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    before, after = run(a, "init", "--id", "demo"), run(b, "project", "new", "--id", "demo")
    assert (before.code, before.out) == (after.code, after.out) == (0, "")
    assert before.err.replace(str(a), "<root>") == after.err.replace(str(b), "<root>")
    assert snapshot(a) == snapshot(b)


def test_an_error_line_names_the_command_typed(tmp_path):
    # A configuration that cannot be read stops provisioning; one with a
    # problem is still printed by `--origin`, the problem after it.
    for argv, prefix, text in (
            (["provision"], "tcw provision: ", "id: app\nwork: [\n"),
            (["project", "provision"], "tcw project provision: ", "id: app\nwork: [\n"),
            (["config", "show", "--origin"], "tcw config show: ", "id: app\nwork: [1]\n"),
            (["project", "config", "--origin"], "tcw project config: ",
             "id: app\nwork: [1]\n")):
        root = tmp_path / "-".join(argv)
        write_config(root, text)
        done = run(root, *argv)
        assert done.code == 1, (argv, done)
        assert done.err.startswith(prefix), (argv, done.err)
