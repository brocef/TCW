"""No test reads the developer's own personal configuration (TCW-72 AC 19),
and the configuration files are read through one duplicate-key loader."""

from __future__ import annotations

import os

import pytest

from tcw.store import fs, project
from tcw.store.yaml_source import UniqueKeyLoader


def test_every_test_runs_with_personal_files_switched_off(tmp_path):
    assert os.environ["TCW_NO_PERSONAL_CONFIG"] == "1"
    assert os.environ["XDG_CONFIG_HOME"] == str(tmp_path / "xdg-config")


def test_one_duplicate_key_loader_serves_both_readers():
    assert fs._UniqueKeyLoader is UniqueKeyLoader
    assert project._UniqueKeyLoader is UniqueKeyLoader


def test_a_duplicate_key_is_still_refused_by_both_readers(tmp_path):
    (tmp_path / "tcw-config.yaml").write_text("id: p\nid: q\n")
    with pytest.raises(ValueError, match="duplicate key"):
        fs.load_config(tmp_path / "tcw-config.yaml")
    problems = [str(p) for p in project.FsProjectRegistry.open(tmp_path).check()]
    assert any("duplicate key" in p for p in problems), problems
