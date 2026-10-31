"""A migration's related projects: placed where 3.x placed them, read only
when a conversion must read them, in either format, and never written
(TCW-116 Design 1.3, 6.1, 6.5; criteria 48 and 69; plan Step 16).

These call `family.read_family` directly: a fixture with a related project
holds `projects:` or `extends`, which the command still refuses until Steps
18 and 19 convert them.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tcw.migrate import family as family_module, legacy
from tcw.migrate.family import absent_project_message, read_family
from tests.migrate.fixtures import LIB_URL, build_f_full, lib_clone, snapshot


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    build_f_full(tmp_path / "base", cache_home=tmp_path / "cache")
    return tmp_path / "base"


def family_of(folder: Path):
    data = legacy.read_3x_layers(folder).shared.data
    return read_family(folder, data["id"], data)


@pytest.fixture
def reads(monkeypatch):
    """Each folder `legacy.read_3x_layers` reads, in order."""
    seen: list[Path] = []
    original = legacy.read_3x_layers

    def spy(root):
        seen.append(Path(root))
        return original(root)
    monkeypatch.setattr(legacy, "read_3x_layers", spy)
    return seen


def test_each_entry_is_placed_without_being_read(base, tmp_path, reads):
    app = base / "ws/app"
    found = family_of(app)
    reads.clear()
    assert {pid: (p.folder, p.how) for pid, p in found.placed.items()} == {
        "kid": (base / "ws/kid", "locator"), "ws": (base / "ws", "locator"),
        "core": (base / "core", "locator"),
        "lib": (lib_clone(tmp_path / "cache"), "repository")}
    assert found.place("ws").here
    assert reads == []


def test_a_project_is_read_once_and_only_when_asked_for(base, reads):
    found = family_of(base / "ws/app")
    reads.clear()
    ws = found.member("ws", "E1", "tcw-config.yaml")
    assert (ws.id, ws.form, ws.folder) == ("ws", "3.x", base / "ws")
    assert ws.raw["work"]["tags"] == ["bug", "docs"]
    found.member("ws", "E1", "tcw-config.yaml")
    assert reads == [base / "ws"]


def test_nothing_is_written_in_any_project(base, tmp_path):
    before = snapshot(base, tmp_path / "cache")
    found = family_of(base / "ws/sib")
    for pid in ("ws", "core", "app", "lib", "kid"):
        found.member(pid, "C14", "tcw-config.yaml")
    assert snapshot(base, tmp_path / "cache") == before
    assert found.blockers == []


def test_a_project_no_entry_names_is_reached_as_3x_reached_it(base, reads):
    """sib names only ws; core is reached through ws's child app, whose
    upstream it is, and kid through app's children."""
    found = family_of(base / "ws/sib")
    reads.clear()
    assert found.member("core", "C14", "tcw-config.yaml").folder == base / "core"
    assert reads[:2] == [base / "ws", base / "ws/app"]
    assert found.member("kid", "C16", "tcw-config.yaml").folder == base / "ws/kid"
    assert found.member("nobody", "C16", "tcw-config.yaml") is None
    assert found.blockers == []


def test_an_upstream_s_own_entries_are_not_followed(base):
    """With app no longer naming lib, lib is not reached from sib, though
    core, app's upstream, names it: 3.x loaded an upstream only as far as
    its own file."""
    config = base / "ws/app/tcw-config.yaml"
    text = config.read_text()
    config.write_text(text.replace(
        "    lib:\n      repository:\n        url: https://example.invalid/lib.git\n", ""))
    found = family_of(base / "ws/sib")
    assert found.member("core", "C14", "tcw-config.yaml") is not None
    assert found.member("lib", "C14", "tcw-config.yaml") is None
    assert found.blockers == []


def test_a_related_project_already_migrated_is_read_as_it_is(base):
    ws = base / "ws"
    (ws / "tcw-config.yaml").unlink()
    (ws / ".tcw").mkdir()
    (ws / ".tcw/tcw-config.yaml").write_text(
        "tcw-version: 4.0.0\nid: ws\nchildren:\n- app\n- sib\nwork:\n  tags:\n  - bug\n")
    (ws / ".tcw/tcw-manifest.yaml").write_text(
        "tcw-version: 4.0.0\nprojects:\n  app:\n    path: app\n  sib:\n    path: sib\n")
    found = family_of(base / "ws/app")
    member = found.member("ws", "E1", "tcw-config.yaml")
    assert (member.form, member.raw) == ("4.0", {"id": "ws", "children": ["app", "sib"],
                                                 "work": {"tags": ["bug"]}})
    # Its own children are followed by 4.0's lookup.
    assert found.member("sib", "E4", "tcw-config.yaml").folder == base / "ws/sib"


def test_a_project_that_must_be_read_and_is_not_here_is_b5(base, tmp_path):
    shutil.rmtree(base / "core")
    shutil.rmtree(lib_clone(tmp_path / "cache"))
    found = family_of(base / "ws/app")
    assert found.member("core", "E1", "tcw-config.yaml") is None
    assert found.member("lib", "C14", "tcw-config.yaml") is None
    found.member("core", "E1", "tcw-config.yaml")
    assert [(b.code, b.where) for b in found.blockers] == [("B5", "tcw-config.yaml")] * 2
    core, lib = (b.why for b in found.blockers)
    assert core == "E1: " + absent_project_message("core", base / "core", None)
    assert f"put the project at {base / 'core'}" in core
    assert f"'git clone {LIB_URL} {lib_clone(tmp_path / 'cache')}'" in lib
    for text in (core, lib):
        assert "then run 'tcw migrate' again" in text
        assert "'tcw project provision' fetches every related project" in text


def test_a_pinned_repository_names_its_ref():
    text = absent_project_message("lib", Path("/w/lib"),
                                  legacy.RepoDecl3(LIB_URL, ref="v1"))
    assert f"'git clone {LIB_URL} (at v1) /w/lib'" in text


def test_the_static_guard_allows_the_clone_line_only_here():
    """Criterion 69: the clone line is the one exemption TCW-116 adds to
    TCW-73's guard. TCW-118 adds one more, B18's messages, which name the
    git ignore rule that is the reason the run refuses; no other function in
    `tcw/migrate/` may name git."""
    from tests import test_static_guards
    assert ("migrate/family.py", "absent_project_message") in test_static_guards.EXEMPT
    assert sorted(e for e in test_static_guards.EXEMPT if e[0].startswith("migrate/")) == [
        ("migrate/family.py", "absent_project_message"),
        ("migrate/plan.py", "ignored_blockers")]
    assert family_module.absent_project_message is absent_project_message
