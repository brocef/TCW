"""The taxonomy and capabilities stores list their objects by the walk: only a
folder holding its state file is a term or a capability (TCW-111 Design 2.3,
2.4, 2.5; AC 4, AC 6 and AC 17's listing half)."""

from __future__ import annotations

import pytest

from tcw.object_folders import object_paths
from tcw.store.fs import FsCapabilitiesStore
from tests.objectcli import obj, project, store, tcw  # noqa: F401
from tests.statefiles import write_state
from tests.test_capabilities_rm import connect, federated, repo, write_cap


@pytest.fixture
def demo(tmp_path):
    return project(tmp_path, work={})


def snapshot(root):
    return sorted((str(p.relative_to(root)), p.read_bytes() if p.is_file() else None)
                  for p in (root / "docs").rglob("*"))


# -- AC 4 -------------------------------------------------------------------------

def test_an_organising_taxonomy_folder_is_no_term(tcw, demo):
    obj(demo, "taxonomy", "group/refund", name="Refund")
    listed = tcw(["taxonomy", "list"], demo)
    assert (listed.code, listed.out) == (0, "demo.taxonomy/group/refund\n")
    assert tcw(["taxonomy", "show", "group"], demo).code == 4
    assert tcw(["taxonomy", "show", "group/refund"], demo).code == 0


def test_an_organising_capabilities_folder_is_no_capability(tcw, demo):
    obj(demo, "capabilities", "group/x", id="cap-aaaaaa", name="X", Status="Missing")
    listed = tcw(["capabilities", "list"], demo)
    assert (listed.code, listed.out) == (0, "demo.capabilities/group/x\n")
    assert tcw(["capabilities", "show", "group"], demo).code == 4


def test_a_parent_that_is_an_organising_folder_is_no_term(tcw, demo):
    obj(demo, "taxonomy", "group/refund", name="Refund")
    added = tcw(["taxonomy", "add", "Child", "--parent", "group"], demo)
    assert added.code == 2 and "parent term does not exist" in added.err
    assert not (store(demo, "taxonomy") / "group" / "child").exists()


# -- AC 6 -------------------------------------------------------------------------

@pytest.mark.parametrize("argv", [["taxonomy", "add", "Resources"],
                                  ["taxonomy", "add", "x", "--slug", "resources"],
                                  ["capabilities", "add", "cli/resources"],
                                  ["capabilities", "add", "Resources/x"]])
def test_a_reserved_name_is_refused_writing_nothing(tcw, demo, argv):
    before = snapshot(demo)
    added = tcw(argv, demo)
    assert added.code == 2, added
    assert "is reserved in the" in added.err
    assert snapshot(demo) == before


def test_reserved_names_are_per_store(tcw, demo):
    for name in ("Review", "Plan", "Comments"):
        assert tcw(["taxonomy", "add", name], demo).code == 0
    assert tcw(["capabilities", "add", "cli/review"], demo).code == 0


# -- AC 17, listing ---------------------------------------------------------------

def test_a_3x_taxonomy_folder_is_not_listed(tcw, demo):
    obj(demo, "taxonomy", "kept", name="Kept")
    old = store(demo, "taxonomy") / "old"
    old.mkdir()
    (old / "meta.yaml").write_text("name: Old\n")
    assert tcw(["taxonomy", "list"], demo).out == "demo.taxonomy/kept\n"
    assert tcw(["taxonomy", "show", "old"], demo).code == 4


def test_a_3x_capability_folder_is_not_listed(tcw, demo):
    old = store(demo, "capabilities") / "cli" / "old"
    old.mkdir(parents=True)
    (old / "meta.yaml").write_text("id: cap-old000\nname: Old\nStatus: Missing\n")
    assert tcw(["capabilities", "list"], demo).out == ""


# -- the 3.x override folders (Design 2.5, last paragraph) -------------------------

def test_an_override_at_the_mirror_path_is_applied_and_not_listed(tmp_path):
    base, child = federated(tmp_path)
    folder = child / "docs" / "capabilities" / "auth" / "login"
    write_state(folder / "tcw-capability.yaml", "overrides: base/cap-aaa111\nStatus: Omitted\n")
    st = FsCapabilitiesStore.open(child)
    assert st.list_all(local_only=True) == []
    [composed] = st.list_all()
    assert str(composed.full_id) == "base.capabilities/auth/login"
    assert composed.status == "Omitted"
    assert "auth/login" in object_paths(st.root, "capabilities")


def test_an_override_at_the_alias_path_is_applied_and_not_listed(tmp_path):
    base, child = federated(tmp_path)
    write_cap(child, "auth/login", id="cap-own001", Status="Supported")
    folder = child / "docs" / "capabilities" / "base" / "auth" / "login"
    write_state(folder / "tcw-capability.yaml", "overrides: base/cap-aaa111\nStatus: Omitted\n")
    st = FsCapabilitiesStore.open(child)
    assert [str(c.full_id) for c in st.list_all(local_only=True)] == \
        ["child.capabilities/auth/login"]
    assert st.get_inherited("base", "auth/login").status == "Omitted"
    assert "base/auth/login" in object_paths(st.root, "capabilities")


def test_the_walk_does_not_list_a_hidden_folder(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "routes", id="cap-rou001", Status="Supported")
    write_cap(root, "routes/.drafts/login", id="cap-log001", Status="Supported")
    assert [c.path for c in FsCapabilitiesStore.open(root).list_all()] == ["routes"]
