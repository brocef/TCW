"""Configuration a project takes from its parents (TCW-109 Design 1-3, 6, 7),
through `load_config` and the command line.

Each test is named after the criterion it proves. The layouts are the spec's:
`core` is a parent, `app` its child, both side by side in one folder, where
TCW-107's search finds them."""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw.config import Withheld, load_config
from tcw.errors import BackendError, InheritedUnavailable
from tests.projectfiles import config_file, write_config, write_config_file, \
    write_local_config
from tests.test_project_files_cli import personal_env, tcw
from tests.work.projects import commit_all, make_project

INHERIT = {"inherit": True}


@dataclass
class Ran:
    code: int
    out: str
    err: str


@pytest.fixture
def run(monkeypatch, capsys):
    """`tcw` in this process, from `cwd`: what a test that replaces a
    function inside the command needs."""
    from tcw.cli import main

    def go(cwd: Path, *argv: str, stdin: str = "") -> Ran:
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(list(argv))
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Ran(code, captured.out, captured.err)
    return go


def set_work(root: Path, work: dict | None = None, **keys) -> Path:
    """Replace `work:` (and any other top-level key given) in a project
    `make_project` built."""
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    if work is not None:
        document["work"] = work
    document.update(keys)
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    return root


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


# -- what reads an inherited key reads it only when it uses it (Design 3.4) ------------


def test_withheld_raises_only_when_used():
    held = Withheld(lambda: BackendError("held back"))
    for use in (list, len, bool, lambda h: "a" in h, lambda h: h.site):
        with pytest.raises(BackendError, match="held back"):
            use(held)
    assert repr(held) == "Withheld(...)"
    assert (lambda value: value)(held) is held
    import copy
    assert copy.deepcopy(held) is held


def test_a_tag_is_read_only_when_one_is_applied():
    from tcw.work.model import Changes, validate_changes
    held = Withheld(lambda: BackendError("held back"))
    common = dict(item_slug=None, registered_tags=held, current_project="app",
                  parent_of=lambda slug: None)
    validate_changes(Changes(), **common)
    with pytest.raises(BackendError, match="held back"):
        validate_changes(Changes(add_tags=("t",)), **common)


@pytest.fixture
def no_store(monkeypatch):
    """Opening a work store fails loudly."""
    import tcw.work.cli
    import tcw.work.open

    def refuse(*args, **kwargs):
        raise AssertionError("the work store was opened")
    monkeypatch.setattr(tcw.work.open, "open_backend", refuse)
    monkeypatch.setattr(tcw.work.cli, "open_backend", refuse)


def _two_projects(tmp_path, run):
    """`app` and `lib`, with an item in `lib`, and what each command that
    needs nothing inherited answers in `app` while the store can be opened."""
    app = make_project(tmp_path, "app", config={})
    lib = make_project(tmp_path, "lib", config={})
    commit_all(app)
    made = run(lib, "work", "new", "lib thing")
    assert made.code == 0, made
    item = made.out.strip()
    before = {argv: run(app, *argv) for argv in [
        ("work", "lifecycle"), ("work", "docs"), ("work", "stage", "prompt", "spec"),
        ("work", "procedure", "search"), ("work", "path"), ("work", "show", item)]}
    assert all(r.code == 0 for r in before.values()), before
    assert "owner: lib" in before[("work", "show", item)].out
    return app, before


def test_commands_that_need_nothing_inherited_do_not_open_the_store(
        tmp_path, run, monkeypatch):
    """Design 3.4: the active project's store is never opened by these, so
    they answer as they did with it refused."""
    app, before = _two_projects(tmp_path, run)
    import tcw.work.cli
    import tcw.work.open
    real = tcw.work.open.open_backend

    def refuse_app(root, **kwargs):
        if Path(root).resolve() == app.resolve():
            raise AssertionError("the active project's work store was opened")
        return real(root, **kwargs)
    monkeypatch.setattr(tcw.work.cli, "open_backend", refuse_app)
    monkeypatch.setattr(tcw.work.open, "open_backend", refuse_app)
    for argv, was in before.items():
        now = run(app, *argv)
        assert (now.code, now.out, now.err) == (was.code, was.out, was.err), argv


def test_the_checks_the_store_made_are_kept(tmp_path, run):
    """In a project whose graph is invalid, each command that no longer opens
    the store fails with the message it gave when it did."""
    app = make_project(tmp_path, "app", config={})
    make_project(tmp_path, "kid", config={})
    set_work(app, children=["kid"])
    listed = run(app, "work", "list")
    assert listed.code == 1, listed
    graph = listed.err.split(": ", 1)[1]
    for argv in [("work", "lifecycle"), ("work", "docs"),
                 ("work", "stage", "prompt", "spec"), ("work", "path")]:
        ran = run(app, *argv)
        assert ran.code == 1, (argv, ran)
        assert graph in ran.err, (argv, ran.err)


def test_no_work_path_is_still_the_same_failure(tmp_path, run):
    app = project(tmp_path / "app", "app", work={"path": "nowhere"})
    listed, path = run(app, "work", "list"), run(app, "work", "path")
    assert listed.code == path.code != 0
    assert listed.err.split(": ", 1)[1] == path.err.split(": ", 1)[1]
