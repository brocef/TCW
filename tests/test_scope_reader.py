"""TCW-113 plan Step 4: reading the projects a command covers (`tcw.scope`),
spec Design 1.5-1.8 and 2.2, called directly on the family `F`."""

from __future__ import annotations

import pytest
import yaml

from tcw import scope as scope_module
from tcw.errors import (ConfigError, InheritedUnavailable, NotFound, Unreachable,
                        UsageError)
from tcw.locate import Locator
from tcw.scope import UNAVAILABLE, cover
from tcw.store.base import (StoreDeclarationError, StoreLocationUnusable,
                            StoreNotProvisioned, UnreachableProject)
from tcw.store.fs import FsTreeStore
from tcw.store.project import FsProjectRegistry
from tests.families import build_family


@pytest.fixture
def family(tmp_path):
    return build_family(tmp_path, docs_passes="none")


@pytest.fixture
def opened(monkeypatch):
    """Every work backend and tree store opened, by the folder opened."""
    seen = []
    import tcw.work.open as work_open
    real_backend = work_open.open_backend
    monkeypatch.setattr(work_open, "open_backend",
                        lambda root, **kw: seen.append(("backend", root))
                        or real_backend(root, **kw))
    real_init = FsTreeStore.__init__

    def init(self, root, **kw):
        seen.append(("store", root))
        real_init(self, root, **kw)
    monkeypatch.setattr(FsTreeStore, "__init__", init)
    return seen


def test_own_asks_the_registry_for_no_scope(family, monkeypatch):
    asked = []
    real = FsProjectRegistry.scope_members
    monkeypatch.setattr(FsProjectRegistry, "scope_members",
                        lambda self, s, *a: asked.append(s) or real(self, s, *a))
    covered = cover(family["shared"], "own", None)
    assert asked == []
    assert covered.ids == ["shared"]
    assert covered.projects_json() is None


def test_project_outside_the_scope_names_the_scope_that_covers_it(family, opened):
    # AC 6's refusal, Design 2.2's whole form.
    with pytest.raises(UsageError) as raised:
        cover(family["shared"], "own", "desktop")
    assert str(raised.value) == ("--project desktop: 'desktop' is not covered by "
                                 "--scope own in 'shared', which covers shared; "
                                 "--scope down covers it")
    assert opened == []


def test_a_sibling_is_neither_ancestor_nor_descendant(family, opened):
    # AC 4's refusal.
    with pytest.raises(UsageError) as raised:
        cover(family["shared"], "all", "other")
    assert str(raised.value).endswith(
        "; it is neither an ancestor nor a descendant of 'shared'")
    assert "which covers docs, shared, desktop, server, mobile" in str(raised.value)
    assert opened == []


def test_a_project_that_is_no_project_id_is_refused(family, opened):
    with pytest.raises(UsageError) as raised:
        cover(family["shared"], "down", "Bad_Id")
    assert "'Bad_Id' is not a project ID" in str(raised.value)
    assert "lowercase letters and digits" in str(raised.value)
    assert opened == []


def test_an_unknown_scope_is_refused(family):
    with pytest.raises(UsageError):
        cover(family["shared"], "sideways", None)


def test_a_project_not_here_is_unavailable_with_its_fetch_command(family):
    covered = cover(family["shared"], "down", None)
    called = []
    assert covered.read("mobile", lambda root: called.append(root)) is UNAVAILABLE
    assert called == []
    assert "tcw project provision mobile" in covered.reasons["mobile"]
    said = []
    covered.warn("its work items are not listed", said.append)
    assert said == [f"warning: 'mobile' is unavailable, so its work items are not "
                    f"listed: {covered.reasons['mobile']}"]


@pytest.mark.parametrize("error", [
    Unreachable("u"), InheritedUnavailable("i"), ConfigError(["c1", "c2"]),
    NotFound("n"), StoreLocationUnusable("l"), StoreDeclarationError("d"),
    StoreNotProvisioned("p"), yaml.YAMLError("y"), OSError("o")])
