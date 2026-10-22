"""Where the layers are, and switching the personal ones off (TCW-72 AC 1, 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tcw.config import load_config, user_config_path
from tests.projectfiles import write_local_config


def test_an_absolute_xdg_config_home_names_the_user_file(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "x"))
    assert user_config_path() == tmp_path / "x" / "tcw" / "config.yaml"


def test_without_xdg_config_home_the_home_folder_is_used(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert user_config_path() == tmp_path / ".config" / "tcw" / "config.yaml"


def test_a_relative_xdg_config_home_is_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", "rel/x")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert user_config_path() == tmp_path / ".config" / "tcw" / "config.yaml"


def test_with_no_home_folder_the_user_layer_is_skipped(personal, monkeypatch):
    personal.user("work: [this would be a problem]\n")
    monkeypatch.delenv("XDG_CONFIG_HOME")
    monkeypatch.delenv("HOME")

    def no_home():
        raise RuntimeError("Could not determine home directory.")
    monkeypatch.setattr(Path, "home", staticmethod(no_home))
    assert user_config_path() is None
    config = load_config(personal.root)
    assert config.problems == []
    assert {o.layer for o in config.origins.values()} <= {"built-in", "project"}


def test_the_user_file_is_read_from_xdg_config_home(personal):
    personal.user({"user": {"name": "Brian"}})
    config = load_config(personal.root)
    assert config.user_name == "Brian"
    assert config.origins[("user", "name")].file == personal.user_file


def test_a_local_file_beside_the_project_file_is_read(personal):
    personal.local({"user": {"name": "Brian"}})
    config = load_config(personal.root)
    assert config.origins[("user", "name")].layer == "local"


def test_a_local_file_in_the_parent_folder_is_not_read(personal):
    write_local_config(personal.root.parent, "id: wrong\n")
    config = load_config(personal.root)
    assert config.problems == []
    assert config.values["id"] == "p"


def test_skipping_personal_layers_opens_neither_file(personal, monkeypatch):
    personal.user("{ not yaml")
    personal.local("{ not yaml either")
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", "1")
    config = load_config(personal.root)
    assert config.problems == []
    assert {o.layer for o in config.origins.values()} == {"built-in", "project"}


def test_an_empty_skip_variable_reads_the_layers(personal, monkeypatch):
    personal.local({"user": {"name": "Brian"}})
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", "")
    assert load_config(personal.root).user_name == "Brian"


@pytest.mark.parametrize("value", ["true", "0", "yes"])
def test_any_other_skip_value_is_one_problem_naming_the_variable(personal, monkeypatch,
                                                                  value):
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", value)
    config = load_config(personal.root)
    assert len(config.problems) == 1
    assert "TCW_NO_PERSONAL_CONFIG" in str(config.problems[0])


def test_personal_false_reads_only_the_project_file(personal):
    personal.local({"id": "wrong", "user": {"name": "Brian"}})
    config = load_config(personal.root, personal=False)
    assert config.problems == [] and config.user_name is None


@pytest.mark.parametrize("text", ["", "null\n"])
def test_an_empty_personal_file_is_an_empty_layer(personal, text):
    personal.local(text)
    assert load_config(personal.root).problems == []


def test_an_unreadable_personal_file_is_a_problem_naming_it(personal):
    personal.local("work: [unclosed\n")
    config = load_config(personal.root)
    assert [p.file for p in config.problems] == [personal.local_file]
