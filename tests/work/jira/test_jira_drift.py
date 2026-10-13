"""`tcw capabilities drift` in Jira mode (TCW-73 Design 7.5; AC 16): Jira
alone knows which items are completed, so an unreachable Jira is exit 5, and
the unreviewed half, which needs no network, is printed first."""

from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore, init
from tests.work.projects import connect, make_project


def test_an_unreachable_jira_exits_5_after_the_unreviewed_lines(
        jira_project, tmp_path, monkeypatch, capsys):
    base = make_project(tmp_path, "base")
    init(["capabilities"], base, "base")
    FsCapabilitiesStore.open(base).add("auth/login", status="Supported")
    init(["capabilities"], jira_project.root, "tcw")
    connect(jira_project.root, base, "upstream")
    FsCapabilitiesStore.open(jira_project.root).extends_add("base")
    jira_project.fake.unreachable()
    monkeypatch.chdir(jira_project.root)
    assert main(["capabilities", "drift"]) == 5
    printed = capsys.readouterr()
    assert printed.out.splitlines() == [
        line for line in printed.out.splitlines() if line.startswith("unreviewed: ")]
    assert "base/auth/login" in printed.out
    assert printed.err.startswith("tcw capabilities drift: ")


def test_completed_items_come_from_jira(jira_project, monkeypatch, capsys):
    init(["capabilities"], jira_project.root, "tcw")
    _, done = jira_project.item("Done", "done", status="Done")
    (jira_project.work / done / "capabilities.yaml").write_text("new: [x/y]\n")
    monkeypatch.chdir(jira_project.root)
    assert main(["capabilities", "drift"]) == 1
    [line] = capsys.readouterr().out.splitlines()
    assert line.startswith("drift: x/y: ") and done in line
