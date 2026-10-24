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


# -- AC 2: the removed commands name their replacement -----------------------

@pytest.mark.parametrize("argv, line", [
    (["init", "--id", "x"], "`tcw init` is now `tcw project new`"),
    (["projects", "list"], "`tcw projects list` is now `tcw project list`"),
    (["config", "show", "--origin"], "`tcw config show` is now `tcw project config`"),
    (["provision", "--dry-run"], "`tcw provision` is now `tcw project provision`"),
])
def test_a_removed_command_names_its_replacement(tmp_path, argv, line):
    root = tmp_path / "app"
    write_config(root, "id: app\n")
    before = snapshot(root)
    done = run(root, *argv)
    assert (done.code, done.out) == (2, ""), done
    assert line in done.err.splitlines(), done.err
    assert f"invalid choice: '{argv[0]}'" in done.err, done.err
    assert snapshot(root) == before


def test_tcw_help_lists_none_of_the_removed_commands(tmp_path):
    names = [line.split()[0] for line in run(tmp_path, "--help").out.splitlines()
             if line.startswith("    ") and not line.startswith("     ")]
    assert not {"init", "projects", "config", "provision"} & set(names), names


def test_an_error_line_names_the_command_typed(tmp_path):
    # A configuration that cannot be read stops provisioning; one with a
    # problem is still printed by `--origin`, the problem after it.
    for argv, prefix, text in (
            (["project", "provision"], "tcw project provision: ", "id: app\nwork: [\n"),
            (["project", "config", "--origin"], "tcw project config: ",
             "id: app\nwork: [1]\n")):
        root = tmp_path / "-".join(argv)
        write_config(root, text)
        done = run(root, *argv)
        assert done.code == 1, (argv, done)
        assert done.err.startswith(prefix), (argv, done.err)
