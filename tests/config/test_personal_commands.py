"""Every command on the layered loader (TCW-72 AC 8, 9, 11, 21)."""

from __future__ import annotations

import pytest
import yaml

from tcw.errors import ConfigError
from tcw.work.open import open_backend, open_project
from tcw.work.resolve import packaged_text
from tests.config.conftest import tcw
from tests.work.projects import commit_all, connect, make_project
from tests.projectfiles import config_file, write_config_file, write_local_config


def packaged_lines(name: str) -> list[str]:
    return [line for line in packaged_text("prompts", name).splitlines()
            if line.strip() and "{{" not in line]


# -- AC 8: every command that loads the configuration refuses -----------------------


@pytest.mark.parametrize("argv", [
    ["work", "list"],
    ["work", "stage", "prompt", "spec"],
    ["taxonomy", "list"],
    ["capabilities", "list"],
    ["projects", "list"],
    ["work", "lifecycle"],
])
def test_a_shared_key_in_the_local_file_stops_every_command(personal, argv):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.local({"id": "other"})
    result = tcw(personal.root, *argv)
    assert result.code == 1, result
    assert result.out == ""
    assert ".tcw/tcw-config.local.yaml" in result.err and "id" in result.err
    words = argv[:3] if argv[1] == "stage" else argv[:2]
    assert result.err.startswith(f"tcw {' '.join(words)}: .tcw/tcw-config.local.yaml: id: ")


def test_version_runs_whatever_the_configuration(personal):
    personal.local({"id": "other"})
    assert tcw(personal.root, "--version").code == 0


def test_with_personal_files_switched_off_the_same_command_runs(personal, monkeypatch):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.local({"id": "other"})
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", "1")
    assert tcw(personal.root, "work", "list").code == 0


# -- AC 21: open_backend uses the loader ------------------------------------------------


def test_open_backend_refuses_a_shared_key_in_a_personal_file(personal):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.local({"id": "other"})
    with pytest.raises(ConfigError) as caught:
        open_backend(personal.root)
    assert caught.value.code == 1
    assert ".tcw/tcw-config.local.yaml" in str(caught.value) and "id" in str(caught.value)


def test_open_backend_opens_with_personal_files_switched_off(personal, monkeypatch):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.local({"id": "other"})
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", "1")
    assert open_backend(personal.root).project == "p"


def test_open_backend_answers_the_local_user_name(personal):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.local({"user": {"name": "Brian"}})
    assert open_backend(personal.root).current_user() == "Brian"


# -- AC 9: other projects ignore personal layers --------------------------------------


@pytest.fixture
def family(tmp_path, monkeypatch):
    parent = make_project(tmp_path, "parent")
    child = make_project(tmp_path, "child")
    connect(parent, child, "children")
    connect(child, parent, "parent")
    commit_all(parent)
    commit_all(child)
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    return parent, child


def test_a_childs_local_file_is_not_read_when_delegating_to_it(family):
    parent, child = family
    write_local_config(child, "id: wrong\n")
    result = tcw(parent, "work", "new", "--project", "child", "x")
    assert result.code == 0, result
    assert result.out.startswith("child/")
    folder = result.out.strip().split("/", 1)[1]
    assert (child / "docs" / "work" / folder).is_dir()


def test_identity_is_only_the_acting_projects(family, tmp_path):
    parent, child = family
    user = tmp_path / "xdg-config" / "tcw" / "config.yaml"
    user.parent.mkdir(parents=True)
    write_config_file(user, "user:\n  name: Brian\n")
    assert open_backend(parent).current_user() == "Brian"
    assert open_project("child", parent).current_user() is None


def test_graph_readers_tolerate_what_the_loader_refuses(family, monkeypatch):
    parent, child = family
    path = config_file(child)
    document = yaml.safe_load(path.read_text())
    document["work"] = {"lifecycle": {"spec": {"prompt": []}}}
    write_config_file(path, yaml.safe_dump(document))
    write_local_config(parent, "work: [unclosed\n")
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", "1")
    listed = tcw(parent, "projects", "list")
    assert listed.code == 0, listed
    assert "child" in listed.out.split()


# -- AC 11: TCW's own text only through the list ---------------------------------------


def test_an_empty_local_prompt_list_prints_no_packaged_text(personal):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.local({"work": {"stages": {"spec": {"prompt": []}}}})
    result = tcw(personal.root, "work", "stage", "prompt", "spec")
    assert result.code == 0, result
    assert not any(line in result.out for line in packaged_lines("spec"))


def test_a_project_list_without_inherit_replaces_the_packaged_text(personal):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.project({"work": {"stages": {"spec": {"prompt": [{"blob": "house"}]}}}})
    result = tcw(personal.root, "work", "stage", "prompt", "spec")
    assert result.code == 0, result
    assert "house" in result.out
    assert not any(line in result.out for line in packaged_lines("spec"))


def test_inherit_puts_the_packaged_text_where_it_stands(personal):
    (personal.root / "docs" / "work").mkdir(parents=True)
    personal.project({"work": {"stages": {"spec": {"prompt": [{"inherit": True},
                                                              {"blob": "house"}]}}}})
    result = tcw(personal.root, "work", "stage", "prompt", "spec")
    assert result.code == 0, result
    lines = packaged_lines("spec")
    assert all(line in result.out for line in lines)
    assert result.out.index(lines[-1]) < result.out.index("house")
