"""2.x's tracker is gone, and the Jira backend never changes git state
(TCW-71 AC 21, AC 22). The capability-record half of AC 21 is in task 16."""

import ast
import io
import sys
from pathlib import Path

import pytest

import tcw
from tcw.cli import main
from tcw.work.config import MIGRATION_GUIDE, parse_work_config
from tcw.work.model import Changes
from tests.work.projects import commit_all, git

PACKAGE = Path(tcw.__file__).resolve().parent
JIRA_MODULES = sorted((PACKAGE / "work" / "jira").glob("*.py"))
FORBIDDEN = ("work.tracker", "tracker_strict", "tracker.yaml", "tcw.tracker",
             "TrackerConfig")


# -- AC 21 -------------------------------------------------------------------------


def test_the_tracker_package_is_gone():
    assert not (PACKAGE / "tracker").exists()


def test_no_module_names_the_2x_tracker():
    found = [f"{path.relative_to(PACKAGE)}: {word}"
             for path in sorted(PACKAGE.rglob("*.py"))
             for word in FORBIDDEN if word in path.read_text(encoding="utf-8")]
    assert found == []


def test_tcw_work_tracker_is_unknown(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    with pytest.raises(SystemExit) as stop:
        main(["work", "tracker", "--help"])
    assert stop.value.code == 2


def test_work_tracker_names_the_migration_guide():
    _, problems = parse_work_config({"tracker": {"provider": "jira"}})
    assert any(MIGRATION_GUIDE in str(p) for p in problems)


# -- AC 22 -------------------------------------------------------------------------


def _git_calls(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names if a.name.split(".")[0] == "subprocess"]
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] \
                == "subprocess":
            found.append(node.module)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id == "os" and node.attr in ("system", "popen"):
            found.append(f"os.{node.attr}")
    return found


@pytest.mark.parametrize("path", JIRA_MODULES, ids=lambda p: p.name)
def test_no_jira_module_runs_a_process(path):
    assert _git_calls(path) == []


def test_the_scan_sees_each_way_of_running_a_process(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text("import subprocess\nfrom subprocess import run\nimport os\n"
                      "os.system('x')\nos.popen('y')\n")
    assert _git_calls(sample) == ["subprocess", "subprocess", "os.system", "os.popen"]


def test_create_rename_and_adopt_leave_git_alone(jira_project, tcw):
    root = jira_project.root
    commit_all(root)

    def state():
        return (git(root, "rev-parse", "HEAD"), git(root, "for-each-ref"))
    before = state()
    backend = jira_project.backend()
    made = backend.create("Made here", Changes(), stage="request", request=None)
    renamed = backend.rename(made.slug.folder, "renamed")
    plain = jira_project.fake.ticket("Plain")
    assert tcw(["tickets", "adopt", plain.key], root).code == 0
    assert state() == before
    status = sorted(git(root, "status", "--porcelain", "--untracked-files=normal")
                    .splitlines())
    assert status == [f"?? docs/work/{renamed.slug.folder}/",
                      f"?? docs/work/{plain.key}-plain/"]
