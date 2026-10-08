"""The `tcw work` commands TCW-70 removed are gone (AC 10): each exits 2 with
the parser's unknown-command message and writes nothing."""

import io
import sys

import pytest

from tcw.cli import main
from tests.doc_allowance import REMOVED_COMMANDS
from tests.work.projects import commit_all, git, make_project, write_item


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    root = make_project(tmp_path_factory.mktemp("removed"), "p")
    write_item(root, "2026-10-01-a", {"title": "a", "stage": "request"})
    commit_all(root)
    return root


@pytest.mark.parametrize("command", REMOVED_COMMANDS)
def test_a_removed_command_is_unknown(command, project, monkeypatch, capsys):
    monkeypatch.chdir(project)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    words = command.split()[1:]                      # drop "tcw"
    with pytest.raises(SystemExit) as stop:
        main([*words, "2026-10-01-a"])
    err = capsys.readouterr().err
    assert stop.value.code == 2
    assert "invalid choice" in err
    assert git(project, "status", "--porcelain", "--untracked-files=all") == ""
