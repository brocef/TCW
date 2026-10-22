"""`tcw validate` and `tcw init` with personal files (TCW-72 AC 8's validate
line, AC 9's, 16 and 17)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from tests.config.conftest import tcw
from tests.work.projects import commit_all, connect, make_project

WARNING = ("warning: tcw-config.local.yaml: tracked; personal configuration "
           "should stay out of version control (stop tracking it and list it "
           "in .gitignore)")
NOTICE = ("note: not inside a repository, so no ignore rule was written; keep "
          "tcw-config.local.yaml out of version control yourself")


def git(root: Path, *argv: str) -> str:
    return subprocess.run(["git", "-C", str(root), *argv], check=True,
                          capture_output=True, text=True).stdout


def repository(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    git(root, "config", "user.name", "t")
    git(root, "config", "user.email", "t@example.test")
    return root


# -- AC 8: validate reports a personal problem as a finding --------------------------


def test_validate_names_a_shared_key_in_the_local_file(personal):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.local({"id": "other"})
    result = tcw(personal.root, "validate")
    assert result.code == 1, result
    assert ("error: tcw-config.local.yaml: id: a shared key; a personal file "
            "cannot set it") in result.out.splitlines()
    assert result.out.count("tcw-config.local.yaml") == 1, result.out


def test_validate_names_a_user_wide_problem_by_its_path(personal):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.user({"work": {"stages": {"spec": {"prompt": [{"nonsense": 1}]}}}})
    result = tcw(personal.root, "validate")
    assert result.code == 1, result
    assert any(line.startswith(f"error: {personal.user_file}: "
                               f"work.stages.spec.prompt[0]: ")
               for line in result.out.splitlines()), result.out


# -- AC 9: another project's personal file is not this project's business -------------


def test_validate_in_the_parent_ignores_the_childs_local_file(tmp_path, monkeypatch):
    parent = make_project(tmp_path, "parent")
    child = make_project(tmp_path, "child")
    connect(parent, child, "children")
    connect(child, parent, "parent")
    commit_all(parent)
    commit_all(child)
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    write_local_config(child, "id: wrong\n")
    result = tcw(parent, "validate")
    assert result.code == 0, result
    assert "tcw-config.local.yaml" not in result.out + result.err


# -- AC 16: writers touch only the team's file ---------------------------------------


def test_tags_add_leaves_the_personal_files_alone(personal):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.project({"work": {"tags": ["a"]}})
    personal.local({"user": {"name": "Brian"}})
    personal.user({"work": {"stages": {"spec": {"post": [{"command": "true"}]}}}})
    local_before = personal.local_file.read_bytes()
    project_before = yaml.safe_load(personal.project_file.read_text())
    result = tcw(personal.root, "work", "tags", "add", "x")
    assert result.code == 0, result
    assert personal.local_file.read_bytes() == local_before
    project_after = yaml.safe_load(personal.project_file.read_text())
    assert project_after["work"].pop("tags") == ["a", "x"]
    project_before["work"].pop("tags")
    assert project_after == project_before
    assert "post" not in personal.project_file.read_text()


# -- AC 17: init writes the ignore rule; validate warns when the file is tracked ------


def test_init_adds_the_ignore_rule_once(tmp_path):
    root = repository(tmp_path / "p")
    first = tcw(root, "init", "--id", "p")
    assert first.code == 0, first
    assert "wrote .gitignore" in first.err.splitlines()
    assert (root / ".gitignore").read_text() == "/tcw-config.local.yaml\n"
    again = tcw(root, "init")
    assert again.code == 0, again
    assert (root / ".gitignore").read_text() == "/tcw-config.local.yaml\n"
    assert ".gitignore" not in again.err
    staged = [l for l in git(root, "status", "--porcelain").splitlines()
              if l[0] not in " ?"]
    assert staged == []


def test_init_accepts_the_rule_written_without_a_slash(tmp_path):
    root = repository(tmp_path / "p")
    (root / ".gitignore").write_text("node_modules\ntcw-config.local.yaml\n")
    assert tcw(root, "init", "--id", "p").code == 0
    assert (root / ".gitignore").read_text() == "node_modules\ntcw-config.local.yaml\n"


def test_init_adds_a_line_end_before_its_rule(tmp_path):
    root = repository(tmp_path / "p")
    (root / ".gitignore").write_text("node_modules")
    assert tcw(root, "init", "--id", "p").code == 0
    assert (root / ".gitignore").read_text() == \
        "node_modules\n/tcw-config.local.yaml\n"


def test_init_outside_a_repository_prints_the_notice(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    result = tcw(root, "init", "--id", "p")
    assert result.code == 0, result
    assert not (root / ".gitignore").exists()
    assert NOTICE in result.err.splitlines()


def _validated(root: Path):
    return tcw(root, "validate")


def test_validate_warns_when_the_local_file_is_tracked(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    root = repository(tmp_path / "p")
    assert tcw(root, "init", "--id", "p").code == 0
    write_local_config(root, "user:\n  name: Brian\n")
    assert WARNING not in _validated(root).out           # untracked and ignored
    (root / ".gitignore").write_text("")
    assert WARNING not in _validated(root).out           # untracked, not ignored
    git(root, "add", "-f", "tcw-config.local.yaml")
    result = _validated(root)
    assert (result.code, result.out) == (0, WARNING + "\n"), result


def test_validate_ignores_the_setting_that_hides_untracked_files(tmp_path, monkeypatch):
    # Review finding C6: with `status.showUntrackedFiles=no`, git's status
    # prints nothing for an untracked file, just as for a tracked one.
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    root = repository(tmp_path / "p")
    git(root, "config", "status.showUntrackedFiles", "no")
    assert tcw(root, "init", "--id", "p").code == 0
    write_local_config(root, "user:\n  name: Brian\n")
    assert WARNING not in _validated(root).out           # untracked and ignored
    (root / ".gitignore").write_text("")
    assert WARNING not in _validated(root).out           # untracked, not ignored
    git(root, "add", "-f", "tcw-config.local.yaml")
    result = _validated(root)
    assert (result.code, result.out) == (0, WARNING + "\n"), result


def test_validate_outside_a_repository_does_not_warn(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    root = tmp_path / "p"
    root.mkdir()
    assert tcw(root, "init", "--id", "p").code == 0
    write_local_config(root, "user:\n  name: Brian\n")
    result = _validated(root)
    assert (result.code, result.out) == (0, ""), result


# -- A broken tcw-config.yaml is one error (review finding C4) -------------------------


import pytest
from tests.projectfiles import write_config_file, write_local_config


@pytest.mark.parametrize("text", [b"id: p\nid: q\n", b"id: [p\n", b"- p\n", b"id: p\xff\n"])
def test_a_broken_project_file_is_one_validate_error(personal, text):
    (personal.root / "docs" / "work").mkdir(parents=True)
    write_config_file(personal.project_file, text)
    result = tcw(personal.root, "validate")
    assert result.code == 1, result
    errors = [l for l in result.out.splitlines() if l.startswith("error: ")]
    assert len(errors) == 1, result.out
    assert errors[0].startswith("error: tcw-config.yaml: "), errors
