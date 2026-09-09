"""`TCW_PROJECT_<ID>` — telling TCW where a connected project sits on this machine.

The registry-level behaviour is pinned in `test_project_registry.py`. What is
here is the half that only shows at the command boundary: whether an override is
*reported*, and whether the commands that resolve a graph all honour it.

Both matter more than they look. An override is invisible to every file the
checkout holds — set in an environment's configuration, it is in no config any
reader can grep — so a graph that resolves for a reason nobody can see is the
inverse of works-on-my-machine. Reporting is the whole mitigation.

**No test here reaches the network.** Where a remote is needed it is a real bare
repository in `tmp_path`; git does not care that the URL is a local path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main


def _node(root: Path, body: str) -> Path:
    """A tcw node at `root` with `body` as its config, and nothing defaulted.

    Every key the resolution ladder branches on is written by the caller. A
    helper that supplied a locator or a repository of its own would fix an axis
    these tests exist to vary.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "tcw-config.yaml").write_text(body, encoding="utf-8")
    return root


def _git_repo(root: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    for key, value in (("user.email", "t@example.invalid"), ("user.name", "T"),
                       ("commit.gpgsign", "false")):
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
    return root


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Three sibling nodes, laid out flat, with the configs written for a
    *nested* layout — the reproduction from the intake.

    `orchestrator` declares its child at `./core`, which is where it would sit
    on the machine whose author wrote the config. Here it is a sibling, so the
    declared locator names nothing and the graph is incomplete without help.
    """
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    orchestrator = _node(
        tmp_path / "orchestrator",
        "id: root-project\nconnected-projects:\n  children:\n"
        "    core-project: ./core\n",
    )
    core = _node(
        tmp_path / "core",
        "id: core-project\nconnected-projects:\n  parent:\n"
        "    root-project: ..\n",
    )
    monkeypatch.chdir(orchestrator)
    return tmp_path, orchestrator, core


def test_validate_says_which_overrides_are_in_effect(workspace, capsys, monkeypatch):
    """Criterion 9 — printed, exit 0, and not counted as a problem."""
    _tmp, _orchestrator, core = workspace
    monkeypatch.setenv("TCW_PROJECT_CORE_PROJECT", str(core))
    assert main(["validate"]) == 0
    err = capsys.readouterr().err
    assert err.count("TCW_PROJECT_CORE_PROJECT") == 1
    assert "'core-project' is overridden by TCW_PROJECT_CORE_PROJECT" in err
    assert str(core) in err
    # Never counted. The tally is what a reader scans for, and an override in
    # it would read as something to fix.
    assert "problem(s)" not in err


def test_validate_reports_the_override_beside_the_error_it_explains(
        workspace, capsys, monkeypatch):
    """An override that landed on the wrong node names a path in no config.

    `_cmd_validate` returns from inside its problem block, so an override line
    printed after it never appears on precisely the run where the reader most
    needs it. This asserts the ordering, not merely the presence.
    """
    tmp_path, _orchestrator, _core = workspace
    _node(tmp_path / "wrong", "id: other-project\n")
    monkeypatch.setenv("TCW_PROJECT_CORE_PROJECT", str(tmp_path / "wrong"))
    assert main(["validate"]) == 1
    err = capsys.readouterr().err
    assert "TCW_PROJECT_CORE_PROJECT" in err
    assert "other-project" in err
    assert err.index("TCW_PROJECT_CORE_PROJECT") < err.index("project graph problem")


def test_validate_with_no_override_says_nothing_about_one(workspace, capsys):
    """The rung is absent, not empty.

    Exit 0: the declared locator resolves nothing, which is a declaration this
    checkout cannot follow rather than a defect, and that was true before this
    feature existed. The assertion that matters is that no override vocabulary
    reaches a run that has none.
    """
    assert main(["validate"]) == 0
    err = capsys.readouterr().err
    assert "declared but not reachable" in err       # the pre-existing report
    assert "TCW_PROJECT" not in err
    assert "overridden" not in err