def test_each_unavailability_records_a_reason(family, error):
    covered = cover(family["shared"], "down", None)

    def fail(root):
        raise error
    assert covered.read("desktop", fail) is UNAVAILABLE
    assert covered.reasons["desktop"]
    if isinstance(error, ConfigError):
        assert covered.reasons["desktop"] == "c1; c2"


@pytest.mark.parametrize("error", [UsageError("x"), ValueError("x")])
def test_a_usage_error_or_an_unclassified_one_propagates(family, error):
    covered = cover(family["shared"], "down", None)

    def fail(root):
        raise error
    with pytest.raises(type(error)):
        covered.read("desktop", fail)
    assert covered.reasons == {}


def test_a_project_that_failed_is_not_read_again(family):
    covered = cover(family["shared"], "down", None)
    calls = []

    def fail(root):
        calls.append(root)
        raise OSError("first")
    covered.read("desktop", fail)
    assert covered.read("desktop", lambda root: calls.append("again")) is UNAVAILABLE
    assert calls == [family["desktop"]]
    assert covered.reasons["desktop"] == "first"


def test_projects_names_only_what_was_left_out(family):
    # Design 1.8: `desktop`, never read, has no `unavailable` even when its
    # folder is gone.
    family.remove("desktop")
    covered = cover(family["shared"], "down", None)
    covered.read("mobile", lambda root: root)
    projects = covered.projects_json()
    assert [p["id"] for p in projects] == ["shared", "desktop", "server", "mobile"]
    assert [p["relation"] for p in projects] == ["current", "descendant", "descendant",
                                                 "descendant"]
    assert [p for p in projects if "unavailable" in p] == [
        {"id": "mobile", "relation": "descendant",
         "unavailable": covered.reasons["mobile"]}]


def test_root_of_a_member(family):
    covered = cover(family["shared"], "down", None)
    assert covered.root_of("desktop").resolve() == family["desktop"].resolve()
    assert covered.root_of("shared") == covered.root


def test_a_project_nothing_records_gets_the_fixed_sentence(family, monkeypatch):
    # Plan choice 3: `unreachable_project` answering None never reaches
    # `None.message`.
    monkeypatch.setattr(FsProjectRegistry, "unreachable_project", lambda self, pid: None)
    covered = cover(family["shared"], "down", None)
    called = []
    assert covered.read("mobile", called.append) is UNAVAILABLE
    assert called == []
    assert covered.reasons["mobile"] == ("project 'mobile' is not on this machine, and "
                                         "no manifest entry says where it would be")


@pytest.mark.parametrize("declaration", ["https://example.invalid/mobile.git", None])
def test_an_entry_with_no_message_still_gives_a_reason(family, monkeypatch, declaration):
    # Plan choice 3, the re-check's F1.
    declared_in = family["shared"] / ".tcw" / "tcw-config.yaml"
    record = UnreachableProject(id="mobile", locator=declaration or "../mobile",
                                declared_in=declared_in, message="")
    monkeypatch.setattr(FsProjectRegistry, "unreachable_project",
                        lambda self, pid: record if pid == "mobile" else None)
    covered = cover(family["shared"], "down", None)
    assert covered.read("mobile", lambda root: root) is UNAVAILABLE
    reason = covered.reasons["mobile"]
    assert "mobile" in reason and str(declared_in) in reason
    said = []
    covered.warn("its work items are not listed", said.append)
    assert not said[0].endswith(": ")


def test_one_locator_per_cover(family, monkeypatch):
    calls = []
    real = Locator.of.__func__
    monkeypatch.setattr(Locator, "of", classmethod(
        lambda cls, root: calls.append(root) or real(cls, root)))
    covered = cover(family["shared"], "down", None)
    for member in covered.others():
        covered.read(member.id, lambda root: root)
    assert len(calls) == 1
