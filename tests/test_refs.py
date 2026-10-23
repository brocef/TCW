"""Resolving a `tcw://` address (TCW-110 Design 2, 6): `resolve_address` is
thin glue over `tcw.locate` that never propagates a store exception to a
caller scanning many links. Two git repositories side by side, `app` naming
`core` under `projects.upstream` by ID, with no `extends` unless a test adds
one. The grammar itself is tested in `tests/test_ids.py`."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tcw import locate
from tcw.locate import ERROR, MISSING, UNRESOLVED
from tcw.refs import resolve_address
from tcw.store.fs import FsCapabilitiesStore, init
from tests.inherit import entry
from tests.projectfiles import connect_projects
from tests.work.projects import make_project


@pytest.fixture
def app(tmp_path) -> Path:
    app = make_project(tmp_path, "app", config={})
    core = make_project(tmp_path, "core", config={})
    for root in (app, core):
        init(["taxonomy", "capabilities"], root)
    entry(app, "taxonomy", "auth")
    entry(app, "capabilities", "auth/login", id="cap-login", Status="Supported")
    entry(core, "taxonomy", "term")
    entry(core, "capabilities", "cli/y", id="cap-y", Status="Supported")
    connect_projects(app, "upstream", "core")
    return app


# -- a 3.x reference is recognised and refused (Design 2.4) -------------------------


@pytest.mark.parametrize("uri", ["tcw://C/auth/login", "tcw://T/auth",
                                 "tcw://W/2026-01-01-x", "tcw://core/T/term"])
def test_a_3x_reference_is_refused_naming_tcw_migrate(app, uri):
    found = resolve_address(app, uri)
    assert (found.ok, found.outcome) == (False, ERROR)
    assert found.reason.startswith(f"{uri} is a TCW 3.x reference")
    assert "tcw migrate" in found.reason


@pytest.mark.parametrize("uri", ["tcw://app/", "tcw://app.taxonomy/a/../b",
                                 "tcw://app.taxonomy/auth/", "tcw://App.taxonomy/auth",
                                 "tcw://app.path", "http://app.taxonomy/auth"])
def test_a_malformed_address_is_an_error_not_an_exception(app, uri):
    found = resolve_address(app, uri)
    assert (found.ok, found.outcome) == (False, ERROR)
    assert found.reason


# -- objects ------------------------------------------------------------------------


@pytest.mark.parametrize("uri, namespace, key", [
    ("tcw://app.taxonomy/auth", "taxonomy", "auth"),
    ("tcw://app.capabilities/auth/login", "capabilities", "auth/login"),
])
def test_this_projects_own_object_is_keyed_by_its_id_path(app, uri, namespace, key):
    found = resolve_address(app, uri)
    assert (found.ok, found.namespace, found.key, found.project) == \
        (True, namespace, key, "")


def test_an_inherited_object_is_keyed_by_its_full_identifier(app):
    FsCapabilitiesStore.open(app).extends_add("core")
    found = resolve_address(app, "tcw://core.capabilities/cli/y")
    assert (found.ok, found.key, found.project) == (True, "core.capabilities/cli/y", "")


def test_another_projects_object_names_its_owner(app):
    """TCW-99 principle 1: naming is not inheriting (Design 6.2)."""
    found = resolve_address(app, "tcw://core.taxonomy/term")
    assert (found.ok, found.project) == (True, "core")


def test_an_object_that_is_not_there_is_missing(app):
    found = resolve_address(app, "tcw://core.taxonomy/missing")
    assert (found.ok, found.outcome) == (False, MISSING)
    assert "core.taxonomy/missing" in found.reason


def test_an_object_of_a_project_not_on_this_machine_is_unresolved(app):
    shutil.rmtree(app.parent / "core")
    found = resolve_address(app, "tcw://core.taxonomy/term")
    assert (found.ok, found.outcome) == (False, UNRESOLVED)


def test_an_id_nothing_knows_is_an_error_saying_check_the_spelling(app):
    found = resolve_address(app, "tcw://cor.taxonomy/term")
    assert (found.ok, found.outcome) == (False, ERROR)
    assert "no project with ID 'cor'" in found.reason
    assert "check the spelling" in found.reason


def test_two_folders_declaring_one_id_are_an_error_naming_both(app, tmp_path):
    one = make_project(tmp_path, "lib")
    two = make_project(tmp_path, "lib", name="lib-copy")
    found = resolve_address(app, "tcw://lib.taxonomy/term")
    assert (found.ok, found.outcome) == (False, ERROR)
    assert str(one.resolve()) in found.reason and str(two.resolve()) in found.reason


# -- folders (Design 6.4) -----------------------------------------------------------


@pytest.mark.parametrize("uri", ["tcw://core.path/docs", "tcw://core.path/nothing/here",
                                 "tcw://app.work.path/", "tcw://app.path/"])
def test_a_folder_address_is_checked_for_its_project_not_its_folder(app, uri):
    found = resolve_address(app, uri)
    assert (found.ok, found.folder) == (True, True)


def test_a_folder_address_of_an_unknown_project_is_an_error(app):
    found = resolve_address(app, "tcw://cor.path/docs")
    assert (found.ok, found.outcome) == (False, ERROR)
    assert "check the spelling" in found.reason


def test_a_folder_address_of_a_project_not_on_this_machine_is_unresolved(app):
    shutil.rmtree(app.parent / "core")
    assert resolve_address(app, "tcw://core.path/docs").outcome == UNRESOLVED


# -- never raises -------------------------------------------------------------------


def test_no_project_is_an_error(app):
    found = resolve_address(None, "tcw://app.taxonomy/auth")
    assert (found.ok, found.reason) == (False, "no TCW project")


@pytest.mark.parametrize("raised", [OSError("disk gone"), ValueError("bad file")])
def test_a_store_failure_becomes_an_answer(app, monkeypatch, raised):
    def broken(*_args, **_kwargs):
        raise raised
    monkeypatch.setattr(locate.Locator, "read", broken)
    found = resolve_address(app, "tcw://app.taxonomy/auth")
    assert (found.ok, found.outcome, found.reason) == (False, ERROR, str(raised))


def test_an_unreadable_store_becomes_an_answer(app):
    (app / "docs" / "taxonomy" / "auth" / "meta.yaml").write_text("name: [unclosed\n")
    found = resolve_address(app, "tcw://app.taxonomy/auth")
    assert (found.ok, found.outcome) == (False, ERROR)
    assert "meta.yaml" in found.reason
