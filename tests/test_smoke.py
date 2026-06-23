import subprocess
from pathlib import Path

import pytest

from tcw.cli import build_parser, main
from tcw.store.fs import COMPONENTS, WORK_STATUSES


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def test_init_scaffolds_all_components(tmp_path, monkeypatch):
    _git_init(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    for c in COMPONENTS:
        assert (tmp_path / "docs" / c).is_dir()
    for s in WORK_STATUSES:
        assert (tmp_path / "docs" / "work" / s / ".gitkeep").is_file()


def test_init_named_subset_only(tmp_path, monkeypatch):
    _git_init(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["init", "taxonomy"]) == 0
    assert (tmp_path / "docs" / "taxonomy").is_dir()
    assert not (tmp_path / "docs" / "work").exists()


def test_init_refuses_outside_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # tmp_path is not a git work-tree
    assert main(["init"]) == 1


def test_init_rejects_unknown_component(tmp_path, monkeypatch):
    _git_init(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["init", "bogus"]) == 2


def test_init_scaffolds_in_current_subfolder(tmp_path, monkeypatch):
    _git_init(tmp_path)                       # one git repo
    proj = tmp_path / "project-b"
    proj.mkdir()
    monkeypatch.chdir(proj)                   # cwd is a subfolder, not the git root
    assert main(["init", "work"]) == 0
    assert (proj / "tcw-config.yaml").is_file()
    assert (proj / "docs" / "work").is_dir()
    assert not (tmp_path / "docs").exists()   # scaffolded at cwd, not the git root


def test_command_outside_a_node_reports_helpfully(tmp_path, monkeypatch, capsys):
    _git_init(tmp_path)            # a git repo but NOT a tcw node (no sentinel)
    monkeypatch.chdir(tmp_path)
    assert main(["work", "list"]) == 1
    assert "tcw init" in capsys.readouterr().err


def test_capabilities_check_outside_a_node_reports_helpfully(tmp_path, monkeypatch, capsys):
    _git_init(tmp_path)            # a git repo but NOT a tcw node (no sentinel)
    monkeypatch.chdir(tmp_path)
    assert main(["capabilities", "check"]) == 1
    assert "tcw init" in capsys.readouterr().err


def test_help_lists_four_groups(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    out = capsys.readouterr().out
    for group in ("init", *COMPONENTS):
        assert group in out
