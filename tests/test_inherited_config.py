"""Configuration a project takes from its parents (TCW-109 Design 1-3, 6, 7),
through `load_config` and the command line.

Each test is named after the criterion it proves. The layouts are the spec's:
`core` is a parent, `app` its child, both side by side in one folder, where
TCW-107's search finds them."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tcw.config import load_config
from tests.projectfiles import write_config, write_local_config
from tests.test_project_files_cli import personal_env, tcw

INHERIT = {"inherit": True}


def project(root: Path, project_id: str, *, parents=None, children=None,
            work=None, extra: dict | None = None) -> Path:
    """A 4.0 project at `root`. Every key a test's outcome depends on is given
    by the test: nothing is defaulted but the ID."""
    data: dict = {"id": project_id}
    if parents is not None:
        data["parents"] = parents
    if children is not None:
        data["children"] = children
    if work is not None:
        data["work"] = work
    data.update(extra or {})
    write_config(root, yaml.safe_dump(data, sort_keys=False))
    return root.resolve()


def problems(config) -> list[str]:
    return [str(p) for p in config.problems]


# -- one project: `inherit: true` in `work.tags`, and `null` (Design 2.4, 2.5) -----------


def test_ac7_inherit_in_a_project_with_no_parents(tmp_path):
    app = project(tmp_path / "app", "app", work={"tags": [INHERIT, "c"]})
    config = load_config(app)
    assert problems(config) == []
    assert config.work.tags == ("c",)
    ran = tcw(app, "validate")
    assert ran.code == 0, ran


def test_ac7_inherit_elsewhere_is_refused_naming_work_tags(tmp_path):
    app = project(tmp_path / "app", "app", work={"documentation": [INHERIT]})
    found = [p for p in problems(load_config(app)) if "'inherit' is allowed only" in p]
    assert len(found) == 1 and "work.tags" in found[0]


def test_ac7_two_inherit_entries_in_work_tags(tmp_path):
    app = project(tmp_path / "app", "app", work={"tags": [INHERIT, "c", INHERIT]})
    assert any("a list may hold one 'inherit' entry" in p
               for p in problems(load_config(app)))


def test_ac8_null_in_a_personal_file_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    app = project(tmp_path / "app", "app")
    write_local_config(app, "work:\n  tags: null\n")
    assert any("null has no meaning in a personal file" in p
               for p in problems(load_config(app)))


def test_ac8_a_null_backend_is_still_refused(tmp_path):
    app = project(tmp_path / "app", "app", work={"backend": None})
    assert any("must be one of" in p for p in problems(load_config(app)))


@pytest.mark.parametrize("key", ["tags", "jira"])
def test_ac8_null_at_an_inherited_key_in_one_project_is_no_value(tmp_path, key):
    app = project(tmp_path / "app", "app", work={key: None})
    config = load_config(app)
    assert problems(config) == []
    assert config.work.tags == ()
    assert key not in config.values["work"]
