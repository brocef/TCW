"""TCW-113 plan Step 3: which projects a scope covers, asked of the registry
(spec Design 1.2-1.4, 1.6's set of errors, 1.9, 2.2's covering scope).

Each test names the acceptance criterion it holds at the registry's level.
"""

from __future__ import annotations

import subprocess

import pytest
import yaml

from tcw.errors import (BackendError, ConfigError, InheritedUnavailable, NotFound,
                        TcwError, Unreachable, UsageError)
from tcw.store import project as project_module
from tcw.store.base import (SCOPES, StoreDeclarationError, StoreLocationUnusable,
                            StoreNotProvisioned, UNAVAILABILITY_ERRORS, is_unavailability)
from tcw.store.fs import init
from tcw.store.project import FsProjectRegistry
from tests.families import build_family
from tests.projectfiles import write_local_config, write_manifest


def members(root, scope):
    return [(m.id, m.relation) for m in FsProjectRegistry.open(root).scope_members(scope)]


@pytest.fixture
def family(tmp_path):
    return build_family(tmp_path, docs_passes="none")


def test_scopes_are_the_four():
    assert SCOPES == ("own", "up", "down", "all")


def test_scope_order_in_shared(family):
    # AC 3's order, at the registry's level; AC 4: never `other`.
    root = family["shared"]
    assert members(root, "own") == [("shared", "current")]
    assert members(root, "down") == [("shared", "current"), ("desktop", "descendant"),
                                     ("server", "descendant"), ("mobile", "descendant")]
    assert members(root, "all") == [("docs", "ancestor"), ("shared", "current"),
                                    ("desktop", "descendant"), ("server", "descendant"),
                                    ("mobile", "descendant")]
    assert members(root, "up") == [("docs", "ancestor"), ("shared", "current")]
    for scope in SCOPES:
        assert "other" not in [pid for pid, _ in members(root, scope)]


def test_up_covers_every_ancestor_whatever_inherit_says(family):
    # AC 10's `projects` order: `shared` passes nothing from `docs` down,
    # and `docs` is covered all the same.
    assert members(family["desktop"], "up") == [
        ("docs", "ancestor"), ("shared", "ancestor"), ("desktop", "current")]


def test_descendants_are_breadth_first(family):
    for kid, parent in (("kid", "desktop"), ("kid2", "server")):
        family.roots[kid] = root = family.base / kid
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        init(["work"], root, kid)
        family.set_parents(kid, [parent])
        family.add_child(parent, kid)
    # A depth-first walk would put `kid` straight after `desktop`, and a
    # walk taking the newest project first `kid2` before `kid`.
    assert [pid for pid, _ in members(family["shared"], "down")] == [
        "shared", "desktop", "server", "mobile", "kid", "kid2"]


def test_a_listed_child_not_here_is_covered_and_not_searched_below(family, monkeypatch):
    # The registry's own walk, when it opens, tries `mobile`'s folder once
    # (TCW-108); the scope asks nothing more of it.
    registry = FsProjectRegistry.open(family["shared"])
    read = []
    real = project_module._read_text
    monkeypatch.setattr(project_module, "_read_text",
                        lambda path: read.append(str(path)) or real(path))
    found = [(m.id, m.relation) for m in registry.scope_members("down")]
    assert ("mobile", "descendant") in found
    mobile_folder = str(family.base / "mobile")
    assert not [p for p in read if p.startswith(mobile_folder)]


def test_a_personal_child_is_covered_after_the_committed_ones(family, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG", raising=False)
    family.roots["extra"] = extra = family.base / "extra"
    extra.mkdir()
    subprocess.run(["git", "init", "-q", str(extra)], check=True)
    init(["work"], extra, "extra")
    family.set_parents("extra", ["shared"])
    write_local_config(family["shared"], yaml.safe_dump({"children": ["extra"]}))
    write_manifest(family["shared"], {"extra": "../extra"}, local=True)
    assert [pid for pid, _ in members(family["shared"], "down")] == [
        "shared", "desktop", "server", "mobile", "extra"]


def test_covering_scope(family):
    registry = FsProjectRegistry.open(family["shared"])
    assert registry.covering_scope("desktop") == "down"
    assert registry.covering_scope("docs") == "up"
    assert registry.covering_scope("other") is None


def test_a_project_with_no_family_asks_for_no_folder(tmp_path, monkeypatch):
    # AC 7 at the registry's level, Design 1.9.
    solo = tmp_path / "solo"
    solo.mkdir()
    subprocess.run(["git", "init", "-q", str(solo)], check=True)
    init(["work"], solo, "solo")
    asked = []
    real = FsProjectRegistry.project_folder
    monkeypatch.setattr(FsProjectRegistry, "project_folder",
                        lambda self, pid, named_by: asked.append(pid)
                        or real(self, pid, named_by))
    for scope in SCOPES:
        assert members(solo, scope) == [("solo", "current")]
    assert asked == []


@pytest.mark.parametrize("error", [
    TcwError("x"), Unreachable("x"), InheritedUnavailable("x"), ConfigError(["x"]),
    BackendError("x"), NotFound("x"), StoreLocationUnusable("x"),
    StoreDeclarationError("x"), StoreNotProvisioned("x"), yaml.YAMLError("x"),
    OSError("x")])
def test_an_unavailability(error):
    assert isinstance(error, UNAVAILABILITY_ERRORS)
    assert is_unavailability(error)


@pytest.mark.parametrize("error", [UsageError("x"), ValueError("x"), KeyError("x")])
def test_not_an_unavailability(error):
    assert not is_unavailability(error)
