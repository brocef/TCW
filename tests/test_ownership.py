"""The ownership check (TCW-114 Design 1.1, 1.3; plan Step 2): one function
refuses an object the active project does not own, in one message shape,
and looking for the owner's folder never changes the outcome."""

from __future__ import annotations

import shutil

import pytest

from tcw import exit as codes
from tcw.errors import Refused
from tcw.ids import FullId
from tcw.ownership import check_owned
from tests.objectcli import project
from tests.projectfiles import write_manifest

CORE_X = FullId("core", "capabilities", "cli/x")


@pytest.fixture
def side_by_side(tmp_path):
    """`app` and `core`, two git repositories side by side, `core` placed in
    `app`'s manifest."""
    app = project(tmp_path, "app", work={})
    core = project(tmp_path, "core", work={})
    write_manifest(app, {"core": "../core"})
    return app, core


def refusal(full_id, app, **kw) -> Refused:
    with pytest.raises(Refused) as caught:
        check_owned(full_id, app, **kw)
    assert caught.value.code == codes.REFUSED
    assert type(caught.value) is Refused
    return caught.value


def test_the_active_projects_own_object_passes(side_by_side):
    app, _ = side_by_side
    assert check_owned(FullId("app", "work", "x"), app) is None


def test_another_projects_object_is_refused_naming_its_folder(side_by_side):
    app, core = side_by_side
    message = str(refusal(CORE_X, app))
    assert message == (f"core.capabilities/cli/x belongs to project 'core'; run the "
                       f"command there: tcw -C {core.resolve()} …")


def test_a_reason_sits_between_the_owner_and_where_to_go(side_by_side):
    app, core = side_by_side
    reason = ", and 'app' does not inherit it, so it cannot be overridden here"
    message = str(refusal(CORE_X, app, reason=reason))
    assert message == (f"core.capabilities/cli/x belongs to project 'core'{reason}; "
                       f"run the command there: tcw -C {core.resolve()} …")


def test_a_hint_ends_the_message(side_by_side):
    app, _ = side_by_side
    message = str(refusal(CORE_X, app, hint="; or override it here"))
    assert message.endswith(" …; or override it here")


@pytest.mark.parametrize("repository", ["https://example.invalid/core.git", None])
def test_a_project_not_on_this_machine(side_by_side, repository):
    app, core = side_by_side
    shutil.rmtree(core)
    entry = {"path": "../core", **({"repository": repository} if repository else {})}
    write_manifest(app, {"core": entry})
    message = str(refusal(CORE_X, app))
    tail = f" ({repository})" if repository else ""
    assert message == ("core.capabilities/cli/x belongs to project 'core'; project "
                       f"'core' is not on this machine{tail}")
    assert "tcw -C" not in message


def test_a_project_nothing_names_is_not_on_this_machine(tmp_path):
    app = project(tmp_path, "app", work={})
    message = str(refusal(CORE_X, app))
    assert message == ("core.capabilities/cli/x belongs to project 'core'; project "
                       "'core' is not on this machine")


def test_a_graph_problem_is_named_as_one(tmp_path):
    """Two folders beside `app` both declare `core`: saying it is not on
    this machine would be false (Design 1.3, review S11)."""
    app = project(tmp_path, "app", work={})
    project(tmp_path, "core", work={}, name="core-a")
    project(tmp_path, "core", work={}, name="core-b")
    message = str(refusal(CORE_X, app))
    assert message.startswith("core.capabilities/cli/x belongs to project 'core'; "
                              "project 'core' cannot be located: ")
    assert "core-a" in message and "core-b" in message
    assert "not on this machine" not in message


def test_no_backend_and_no_store_of_the_owner_is_opened(side_by_side, monkeypatch):
    import tcw.work.open
    from tcw.store.fs import FsTreeStore
    app, core = side_by_side

    def fail(*_, **__):
        raise AssertionError("the check opened something of the owner's")
    monkeypatch.setattr(tcw.work.open, "open_project", fail)
    monkeypatch.setattr(tcw.work.open, "open_backend", fail)
    monkeypatch.setattr(FsTreeStore, "__init__", fail)
    assert str(core.resolve()) in str(refusal(CORE_X, app))
    assert check_owned(FullId("app", "taxonomy", "t"), app) is None
